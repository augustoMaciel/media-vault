"""User model — the login identity and owner of Media rows."""
from datetime import datetime, timezone

from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    # bcrypt hash only — plaintext passwords never touch the database.
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # One user owns many media; deleting the user removes their rows.
    # (Object bytes in MinIO are cleaned up explicitly by the delete route.)
    media = db.relationship(
        "Media",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        """Public-safe shape. NEVER includes password_hash."""
        return {
            "id": self.id,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<User {self.id} {self.email}>"
