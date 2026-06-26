"""Media schemas: upload metadata in, public media out, and search query.

The FILE itself is validated in core/validators.py (magic bytes, size, deep
type checks); these schemas only cover the JSON-ish fields and the ?q= term.
"""
from flask import current_app
from marshmallow import Schema, fields, validate, pre_load, EXCLUDE


class MediaCreateSchema(Schema):
    """Optional metadata sent alongside the uploaded file (multipart form)."""
    class Meta:
        unknown = EXCLUDE

    title = fields.String(
        required=False,
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=255),
    )
    description = fields.String(
        required=False,
        load_default=None,
        validate=validate.Length(max=2000),
        allow_none=True,
    )

    @pre_load
    def strip_blanks(self, data, **kwargs):
        """Trim title; trim description and treat blank as None."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if isinstance(out.get("title"), str):
            out["title"] = out["title"].strip() or None
        if isinstance(out.get("description"), str):
            out["description"] = out["description"].strip() or None
        return out


class MediaUpdateSchema(Schema):
    """Editable fields on a media item (title only, for now)."""
    class Meta:
        unknown = EXCLUDE

    title = fields.String(
        required=False, load_default=None, allow_none=True,
        validate=validate.Length(max=255),
    )

    @pre_load
    def clean(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("title"), str):
            out = dict(data)
            out["title"] = out["title"].strip()
            return out
        return data


class MediaResponseSchema(Schema):
    """Public, owner-safe media shape. Never exposes storage_key/owner_id."""
    id = fields.String(attribute="public_id", dump_only=True)
    title = fields.String(dump_only=True)
    description = fields.String(dump_only=True)
    original_name = fields.String(dump_only=True)
    mime_type = fields.String(dump_only=True)
    size_bytes = fields.Integer(dump_only=True)
    uploaded_at = fields.DateTime(dump_only=True)
    has_thumbnail = fields.Boolean(dump_only=True)


class MediaQuerySchema(Schema):
    """Validates the GET /media ?q= search term."""
    class Meta:
        unknown = EXCLUDE

    q = fields.String(required=False, load_default="")

    @pre_load
    def clean_q(self, data, **kwargs):
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if isinstance(out.get("q"), str):
            # Trim and hard-cap length BEFORE it ever reaches the query layer.
            max_len = current_app.config["MEDIA_SEARCH_MAX_LENGTH"]
            out["q"] = out["q"].strip()[:max_len]
        return out


class MediaVersionResponseSchema(Schema):
    """A single version in a Media item's history (no storage_key exposed)."""
    version_no = fields.Integer(dump_only=True)
    original_name = fields.String(dump_only=True)
    description = fields.String(dump_only=True, allow_none=True)
    mime_type = fields.String(dump_only=True)
    size_bytes = fields.Integer(dump_only=True)
    uploaded_at = fields.DateTime(dump_only=True)
    has_thumbnail = fields.Boolean(dump_only=True)
    is_current = fields.Boolean(dump_only=True)


class MediaVersionUpdateSchema(Schema):
    """Editable fields on a version (description only, for now)."""
    class Meta:
        unknown = EXCLUDE

    description = fields.String(
        required=False, load_default=None, allow_none=True,
        validate=validate.Length(max=2000),
    )

    @pre_load
    def clean(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("description"), str):
            out = dict(data)
            out["description"] = out["description"].strip() or None
            return out
        return data

