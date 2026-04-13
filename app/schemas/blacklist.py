from marshmallow import fields, validate, validates, ValidationError
import re

from app import ma
from app.models.blacklist import BlacklistEntry


class BlacklistEntrySchema(ma.SQLAlchemyAutoSchema):
    """Schema completo — serializa entradas devueltas al cliente."""

    class Meta:
        model = BlacklistEntry
        load_instance = True
        include_fk = True

    id = fields.Int(dump_only=True)
    email = fields.Email(required=True)
    app_uuid = fields.Str(required=True)
    blocked_reason = fields.Str(
        required=False,
        allow_none=True,
        validate=validate.Length(max=255),
    )
    request_ip = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="%Y-%m-%dT%H:%M:%S")


class BlacklistCreateSchema(ma.Schema):
    """Schema de entrada — valida el body del POST /blacklists."""

    email = fields.Email(
        required=True,
        error_messages={"required": "El campo email es obligatorio."},
    )
    app_uuid = fields.Str(
        required=True,
        error_messages={"required": "El campo app_uuid es obligatorio."},
    )
    blocked_reason = fields.Str(
        required=False,
        allow_none=True,
        load_default=None,
        validate=validate.Length(
            max=255, error="El motivo no puede superar 255 caracteres."
        ),
    )

    @validates("app_uuid")
    def validate_uuid(self, value, **kwargs):   # <-- **kwargs requerido en Marshmallow 3.x nuevo
        uuid_regex = re.compile(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )
        if not uuid_regex.match(value):
            raise ValidationError(
                "app_uuid debe ser un UUID válido "
                "(formato xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)."
            )


class BlacklistCheckSchema(ma.Schema):
    """Schema de salida — respuesta del GET /blacklists/<email>."""

    is_blacklisted = fields.Bool()
    blocked_reason = fields.Str(allow_none=True)


blacklist_entry_schema = BlacklistEntrySchema()
blacklist_create_schema = BlacklistCreateSchema()
blacklist_check_schema = BlacklistCheckSchema()
