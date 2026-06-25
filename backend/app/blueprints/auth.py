"""Auth routes: register, login, me. Registered at /auth."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import User
from app.core.security import hash_password, verify_password, make_token, current_user_id
from app.schemas.auth import RegisterSchema, LoginSchema, UserResponseSchema

auth_bp = Blueprint("auth", __name__)

_user_out = UserResponseSchema()

# Pre-computed hash used to equalize timing when an email doesn't exist, so
# login response time doesn't reveal whether an account is registered.
_DUMMY_HASH = hash_password("timing-equalizer-not-a-real-password")


@auth_bp.post("/register")
def register():
    data = RegisterSchema().load(request.get_json(silent=True) or {})

    # Email uniqueness -> 409 (not a generic 400) so the client can react.
    if User.query.filter_by(email=data["email"]).first() is not None:
        return jsonify(error="email_exists",
                       message="An account with this email already exists."), 409

    user = User(email=data["email"], password_hash=hash_password(data["password"]))
    db.session.add(user)
    db.session.commit()

    # Auto-login: hand back a token so the SPA goes straight to the vault.
    token = make_token(user.id)
    return jsonify(access_token=token, user=_user_out.dump(user)), 201


@auth_bp.post("/login")
def login():
    data = LoginSchema().load(request.get_json(silent=True) or {})

    user = User.query.filter_by(email=data["email"]).first()
    if user is None:
        # Burn the same work as a real verify to avoid user-enumeration timing.
        verify_password(data["password"], _DUMMY_HASH)
        return _invalid_credentials()
    if not verify_password(data["password"], user.password_hash):
        return _invalid_credentials()

    token = make_token(user.id)
    return jsonify(access_token=token, user=_user_out.dump(user)), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, current_user_id())
    if user is None:
        # Valid token, but the user no longer exists.
        return jsonify(error="not_found", message="User not found."), 404
    return jsonify(_user_out.dump(user)), 200


def _invalid_credentials():
    # Generic message — never reveal which of email/password was wrong.
    return jsonify(error="invalid_credentials",
                   message="Invalid email or password."), 401
