"""
identity_service/tests/test_identity.py
Tests for the identity / e-KYC service.

Run from repo root:
  PYTHONPATH=. SECRET_KEY=testsecret pytest identity_service/tests/ -v
"""
import hashlib
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-padding!!")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "testdb")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from identity_service.main import app   # noqa: E402
from identity_service.auth import create_access_token, verify_token

client = TestClient(app)

# ── Auth module tests ─────────────────────────────────────────────────────────

def test_token_does_not_contain_uin():
    """Critical security test: UIN must never appear in JWT payload."""
    uin = "LS123456789"
    internal_id = hashlib.sha256(uin.encode()).hexdigest()
    token = create_access_token(internal_id)
    claims = verify_token(token)

    assert "uin" not in claims, "RAW UIN FOUND IN JWT — security violation!"
    assert claims["sub"] == internal_id
    assert claims["aud"] == "lifp"


def test_token_extra_claims_cannot_inject_uin():
    """Extra claims must not be able to smuggle the UIN in."""
    internal_id = "some-hash"
    token = create_access_token(internal_id, extra_claims={"uin": "LS000000"})
    claims = verify_token(token)
    assert "uin" not in claims


def test_token_subject_is_hashed_not_raw():
    """sub field should look like a hex SHA-256, not a short ID number."""
    uin = "LS987654321"
    internal_id = hashlib.sha256(uin.encode()).hexdigest()
    token = create_access_token(internal_id)
    claims = verify_token(token)
    assert len(claims["sub"]) == 64   # SHA-256 hex = 64 chars
    assert claims["sub"] != uin


# ── Endpoint tests ────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200


def test_mock_login_returns_token_not_uin():
    """Login response must include internal_id (hashed), never the raw UIN."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    with patch("identity_service.main.get_db", return_value=iter([mock_db])):
        r = client.post("/v1/auth/token", json={"uin": "LS123456", "user_type": "individual"})

    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "internal_id" in body
    # The response must not echo the UIN back
    assert "LS123456" not in str(body)
    # internal_id should be a 64-char hex string
    assert len(body["internal_id"]) == 64


def test_mock_login_msme():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with patch("identity_service.main.get_db", return_value=iter([mock_db])):
        r = client.post("/v1/auth/token", json={"uin": "LS000001", "user_type": "msme"})
    assert r.status_code == 200


def test_consent_grant():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    token = create_access_token("abc123")
    with patch("identity_service.main.get_db", return_value=iter([mock_db])):
        r = client.post(
            "/v1/consent/grant",
            headers={"Authorization": f"Bearer {token}"},
            json={"purpose": "credit_scoring", "valid_days": 365},
        )
    assert r.status_code == 200
    assert "granted" in r.json()["message"]


def test_consent_revoke_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    token = create_access_token("abc123")
    with patch("identity_service.main.get_db", return_value=iter([mock_db])):
        r = client.post(
            "/v1/consent/revoke",
            headers={"Authorization": f"Bearer {token}"},
            json={"purpose": "credit_scoring"},
        )
    assert r.status_code == 404
