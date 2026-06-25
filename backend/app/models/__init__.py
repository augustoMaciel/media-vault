"""Model re-exports.

Importing the models here ensures SQLAlchemy/Alembic register both tables when
`app.models` is imported by the factory, so `flask db migrate` detects them.
"""
from .user import User
from .media import Media, MediaVersion

__all__ = ["User", "Media", "MediaVersion"]
