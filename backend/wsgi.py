"""WSGI entrypoint.

Gunicorn serves `wsgi:app`, and the `flask` CLI (db migrate/upgrade) discovers
the app here via FLASK_APP=wsgi.
"""
from app import create_app

app = create_app()
