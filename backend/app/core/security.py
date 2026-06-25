"""Security primitives: password hashing and JWT identity helpers.

Hashing uses passlib's bcrypt (constant-time verification, per-hash salt).
JWTs are signed with HMAC-SHA256 (HS256) over JWT_SECRET_KEY; the algorithm is
pinned in config.py (JWT_ALGORITHM / JWT_DECODE_ALGORITHMS) to block
algorithm-confusion and 'alg:none' attacks. Hashes are never logged or returned.
"""
from passlib.context import CryptContext
from flask_jwt_extended import create_access_token, get_jwt_identity

# Single bcrypt context for the whole app.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    """Return a bcrypt hash for a plaintext password."""
    return _pwd_context.hash(plaintext)


def verify_password(plaintext: str, password_hash: str) -> bool:
    """Constant-time check of a plaintext against a stored bcrypt hash."""
    return _pwd_context.verify(plaintext, password_hash)


def make_token(user_id: int) -> str:
    """Issue a JWT access token (HS256) whose identity is the user id.

    JWT 'sub' must be a string, so we stringify here and parse back in
    current_user_id().
    """
    return create_access_token(identity=str(user_id))


def current_user_id() -> int:
    """Return the authenticated user's id from the JWT (int)."""
    return int(get_jwt_identity())
