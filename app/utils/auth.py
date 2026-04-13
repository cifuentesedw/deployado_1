from functools import wraps
from flask import request, current_app


def token_required(f):
    """
    Decorator that validates the static Bearer token sent in the
    Authorization header.

    Returns plain dicts so Flask-RESTful can serialise them correctly.

    Expected header format:
        Authorization: Bearer <STATIC_TOKEN>
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return (
                {"msg": "Token de autorización faltante o con formato incorrecto."},
                401,
            )

        token = auth_header.split(" ", 1)[1]
        expected = current_app.config.get("STATIC_TOKEN", "")

        if token != expected:
            return {"msg": "Token de autorización inválido."}, 403

        return f(*args, **kwargs)

    return decorated
