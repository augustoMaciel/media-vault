"""Thumbnail generation (image-preview bonus).

Pure transform: bytes in -> small PNG bytes out, or None when the source isn't a
supported image. The media blueprint calls make_thumbnail() on upload and, if it
gets bytes back, stores them via storage.put_object under thumbnail_key.
Keeping this isolated means dropping the bonus later is a one-file change.
"""
from io import BytesIO

from PIL import Image

# Max bounding box for a thumbnail; aspect ratio is preserved.
THUMBNAIL_SIZE = (320, 320)
THUMBNAIL_MIME = "image/png"

# Only raster images get thumbnails (PDF/TXT do not).
_THUMBNAILABLE = {"image/png", "image/jpeg"}


def make_thumbnail(image_bytes: bytes, mime_type: str):
    """Return PNG thumbnail bytes for a supported image, else None.

    Never raises: a corrupt/odd image simply yields None so the upload still
    succeeds without a preview.
    """
    if mime_type not in _THUMBNAILABLE:
        return None
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            img.thumbnail(THUMBNAIL_SIZE)
            out = BytesIO()
            img.save(out, format="PNG")
            return out.getvalue()
    except Exception:
        return None


def thumbnail_key_for(storage_key: str) -> str:
    """Derive the thumbnail's storage key from the original's key.

    '<owner>/<uuid>.<ext>' -> '<owner>/<uuid>.thumb.png' (same owner prefix, so
    per-user isolation holds for thumbnails too).
    """
    base = storage_key.rsplit(".", 1)[0]
    return f"{base}.thumb.png"
