"""Media routes: list (+search), upload, versions, download, thumbnail, delete.

Registered at /media; EVERY route is @jwt_required and scoped to the caller.
OWNERSHIP RULE: single-item routes 404 (never 403) when the row isn't the
caller's — 403 would leak that the id exists.
"""
import io
import os
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, Response, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy import or_
from werkzeug.exceptions import NotFound

from app.extensions import db
from app.models import Media, MediaVersion
from app.core.security import current_user_id
from app.core.validators import validate_upload
from app.schemas.media import (
    MediaCreateSchema,
    MediaResponseSchema,
    MediaQuerySchema,
    MediaVersionResponseSchema,
    MediaVersionUpdateSchema,
)
from app.services import storage
from app.services.thumbnails import make_thumbnail, thumbnail_key_for, THUMBNAIL_MIME

media_bp = Blueprint("media", __name__)

_media_out = MediaResponseSchema()
_media_list_out = MediaResponseSchema(many=True)
_version_out = MediaVersionResponseSchema()
_version_list_out = MediaVersionResponseSchema(many=True)

_STREAM_CHUNK = 8192

# Thumbnails are immutable (uuid-keyed) and user-private -> cache hard in the browser.
_THUMB_CACHE_CONTROL = "private, max-age=86400, immutable"


def _escape_like(term: str) -> str:
    """Escape LIKE metacharacters so user input matches LITERALLY (not as
    wildcards). The value still travels as a bound parameter -> SQLi-safe."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _get_owned_or_404(public_id: str) -> Media:
    """Load a row only if it belongs to the caller; otherwise 404."""
    media = Media.query.filter_by(
        public_id=public_id, owner_id=current_user_id()
    ).first()
    if media is None:
        raise NotFound(description="Media not found.")
    return media


def _stream_object(key: str, mimetype: str, disposition: str | None) -> Response:
    """Stream a MinIO object through Flask, releasing the connection at the end."""
    resp = storage.open_stream(key)

    def generate():
        try:
            for chunk in resp.stream(_STREAM_CHUNK):
                yield chunk
        finally:
            resp.close()
            resp.release_conn()

    headers = {}
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(generate(), mimetype=mimetype, headers=headers)


def _store_file(owner_id: int, file_storage):
    """Validate + persist an uploaded file (and its thumbnail) to storage.

    Returns (storage_key, thumbnail_key, mime, size, safe_name). Shared by the
    initial upload and by adding a new version.
    """
    mime, size, safe_name = validate_upload(file_storage)  # 400/413 on bad input
    ext = os.path.splitext(safe_name)[1].lstrip(".").lower()
    storage_key = storage.build_key(owner_id, ext)

    # File is <=10MB; read once for both the object and the (optional) thumbnail.
    file_storage.stream.seek(0)
    data = file_storage.stream.read()
    storage.put_object(storage_key, io.BytesIO(data), len(data), mime)

    thumb_key = None
    thumb_bytes = make_thumbnail(data, mime)
    if thumb_bytes is not None:
        thumb_key = thumbnail_key_for(storage_key)
        storage.put_object(thumb_key, io.BytesIO(thumb_bytes), len(thumb_bytes), THUMBNAIL_MIME)

    return storage_key, thumb_key, mime, size, safe_name


@media_bp.get("")
@jwt_required()
def list_media():
    params = MediaQuerySchema().load(request.args.to_dict())
    q = params["q"]

    query = Media.query.filter(Media.owner_id == current_user_id())  # owner scope FIRST
    if q:
        like = f"%{_escape_like(q)}%"
        query = query.filter(or_(
            Media.title.ilike(like, escape="\\"),
            Media.description.ilike(like, escape="\\"),
            Media.original_name.ilike(like, escape="\\"),
        ))
    items = query.order_by(Media.uploaded_at.desc(), Media.id.desc()).all()
    return jsonify(_media_list_out.dump(items)), 200


@media_bp.post("")
@jwt_required()
def upload_media():
    meta = MediaCreateSchema().load(request.form.to_dict())
    uid = current_user_id()
    storage_key, thumb_key, mime, size, safe_name = _store_file(uid, request.files.get("file"))

    media = Media(
        owner_id=uid,
        title=meta["title"],
        description=meta["description"],
        original_name=safe_name,
        storage_key=storage_key,
        thumbnail_key=thumb_key,
        mime_type=mime,
        size_bytes=size,
    )
    # Record version 1 = the initial upload.
    media.versions.append(MediaVersion(
        version_no=1,
        original_name=safe_name,
        description=meta["description"],
        storage_key=storage_key,
        thumbnail_key=thumb_key,
        mime_type=mime,
        size_bytes=size,
    ))
    db.session.add(media)
    db.session.commit()
    return jsonify(_media_out.dump(media)), 201


@media_bp.post("/<media_id>/versions")
@jwt_required()
def add_version(media_id):
    """Upload a new version of an existing item (file-versioning bonus)."""
    media = _get_owned_or_404(media_id)
    uid = current_user_id()
    storage_key, thumb_key, mime, size, safe_name = _store_file(uid, request.files.get("file"))

    next_no = max((v.version_no for v in media.versions), default=0) + 1
    media.versions.append(MediaVersion(
        version_no=next_no,
        original_name=safe_name,
        description=media.description,  # carry over the current description
        storage_key=storage_key,
        thumbnail_key=thumb_key,
        mime_type=mime,
        size_bytes=size,
    ))
    # Repoint the current snapshot at the new version (old objects are retained).
    media.original_name = safe_name
    media.storage_key = storage_key
    media.thumbnail_key = thumb_key
    media.mime_type = mime
    media.size_bytes = size
    media.uploaded_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(_media_out.dump(media)), 201


@media_bp.get("/<media_id>/versions")
@jwt_required()
def list_versions(media_id):
    media = _get_owned_or_404(media_id)
    versions = sorted(media.versions, key=lambda v: v.version_no, reverse=True)
    return jsonify(_version_list_out.dump(versions)), 200


@media_bp.patch("/<media_id>/versions/<int:version_no>")
@jwt_required()
def update_version(media_id, version_no):
    """Edit a version's description (per-version editable metadata)."""
    media = _get_owned_or_404(media_id)
    version = next((v for v in media.versions if v.version_no == version_no), None)
    if version is None:
        raise NotFound(description="Version not found.")
    data = MediaVersionUpdateSchema().load(request.get_json(silent=True) or {})
    version.description = data["description"]
    if version.storage_key == media.storage_key:  # current version -> keep snapshot in sync
        media.description = data["description"]
    db.session.commit()
    return jsonify(_version_out.dump(version)), 200


@media_bp.get("/<media_id>/download")
@jwt_required()
def download_media(media_id):
    media = _get_owned_or_404(media_id)
    disposition = f'attachment; filename="{media.original_name}"'
    resp = _stream_object(media.storage_key, media.mime_type, disposition)
    resp.headers["Content-Length"] = str(media.size_bytes)
    return resp


@media_bp.get("/<media_id>/versions/<int:version_no>/download")
@jwt_required()
def download_version(media_id, version_no):
    media = _get_owned_or_404(media_id)
    version = next((v for v in media.versions if v.version_no == version_no), None)
    if version is None:
        raise NotFound(description="Version not found.")
    disposition = f'attachment; filename="{version.original_name}"'
    resp = _stream_object(version.storage_key, version.mime_type, disposition)
    resp.headers["Content-Length"] = str(version.size_bytes)
    return resp


@media_bp.get("/<media_id>/link")
@jwt_required()
def download_link(media_id):
    """Return a short-lived presigned URL for the file (expiring-link bonus)."""
    media = _get_owned_or_404(media_id)
    expires = current_app.config["PRESIGNED_URL_EXPIRES"]
    url = storage.presign_get(media.storage_key, expires=expires)
    return jsonify(url=url, expires_in=int(expires.total_seconds())), 200


@media_bp.get("/<media_id>/thumbnail")
@jwt_required()
def thumbnail(media_id):
    media = _get_owned_or_404(media_id)
    if not media.thumbnail_key:
        raise NotFound(description="No thumbnail for this item.")

    # The storage key is unique + immutable, so it doubles as a strong ETag.
    # A matching If-None-Match means the browser already has the bytes -> 304.
    etag = f'"{media.thumbnail_key}"'
    if request.headers.get("If-None-Match") == etag:
        return "", 304, {"ETag": etag, "Cache-Control": _THUMB_CACHE_CONTROL}

    resp = _stream_object(media.thumbnail_key, THUMBNAIL_MIME, None)  # inline
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = _THUMB_CACHE_CONTROL
    return resp


@media_bp.get("/<media_id>/versions/<int:version_no>/thumbnail")
@jwt_required()
def version_thumbnail(media_id, version_no):
    media = _get_owned_or_404(media_id)
    version = next((v for v in media.versions if v.version_no == version_no), None)
    if version is None or not version.thumbnail_key:
        raise NotFound(description="No thumbnail for this version.")

    etag = f'"{version.thumbnail_key}"'
    if request.headers.get("If-None-Match") == etag:
        return "", 304, {"ETag": etag, "Cache-Control": _THUMB_CACHE_CONTROL}

    resp = _stream_object(version.thumbnail_key, THUMBNAIL_MIME, None)
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = _THUMB_CACHE_CONTROL
    return resp


@media_bp.delete("/<media_id>")
@jwt_required()
def delete_media(media_id):
    media = _get_owned_or_404(media_id)
    # Remove every version's object(s); cascade drops the rows.
    keys = [(v.storage_key, v.thumbnail_key) for v in media.versions]
    if not keys:
        keys = [(media.storage_key, media.thumbnail_key)]
    for storage_key, thumb_key in keys:
        storage.delete_object(storage_key)
        if thumb_key:
            storage.delete_object(thumb_key)
    db.session.delete(media)
    db.session.commit()
    return "", 204


@media_bp.delete("/<media_id>/versions/<int:version_no>")
@jwt_required()
def delete_version(media_id, version_no):
    """Delete one version. Remaining versions are renumbered contiguously
    (deleting v2 of [v1,v2,v3] leaves v1 and a renumbered v2). Deleting the last
    remaining version deletes the whole file."""
    media = _get_owned_or_404(media_id)
    target = next((v for v in media.versions if v.version_no == version_no), None)
    if target is None:
        raise NotFound(description="Version not found.")

    # A file can't have zero versions -> deleting the last one removes the file.
    if len(media.versions) == 1:
        for v in media.versions:
            storage.delete_object(v.storage_key)
            if v.thumbnail_key:
                storage.delete_object(v.thumbnail_key)
        db.session.delete(media)
        db.session.commit()
        return jsonify(media_deleted=True), 200

    was_current = target.storage_key == media.storage_key

    storage.delete_object(target.storage_key)
    if target.thumbnail_key:
        storage.delete_object(target.thumbnail_key)
    media.versions.remove(target)
    db.session.flush()

    # Renumber remaining versions 1..N, preserving chronological order.
    remaining = sorted(media.versions, key=lambda v: v.version_no)
    for i, v in enumerate(remaining, start=1):
        v.version_no = i

    # If the current version was removed, repoint the snapshot to the newest one.
    if was_current:
        newest = remaining[-1]
        media.original_name = newest.original_name
        media.description = newest.description
        media.storage_key = newest.storage_key
        media.thumbnail_key = newest.thumbnail_key
        media.mime_type = newest.mime_type
        media.size_bytes = newest.size_bytes
        media.uploaded_at = newest.uploaded_at

    db.session.commit()
    return jsonify(
        media_deleted=False,
        versions=_version_list_out.dump(sorted(media.versions, key=lambda v: v.version_no, reverse=True)),
    ), 200
