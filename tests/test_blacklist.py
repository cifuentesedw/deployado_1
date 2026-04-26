"""
Pruebas Unitarias — Blacklist Microservice
Frameworks: pytest + unittest (unittest.TestCase)

Ejecutar con:
    pytest tests/ -v
    python -m pytest tests/ -v --tb=short

Nota: Se usa SQLite en memoria como mock de la base de datos PostgreSQL.
No se requiere conexión a AWS RDS para ejecutar estas pruebas.
"""
import json
import os
import unittest

from app import create_app, db

# ── Configuración de pruebas ──────────────────────────────────────────────────
STATIC_TOKEN   = "deployado-12042026-token"
AUTH_HEADER    = {"Authorization": f"Bearer {STATIC_TOKEN}"}
INVALID_HEADER = {"Authorization": "Bearer token-invalido-xyz"}
TEST_UUID      = "550e8400-e29b-41d4-a716-446655440000"


class BaseTestCase(unittest.TestCase):
    """
    Clase base que configura la aplicación Flask con SQLite en memoria
    para cada test. Hereda de unittest.TestCase — compatible con pytest.
    """

    def setUp(self):
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["STATIC_TOKEN"] = STATIC_TOKEN

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _post_blacklist(self, email, uuid=TEST_UUID, reason="Spam", headers=None):
        if headers is None:
            headers = AUTH_HEADER
        payload = {"email": email, "app_uuid": uuid}
        if reason:
            payload["blocked_reason"] = reason
        return self.client.post(
            "/blacklists",
            data=json.dumps(payload),
            content_type="application/json",
            headers=headers,
        )


# ── Grupo 1: Health Check ─────────────────────────────────────────────────────

class TestHealthEndpoint(BaseTestCase):

    def test_health_returns_200(self):
        """GET /health debe retornar HTTP 200."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)

    def test_health_returns_json_with_status(self):
        """GET /health debe retornar JSON con status 'healthy'."""
        resp = self.client.get("/health")
        data = resp.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "blacklist-microservice")

    def test_health_no_requiere_autenticacion(self):
        """GET /health no debe requerir token de autorización."""
        resp = self.client.get("/health")
        self.assertNotIn(resp.status_code, [401, 403])


# ── Grupo 2: POST /blacklists ─────────────────────────────────────────────────

class TestPostBlacklists(BaseTestCase):

    def test_agregar_email_con_motivo_retorna_201(self):
        """POST /blacklists con datos válidos y motivo retorna 201 Created."""
        resp = self._post_blacklist("spam@test.com", reason="Envío masivo de spam")
        self.assertEqual(resp.status_code, 201)

    def test_agregar_email_respuesta_tiene_campos_requeridos(self):
        """La respuesta 201 debe incluir 'msg' y 'data' con campos mínimos."""
        resp = self._post_blacklist("campos@test.com")
        data = resp.get_json()
        self.assertIn("msg", data)
        self.assertIn("data", data)
        self.assertIn("email", data["data"])
        self.assertIn("id", data["data"])
        self.assertIn("request_ip", data["data"])
        self.assertIn("created_at", data["data"])

    def test_agregar_email_sin_motivo_retorna_201(self):
        """El campo blocked_reason es opcional. Sin él, retorna 201 y null."""
        resp = self._post_blacklist("sinmotivo@test.com", reason=None)
        self.assertEqual(resp.status_code, 201)
        self.assertIsNone(resp.get_json()["data"]["blocked_reason"])

    def test_email_se_normaliza_a_minusculas(self):
        """El email debe almacenarse en minúsculas."""
        resp = self._post_blacklist("MAYUSCULAS@TEST.COM")
        self.assertEqual(resp.get_json()["data"]["email"], "mayusculas@test.com")

    def test_email_formato_invalido_retorna_400(self):
        """Email con formato inválido debe retornar 400 Bad Request."""
        payload = {"email": "no-es-email", "app_uuid": TEST_UUID}
        resp = self.client.post(
            "/blacklists",
            data=json.dumps(payload),
            content_type="application/json",
            headers=AUTH_HEADER,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("email", resp.get_json()["errors"])

    def test_app_uuid_ausente_retorna_400(self):
        """El campo app_uuid es obligatorio. Sin él retorna 400."""
        payload = {"email": "test@example.com"}
        resp = self.client.post(
            "/blacklists",
            data=json.dumps(payload),
            content_type="application/json",
            headers=AUTH_HEADER,
        )
        self.assertEqual(resp.status_code, 400)

    def test_app_uuid_formato_invalido_retorna_400(self):
        """UUID con formato inválido retorna 400 Bad Request."""
        payload = {"email": "ok@example.com", "app_uuid": "no-es-uuid"}
        resp = self.client.post(
            "/blacklists",
            data=json.dumps(payload),
            content_type="application/json",
            headers=AUTH_HEADER,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("app_uuid", resp.get_json()["errors"])

    def test_blocked_reason_mayor_255_chars_retorna_400(self):
        """blocked_reason mayor a 255 caracteres retorna 400."""
        resp = self._post_blacklist("long@example.com", reason="x" * 256)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("blocked_reason", resp.get_json()["errors"])

    def test_email_duplicado_retorna_409(self):
        """Agregar el mismo email dos veces retorna 409 Conflict."""
        self._post_blacklist("dup@example.com")
        resp = self._post_blacklist("dup@example.com")
        self.assertEqual(resp.status_code, 409)
        self.assertIn("ya se encuentra", resp.get_json()["msg"])

    def test_sin_token_retorna_401(self):
        """POST sin header Authorization retorna 401 Unauthorized."""
        payload = {"email": "noauth@example.com", "app_uuid": TEST_UUID}
        resp = self.client.post(
            "/blacklists",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_token_invalido_retorna_403(self):
        """POST con Bearer Token incorrecto retorna 403 Forbidden."""
        resp = self._post_blacklist("badauth@example.com", headers=INVALID_HEADER)
        self.assertEqual(resp.status_code, 403)


# ── Grupo 3: GET /blacklists/<email> ─────────────────────────────────────────

class TestGetBlacklists(BaseTestCase):

    def setUp(self):
        super().setUp()
        self._post_blacklist("bloqueado@example.com", reason="Phishing detectado")

    def test_email_bloqueado_retorna_is_blacklisted_true(self):
        """GET email en lista negra retorna is_blacklisted: true y HTTP 200."""
        resp = self.client.get(
            "/blacklists/bloqueado@example.com", headers=AUTH_HEADER
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["is_blacklisted"])

    def test_email_bloqueado_incluye_motivo(self):
        """La respuesta para email bloqueado debe incluir el blocked_reason."""
        resp = self.client.get(
            "/blacklists/bloqueado@example.com", headers=AUTH_HEADER
        )
        self.assertEqual(resp.get_json()["blocked_reason"], "Phishing detectado")

    def test_email_no_bloqueado_retorna_is_blacklisted_false(self):
        """GET email no en lista negra retorna is_blacklisted: false y null."""
        resp = self.client.get(
            "/blacklists/limpio@example.com", headers=AUTH_HEADER
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["is_blacklisted"])
        self.assertIsNone(data["blocked_reason"])

    def test_consulta_incluye_campos_requeridos(self):
        """La respuesta GET debe incluir is_blacklisted, email, blocked_reason."""
        resp = self.client.get(
            "/blacklists/bloqueado@example.com", headers=AUTH_HEADER
        )
        data = resp.get_json()
        for campo in ["is_blacklisted", "email", "blocked_reason"]:
            self.assertIn(campo, data)

    def test_sin_token_retorna_401(self):
        """GET sin Authorization retorna 401 Unauthorized."""
        resp = self.client.get("/blacklists/bloqueado@example.com")
        self.assertEqual(resp.status_code, 401)

    def test_token_invalido_retorna_403(self):
        """GET con Bearer Token incorrecto retorna 403 Forbidden."""
        resp = self.client.get(
            "/blacklists/bloqueado@example.com", headers=INVALID_HEADER
        )
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
