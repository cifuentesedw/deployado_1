"""
Tests for the Blacklist Microservice.

Run with:
    pytest tests/ -v
"""
import pytest
import json
from app import create_app, db


STATIC_TOKEN = "my-super-secret-static-token-2024"
AUTH_HEADER = {"Authorization": f"Bearer {STATIC_TOKEN}"}
INVALID_HEADER = {"Authorization": "Bearer invalid-token"}


@pytest.fixture(scope="function")
def app():
    """Create a fresh Flask app with an in-memory SQLite DB for each test."""
    import os
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["STATIC_TOKEN"] = STATIC_TOKEN

    application = create_app()
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Health check ──────────────────────────────────────────────────────────────

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


# ── POST /blacklists ──────────────────────────────────────────────────────────

def test_add_email_success(client):
    payload = {
        "email": "test@example.com",
        "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "blocked_reason": "Spam",
    }
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert "exitosamente" in data["msg"]
    assert data["data"]["email"] == "test@example.com"


def test_add_email_without_reason(client):
    payload = {
        "email": "noreason@example.com",
        "app_uuid": "550e8400-e29b-41d4-a716-446655440001",
    }
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 201


def test_add_email_duplicate(client):
    payload = {
        "email": "dup@example.com",
        "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
    }
    client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 409


def test_add_email_missing_fields(client):
    payload = {"email": "bad@example.com"}   # missing app_uuid
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 400


def test_add_email_invalid_uuid(client):
    payload = {
        "email": "test2@example.com",
        "app_uuid": "not-a-valid-uuid",
    }
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 400


def test_add_email_reason_too_long(client):
    payload = {
        "email": "long@example.com",
        "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "blocked_reason": "x" * 256,
    }
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    assert resp.status_code == 400


def test_add_email_no_token(client):
    payload = {
        "email": "noauth@example.com",
        "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
    }
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_add_email_invalid_token(client):
    payload = {
        "email": "badauth@example.com",
        "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
    }
    resp = client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=INVALID_HEADER,
    )
    assert resp.status_code == 403


# ── GET /blacklists/<email> ───────────────────────────────────────────────────

def test_check_blacklisted_email(client):
    # First add the email
    payload = {
        "email": "check@example.com",
        "app_uuid": "550e8400-e29b-41d4-a716-446655440000",
        "blocked_reason": "Phishing",
    }
    client.post(
        "/blacklists",
        data=json.dumps(payload),
        content_type="application/json",
        headers=AUTH_HEADER,
    )
    # Now check it
    resp = client.get("/blacklists/check@example.com", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_blacklisted"] is True
    assert data["blocked_reason"] == "Phishing"


def test_check_non_blacklisted_email(client):
    resp = client.get("/blacklists/notblacklisted@example.com", headers=AUTH_HEADER)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_blacklisted"] is False
    assert data["blocked_reason"] is None


def test_check_email_no_token(client):
    resp = client.get("/blacklists/noauth@example.com")
    assert resp.status_code == 401


def test_check_email_invalid_token(client):
    resp = client.get(
        "/blacklists/badtoken@example.com", headers=INVALID_HEADER
    )
    assert resp.status_code == 403
