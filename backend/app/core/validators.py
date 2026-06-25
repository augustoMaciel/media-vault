"""Upload validation — the security gate for every uploaded file.

Threat model: an attacker tries to smuggle an executable/script (a "shell") past
us by lying about the file. They can lie in three places, and we trust NONE of
them:
  * the client-sent Content-Type header   -> ignored entirely
  * the filename extension                 -> cross-checked against real content
  * the magic-byte header                  -> not sufficient alone (polyglots),
                                              so each type is DEEP-validated

Only genuine .png/.jpg/.jpeg/.pdf/.txt files pass. Images must fully parse with
Pillow (defeats header-only polyglots and is bomb-guarded); PDFs must start with
the %PDF marker; .txt must be entirely text (no NUL/binary smuggling).

`filetype` is used for the first-pass sniff (pure-Python, no libmagic needed).
"""
import os

import filetype
from flask import current_app
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

# Bytes read from the front of the file for the first-pass content sniff.
_SNIFF_SIZE = 2048

# Allowed image extensions -> the Pillow format string they MUST decode to.
_IMAGE_FORMATS = {"png": "PNG", "jpg": "JPEG", "jpeg": "JPEG"}

# Reject absurd pixel dimensions in a small file (decompression bomb).
Image.MAX_IMAGE_PIXELS = 64_000_000  # ~64 megapixels


def _extension(filename: str) -> str:
    """Lower-case extension without the dot ('photo.JPG' -> 'jpg')."""
    return os.path.splitext(filename)[1].lower().lstrip(".")


def _file_size(file_storage) -> int:
    """Size in bytes via seek, restoring the stream position to the start."""
    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    return size


def _assert_valid_image(file_storage, ext):
    """Fully decode the image with Pillow. Header-only polyglots fail here."""
    stream = file_storage.stream
    stream.seek(0)
    try:
        with Image.open(stream) as img:
            fmt = (img.format or "").upper()
            img.verify()  # checks structural integrity (e.g. PNG CRCs), not just the header
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise BadRequest("File is not a valid image.")
    finally:
        stream.seek(0)

    if fmt != _IMAGE_FORMATS[ext]:
        raise BadRequest(
            f"Image content ({fmt or 'unknown'}) does not match its '.{ext}' extension."
        )


def _assert_valid_pdf(file_storage):
    """A real PDF begins with the '%PDF-' marker."""
    stream = file_storage.stream
    stream.seek(0)
    head = stream.read(5)
    stream.seek(0)
    if head != b"%PDF-":
        raise BadRequest("File is not a valid PDF.")


def _assert_valid_text(file_storage):
    """The ENTIRE file must be UTF-8 text with no NUL/binary bytes."""
    stream = file_storage.stream
    stream.seek(0)
    data = stream.read()
    stream.seek(0)
    if b"\x00" in data:
        raise BadRequest("File is not valid text.")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        raise BadRequest("File is not valid UTF-8 text.")


def validate_upload(file_storage):
    """Validate an uploaded FileStorage. Returns (mime_type, size_bytes, safe_name).

    Raises BadRequest (400) for a missing file, a bad/forged type, or content
    that fails its type's deep check; RequestEntityTooLarge (413) if over 10MB.

    NOTE: file_storage.content_type (client-supplied) is intentionally NOT read.
    """
    if file_storage is None or not file_storage.filename:
        raise BadRequest("No file was provided.")

    cfg = current_app.config
    allowed_ext = cfg["ALLOWED_EXTENSIONS"]
    ext_mime_map = cfg["EXTENSION_MIME_MAP"]
    max_bytes = cfg["MAX_CONTENT_LENGTH"]

    # 1) Extension whitelist (cheap reject before reading bytes).
    ext = _extension(file_storage.filename)
    if ext not in allowed_ext:
        raise BadRequest(
            f"Unsupported file type '.{ext}'. Allowed: "
            f"{', '.join(sorted(allowed_ext))}."
        )

    # 2) Size cap (defense in depth; MAX_CONTENT_LENGTH also auto-413s the body).
    size = _file_size(file_storage)
    if size == 0:
        raise BadRequest("The file is empty.")
    if size > max_bytes:
        raise RequestEntityTooLarge("File exceeds the 10MB limit.")

    # 3) First-pass sniff of the real type, independent of filename/Content-Type.
    head = file_storage.stream.read(_SNIFF_SIZE)
    file_storage.stream.seek(0)
    kind = filetype.guess(head)
    if kind is not None:
        sniffed_mime = kind.mime
    elif ext == "txt":
        sniffed_mime = "text/plain"  # text has no magic signature; deep-checked below
    else:
        raise BadRequest("Could not verify the file's type from its contents.")

    # 4) Sniffed type must be legitimate for the claimed extension.
    if sniffed_mime not in ext_mime_map.get(ext, set()):
        raise BadRequest(
            f"File content ({sniffed_mime}) does not match its '.{ext}' extension."
        )

    # 5) DEEP validation per type — defeats header-only polyglots/shells.
    if ext in _IMAGE_FORMATS:
        _assert_valid_image(file_storage, ext)
    elif ext == "pdf":
        _assert_valid_pdf(file_storage)
    elif ext == "txt":
        _assert_valid_text(file_storage)

    safe_name = secure_filename(file_storage.filename) or f"upload.{ext}"
    return sniffed_mime, size, safe_name
