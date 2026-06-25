"""HTTP route blueprints. The factory registers auth_bp at /auth and media_bp
at /media. Blueprints orchestrate: validate (schemas) -> enforce ownership ->
call services -> serialize. No storage/DB details leak in here.
"""
