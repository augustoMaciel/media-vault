"""Application factory.

Keep this THIN: create the app, load config, wire extensions, register
blueprints and error handlers, expose /health. No business logic here.
"""
from flask import Flask, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.extensions import db, migrate, jwt, cors


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Extensions ----------------------------------------------------------
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}})

    # Ensure models are registered on db.metadata so migrations see them.
    from app import models  # noqa: F401

    # --- Blueprints ----------------------------------------------------------
    from app.blueprints.auth import auth_bp
    from app.blueprints.media import media_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(media_bp, url_prefix="/media")

    # --- Health check --------------------------------------------------------
    @app.get("/health")
    def health():
        return {"status": "ok"}

    # --- JSON error handlers -------------------------------------------------
    register_error_handlers(app)

    return app


def register_error_handlers(app):
    """Return JSON (not HTML) for the errors clients will actually hit."""

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify(error="bad_request", message=str(getattr(err, "description", err))), 400

    @app.errorhandler(401)
    def unauthorized(err):
        return jsonify(error="unauthorized", message="Authentication required."), 401

    @app.errorhandler(404)
    def not_found(err):
        return jsonify(error="not_found", message="Resource not found."), 404

    @app.errorhandler(413)
    def too_large(err):
        return jsonify(error="payload_too_large", message="File exceeds the 10MB limit."), 413

    @app.errorhandler(ValidationError)
    def validation_error(err):
        # marshmallow raised in a route -> uniform 400 with field messages.
        return jsonify(error="validation_error", messages=err.messages), 400

    @app.errorhandler(500)
    def server_error(err):
        return jsonify(error="server_error", message="An unexpected error occurred."), 500

    @app.errorhandler(Exception)
    def unhandled(err):
        # HTTP errors (404/405/…) keep their own JSON handlers; anything else
        # (e.g. storage/MinIO failure) returns JSON 500 instead of an HTML page.
        if isinstance(err, HTTPException):
            return err
        app.logger.exception("Unhandled exception")
        return jsonify(error="server_error", message="An unexpected error occurred."), 500
