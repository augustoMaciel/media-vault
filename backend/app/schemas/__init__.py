"""marshmallow schemas: request validation + response serialization.

Kept separate from models so the HTTP contract (what clients send/receive) is
decoupled from the DB shape. Blueprints load/dump through these.
"""
