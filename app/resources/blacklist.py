from flask import request, jsonify, current_app
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.blacklist import BlacklistEntry
from app.schemas.blacklist import (
    blacklist_create_schema,
    blacklist_entry_schema,
    blacklist_check_schema,
)
from app.utils.auth import token_required


def _get_client_ip():
    """Resolve the real client IP, respecting common proxy headers."""
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


class BlacklistResource(Resource):
    """
    POST /blacklists
    ─────────────────────────────────────────────────────
    Adds an email address to the global blacklist.

    Body (JSON):
        email        (str, required)  – email to blacklist
        app_uuid     (str, required)  – UUID of the requesting application
        blocked_reason (str, optional) – reason (max 255 chars)

    Headers:
        Authorization: Bearer <token>
    """

    @token_required
    def post(self):
        json_data = request.get_json(silent=True)

        if not json_data:
            return {"msg": "El cuerpo de la solicitud debe ser JSON válido."}, 400

        # ── Validate / deserialise input ──────────────────────────────────────
        try:
            data = blacklist_create_schema.load(json_data)
        except ValidationError as err:
            return {"msg": "Datos de entrada inválidos.", "errors": err.messages}, 400

        email = data["email"].lower().strip()
        app_uuid = data["app_uuid"]
        blocked_reason = data.get("blocked_reason")
        request_ip = _get_client_ip()

        # ── Check for duplicates ──────────────────────────────────────────────
        existing = BlacklistEntry.query.filter_by(email=email).first()
        if existing:
            return {
                "msg": f"El email '{email}' ya se encuentra en la lista negra global.",
                "email": email,
            }, 409

        # ── Persist ───────────────────────────────────────────────────────────
        entry = BlacklistEntry(
            email=email,
            app_uuid=app_uuid,
            blocked_reason=blocked_reason,
            request_ip=request_ip,
        )

        try:
            db.session.add(entry)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {
                "msg": f"El email '{email}' ya se encuentra en la lista negra global.",
                "email": email,
            }, 409
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error("DB error on blacklist POST: %s", exc)
            return {"msg": "Error interno al guardar la entrada."}, 500

        return {
            "msg": f"El email '{email}' fue agregado exitosamente a la lista negra global.",
            "data": blacklist_entry_schema.dump(entry),
        }, 201


class BlacklistCheckResource(Resource):
    """
    GET /blacklists/<email>
    ─────────────────────────────────────────────────────
    Returns whether an email address is in the global blacklist and the
    reason it was added (if any).

    Path parameter:
        email  (str) – email address to query

    Headers:
        Authorization: Bearer <token>
    """

    @token_required
    def get(self, email):
        email = email.lower().strip()

        entry = BlacklistEntry.query.filter_by(email=email).first()

        if entry:
            return {
                "is_blacklisted": True,
                "email": email,
                "blocked_reason": entry.blocked_reason,
                "app_uuid": entry.app_uuid,
                "created_at": entry.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
            }, 200

        return {
            "is_blacklisted": False,
            "email": email,
            "blocked_reason": None,
        }, 200
