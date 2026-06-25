"""Flask extension singletons.

These are created unbound (no app) so modules can import them without triggering
circular imports. The application factory (app/__init__.py) calls init_app() on
each one with the real app instance.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

# Database ORM + Alembic migrations
db = SQLAlchemy()
migrate = Migrate()

# JWT bearer-token auth
jwt = JWTManager()

# Cross-origin requests (browser SPA -> API)
cors = CORS()
