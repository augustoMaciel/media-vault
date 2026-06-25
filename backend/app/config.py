"""Application configuration, driven entirely by environment variables.

Secrets (DB URL, JWT key, MinIO creds) are NEVER hard-coded — they come from the
environment (.env via docker-compose). Whitelists and limits live here so the
rest of the app has a single source of truth.
"""
import os
from datetime import timedelta


def _bytes_from_mb(mb: int) -> int:
    return mb * 1024 * 1024


class Config:
    # --- Database (SQLAlchemy + PyMySQL) -------------------------------------
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- JWT auth ------------------------------------------------------------
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    JWT_ALGORITHM = "HS256"            # HMAC-SHA256
    JWT_DECODE_ALGORITHMS = ["HS256"]  # reject anything else (no 'none', no alg confusion)

    # --- Upload limits -------------------------------------------------------
    # Flask returns 413 automatically when a request body exceeds this.
    MAX_CONTENT_LENGTH = _bytes_from_mb(10)

    # --- Object storage (MinIO / S3) -----------------------------------------
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
    MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "media")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "false").lower() == "true"
    # Public endpoint for browser-reachable presigned URLs (bonus). The internal
    # MINIO_ENDPOINT ("minio:9000") is unreachable from the browser.
    MINIO_PUBLIC_ENDPOINT = os.environ.get("MINIO_PUBLIC_ENDPOINT", "localhost:9000")
    # How long a presigned download link stays valid (expiring-link bonus).
    PRESIGNED_URL_EXPIRES = timedelta(
        minutes=int(os.environ.get("PRESIGNED_URL_EXPIRES_MINUTES", "15"))
    )

    # --- Validation whitelists ----------------------------------------------
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "txt"}
    ALLOWED_MIME_TYPES = {
        "image/png",
        "image/jpeg",
        "application/pdf",
        "text/plain",
    }
    # Map a sniffed MIME type back to the extension(s) it may legitimately carry,
    # so a renamed file (e.g. .png bytes uploaded as "x.pdf") is rejected.
    EXTENSION_MIME_MAP = {
        "png": {"image/png"},
        "jpg": {"image/jpeg"},
        "jpeg": {"image/jpeg"},
        "pdf": {"application/pdf"},
        "txt": {"text/plain"},
    }

    # --- Password policy -----------------------------------------------------
    PASSWORD_MIN_LENGTH = 10

    # --- Search --------------------------------------------------------------
    MEDIA_SEARCH_MAX_LENGTH = 100  # cap the ?q= term (schema-enforced)

    # --- CORS ----------------------------------------------------------------
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


class TestConfig(Config):
    """Used by pytest (conftest). In-memory SQLite, fixed secret, storage mocked."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key"
