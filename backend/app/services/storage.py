"""MinIO object storage — the ONLY module that talks to the object store.

Blueprints never see buckets or keys directly; they call these functions. File
bytes live here (under an opaque "<owner>/<uuid>.<ext>" key); MySQL holds only
the metadata row that points at the key.
"""
import uuid
from datetime import timedelta

from flask import current_app
from minio import Minio


def get_client():
    """Build a MinIO client for server-side use (internal Docker endpoint)."""
    cfg = current_app.config
    return Minio(
        cfg["MINIO_ENDPOINT"],
        access_key=cfg["MINIO_ACCESS_KEY"],
        secret_key=cfg["MINIO_SECRET_KEY"],
        secure=cfg["MINIO_SECURE"],
    )


def _public_client():
    """Client bound to the browser-reachable endpoint, for presigned URLs.

    The internal endpoint ('minio:9000') is unreachable from the browser, so
    presigned links must be signed against MINIO_PUBLIC_ENDPOINT.
    """
    cfg = current_app.config
    return Minio(
        cfg["MINIO_PUBLIC_ENDPOINT"],
        access_key=cfg["MINIO_ACCESS_KEY"],
        secret_key=cfg["MINIO_SECRET_KEY"],
        secure=cfg["MINIO_SECURE"],
    )


def ensure_bucket():
    """Create the bucket if it does not exist (idempotent)."""
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def build_key(owner_id: int, ext: str) -> str:
    """Opaque, collision-free storage key namespaced by owner.

    Stored name never reflects the user's filename (no extension-based attacks,
    no path traversal). Shape: '<owner_id>/<uuid4hex>.<ext>'.
    """
    return f"{owner_id}/{uuid.uuid4().hex}.{ext}"


def put_object(key: str, stream, length: int, content_type: str):
    """Stream an upload into the bucket under `key`."""
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    client.put_object(bucket, key, stream, length, content_type=content_type)


def open_stream(key: str):
    """Open an object for streamed download.

    Returns a urllib3 HTTPResponse. The CALLER must close()/release_conn() it
    (the download route streams from it, then releases).
    """
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    return client.get_object(bucket, key)


def delete_object(key: str):
    """Remove an object. Safe to call for keys that may not exist."""
    client = get_client()
    bucket = current_app.config["MINIO_BUCKET"]
    client.remove_object(bucket, key)


def presign_get(key: str, expires: timedelta = timedelta(minutes=15)) -> str:
    """Presigned GET URL (bonus: expiring links), signed for the public endpoint."""
    client = _public_client()
    bucket = current_app.config["MINIO_BUCKET"]
    return client.presigned_get_object(bucket, key, expires=expires)
