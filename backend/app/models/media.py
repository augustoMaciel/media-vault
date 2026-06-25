"""Media model — file METADATA only.

The file bytes live in MinIO under `storage_key`; this row holds everything the
app needs to list, authorize, and serve that object. `owner_id` is the linchpin
of per-user isolation: every /media query is filtered by it.
"""
import secrets
from datetime import datetime, timezone

from app.extensions import db


class Media(db.Model):
    __tablename__ = "media"

    id = db.Column(db.Integer, primary_key=True)
    # Opaque, unguessable public handle used in API URLs. The integer PK stays
    # internal (FKs, joins); clients only ever see this. Defeats ID enumeration.
    public_id = db.Column(
        db.String(32),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: secrets.token_urlsafe(16),
    )

    # --- Ownership (per-user isolation) -------------------------------------
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # --- User-facing metadata -----------------------------------------------
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    original_name = db.Column(db.String(255), nullable=False)

    # --- Storage pointers (never exposed to clients) ------------------------
    storage_key = db.Column(db.String(512), unique=True, nullable=False)
    thumbnail_key = db.Column(db.String(512), nullable=True)

    # --- File facts ----------------------------------------------------------
    mime_type = db.Column(db.String(127), nullable=False)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Full version history; the columns above mirror the latest version as the
    # "current" snapshot, so existing routes keep working unchanged.
    versions = db.relationship(
        "MediaVersion",
        backref="media",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="MediaVersion.version_no",
    )

    @property
    def has_thumbnail(self) -> bool:
        """Derived flag for serialization (MediaResponseSchema reads this)."""
        return self.thumbnail_key is not None

    def to_dict(self):
        """Public-safe shape. Never exposes storage_key/thumbnail_key/owner_id."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "original_name": self.original_name,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "has_thumbnail": self.thumbnail_key is not None,
        }

    def __repr__(self):
        return f"<Media {self.id} owner={self.owner_id} {self.original_name}>"


class MediaVersion(db.Model):
    """One historical version of a Media item.

    Each version keeps its own object in MinIO (its own storage_key), so older
    versions stay downloadable. The parent Media row points at the latest one.
    """
    __tablename__ = "media_versions"

    id = db.Column(db.Integer, primary_key=True)
    media_id = db.Column(
        db.Integer, db.ForeignKey("media.id"), nullable=False, index=True
    )
    version_no = db.Column(db.Integer, nullable=False)

    original_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    storage_key = db.Column(db.String(512), unique=True, nullable=False)
    thumbnail_key = db.Column(db.String(512), nullable=True)
    mime_type = db.Column(db.String(127), nullable=False)
    size_bytes = db.Column(db.BigInteger, nullable=False)
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @property
    def has_thumbnail(self) -> bool:
        return self.thumbnail_key is not None

    @property
    def is_current(self) -> bool:
        """True when this version is the one the Media row currently points to."""
        return self.media is not None and self.storage_key == self.media.storage_key

    def __repr__(self):
        return f"<MediaVersion media={self.media_id} v{self.version_no}>"
