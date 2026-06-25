"""Auth schemas: registration (strong password), login, and user output.

Validation lives here so blueprints stay thin and the password policy is
enforced in ONE place (mirrored, not duplicated, on the frontend).
"""
import re

from flask import current_app
from marshmallow import (
    Schema,
    fields,
    validates,
    ValidationError,
    pre_load,
    EXCLUDE,
)

_LOWER_RE = re.compile(r"[a-z]")
_UPPER_RE = re.compile(r"[A-Z]")
_DIGIT_RE = re.compile(r"\d")
_SYMBOL_RE = re.compile(r"[^A-Za-z0-9]")

# Defense against bcrypt's 72-byte truncation and hash-DoS via huge inputs.
PASSWORD_MAX_LENGTH = 128

# Tiny common-password blocklist (case-insensitive). Not exhaustive — just
# stops the most obvious choices that still satisfy the character rules.
_COMMON_PASSWORDS = {
    "password1!", "password123!", "qwerty123!", "letmein123!",
    "admin123!@#", "welcome123!", "passw0rd!", "p@ssw0rd123",
}


def _normalize_email(data):
    if isinstance(data, dict) and isinstance(data.get("email"), str):
        return {**data, "email": data["email"].strip().lower()}
    return data


class RegisterSchema(Schema):
    class Meta:
        unknown = EXCLUDE  # ignore unexpected fields rather than 500

    email = fields.Email(
        required=True,
        error_messages={"required": "Email is required.",
                        "invalid": "Enter a valid email address."},
    )
    password = fields.String(
        required=True,
        load_only=True,
        error_messages={"required": "Password is required."},
    )

    @pre_load
    def normalize(self, data, **kwargs):
        return _normalize_email(data)

    @validates("password")
    def validate_password(self, value, **kwargs):
        min_len = current_app.config["PASSWORD_MIN_LENGTH"]
        missing = []
        if len(value) < min_len:
            missing.append(f"at least {min_len} characters")
        if len(value) > PASSWORD_MAX_LENGTH:
            raise ValidationError(
                f"Password must be at most {PASSWORD_MAX_LENGTH} characters."
            )
        if not _LOWER_RE.search(value):
            missing.append("a lowercase letter")
        if not _UPPER_RE.search(value):
            missing.append("an uppercase letter")
        if not _DIGIT_RE.search(value):
            missing.append("a digit")
        if not _SYMBOL_RE.search(value):
            missing.append("a symbol")
        if missing:
            raise ValidationError("Password must contain " + ", ".join(missing) + ".")
        if value.lower() in _COMMON_PASSWORDS:
            raise ValidationError("This password is too common; choose a different one.")


class LoginSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    email = fields.Email(required=True,
                         error_messages={"required": "Email is required.",
                                         "invalid": "Enter a valid email address."})
    # No strength rules on login — we only check credentials, not policy.
    password = fields.String(required=True, load_only=True,
                             error_messages={"required": "Password is required."})

    @pre_load
    def normalize(self, data, **kwargs):
        return _normalize_email(data)


class UserResponseSchema(Schema):
    """Public user shape — never includes password_hash."""
    id = fields.Integer(dump_only=True)
    email = fields.Email(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
