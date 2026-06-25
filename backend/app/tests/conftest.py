"""Shared pytest fixtures.

The app runs on SQLite in-memory with storage fully mocked (no MinIO needed),
so the suite is hermetic and fast. Sample files are generated in-process.
"""
import io
import uuid

import pytest
from PIL import Image

from app import create_app
from app.config import TestConfig
from app.extensions import db as _db
from app.services import storage as storage_service


class _FakeMinioResponse:
    """Stand-in for MinIO's urllib3 response: supports stream/close/release_conn."""
    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)

    def stream(self, chunk_size=8192):
        while True:
            chunk = self._buf.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def close(self):
        pass

    def release_conn(self):
        pass


@pytest.fixture
def app(monkeypatch):
    application = create_app(TestConfig)

    # In-memory object store replacing MinIO. Keyed by storage_key -> bytes.
    store = {}

    def fake_put(key, stream, length, content_type):
        store[key] = stream.read()

    def fake_open(key):
        if key not in store:
            raise FileNotFoundError(key)
        return _FakeMinioResponse(store[key])

    def fake_delete(key):
        store.pop(key, None)

    def fake_presign(key, expires=None):
        return f"http://minio.local/{key}?signed=1"

    monkeypatch.setattr(storage_service, "put_object", fake_put)
    monkeypatch.setattr(storage_service, "open_stream", fake_open)
    monkeypatch.setattr(storage_service, "delete_object", fake_delete)
    monkeypatch.setattr(storage_service, "presign_get", fake_presign)
    monkeypatch.setattr(storage_service, "ensure_bucket", lambda: None)
    # build_key is pure (uuid only) — keep the real one.

    application.object_store = store  # exposed for assertions

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def object_store(app):
    return app.object_store


@pytest.fixture
def make_user(client):
    """Register a user and return ready-to-use auth headers."""
    def _make(email=None, password="StrongPass1!"):
        email = email or f"user_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post("/auth/register", json={"email": email, "password": password})
        assert resp.status_code == 201, resp.get_json()
        token = resp.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _make


@pytest.fixture
def auth_headers(make_user):
    return make_user()


# --- Sample file generators ---------------------------------------------------

def png_bytes(color="red", size=(16, 16)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def jpeg_bytes(color="blue", size=(16, 16)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def pdf_bytes() -> bytes:
    # Minimal but valid-enough PDF: starts with the %PDF- marker.
    return b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def txt_bytes() -> bytes:
    return "hello vault\nsecond line\n".encode("utf-8")


@pytest.fixture
def samples():
    """Valid files plus a forged one (text bytes wearing a .png name)."""
    return {
        "png": ("photo.png", png_bytes()),
        "jpg": ("photo.jpg", jpeg_bytes()),
        "pdf": ("doc.pdf", pdf_bytes()),
        "txt": ("note.txt", txt_bytes()),
        "forged_png": ("evil.png", b"this is not really an image"),
    }


def upload_data(filename, data, title="t", description="d"):
    """Build multipart form data for the test client."""
    return {
        "file": (io.BytesIO(data), filename),
        "title": title,
        "description": description,
    }
