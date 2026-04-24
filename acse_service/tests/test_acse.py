"""
acse_service/tests/test_acse.py
Unit + integration tests for the ACSE service.

Run from repo root:
  PYTHONPATH=. SECRET_KEY=testsecret pytest acse_service/tests/ -v
"""
import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# ── env vars must be set before importing the app ────────────────────────────
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-padding!!")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "testdb")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Patch redis before app import so no real Redis is needed in CI
import redis as _redis_mod
_redis_mod.StrictRedis.from_url = MagicMock(return_value=MagicMock(
    get=MagicMock(return_value=None),
    setex=MagicMock(return_value=True),
))

from acse_service.main import app   # noqa: E402 — must come after env setup
from shared.models import Feature, User

client = TestClient(app)

# ── Helpers ───────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ["SECRET_KEY"]
AUDIENCE   = "lifp"

def _make_token(internal_id: str) -> str:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": internal_id, "aud": AUDIENCE, "exp": now + timedelta(hours=1)},
        SECRET_KEY, algorithm="HS256",
    )

def _make_feature(internal_id: str = "test-user-hash") -> Feature:
    return Feature(
        internal_id=internal_id,
        user_type="individual",
        computed_at=datetime.now(timezone.utc),
        total_trans=50, freq_per_week=1.0, days_since_last=2.0,
        active_months=6.0, cash_in=5000.0, cash_out=3000.0,
        net_cash_flow=2000.0, ratio_out_in=0.6, avg_cash_in=833.0,
        avg_cash_out=500.0, std_amount=200.0,
        airtime_count=5.0, airtime_total=100.0, bill_count=3.0,
        bill_total=450.0, merchant_count=10.0, merchant_total=1000.0,
        airtime_ratio=0.03, merchant_ratio=0.33,
        max_gap=7.0, median_gap=3.5, trend_slope=0.02,
    )

# ── Tests ─────────────────────────────────────────────────────────────────────
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_model_health():
    r = client.get("/v1/model/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "loaded"
    assert body["feature_count"] > 0


def test_score_invalid_token():
    r = client.post("/v1/score", json={
        "internal_id": "some-id",
        "consent_token": "not-a-real-token",
    })
    assert r.status_code == 403


def test_score_short_token_rejected():
    """Old bug: any string >= 10 chars was accepted. Now a real JWT is required."""
    r = client.post("/v1/score", json={
        "internal_id": "some-id",
        "consent_token": "abcdefghij",   # 10 chars but not a JWT
    })
    assert r.status_code == 403


def test_score_returns_valid_structure():
    internal_id = "test-user-hash"
    token = _make_token(internal_id)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
        _make_feature(internal_id)
    )

    with patch("acse_service.main.get_db", return_value=iter([mock_db])):
        r = client.post("/v1/score", json={
            "internal_id": internal_id,
            "consent_token": token,
        })

    assert r.status_code == 200
    body = r.json()
    assert 300 <= body["score"] <= 850
    assert body["tier"] in ("A", "B", "C", "D", "E")
    assert 0.0 <= body["prob_default"] <= 1.0
    assert isinstance(body["factors"], list)
    assert body["model_version"] != ""
    # Verify SHAP factors are present and have correct structure
    if body["factors"]:
        assert "feature" in body["factors"][0]
        assert "shap_value" in body["factors"][0]


def test_redis_cache_is_valid_json():
    """Regression: cache must store JSON, not Python str() output."""
    internal_id = "cache-test-user"
    token = _make_token(internal_id)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
        _make_feature(internal_id)
    )

    captured = {}
    def mock_setex(key, ttl, value):
        captured["value"] = value

    with patch("acse_service.main.redis_client") as mock_redis:
        mock_redis.get.return_value = None
        mock_redis.setex.side_effect = mock_setex

        with patch("acse_service.main.get_db", return_value=iter([mock_db])):
            client.post("/v1/score", json={
                "internal_id": internal_id,
                "consent_token": token,
            })

    # Must parse as valid JSON — this would fail with str(result)
    parsed = json.loads(captured["value"])
    assert "score" in parsed


def test_batch_score_exceeds_limit():
    token = _make_token("svc-account")
    r = client.post("/v1/score/batch", json={
        "internal_ids": [f"user-{i}" for i in range(101)],
        "consent_token": token,
    })
    assert r.status_code == 400


def test_batch_score_valid():
    token = _make_token("svc-account")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = (
        _make_feature("u1")
    )
    with patch("acse_service.main.get_db", return_value=iter([mock_db])):
        r = client.post("/v1/score/batch", json={
            "internal_ids": ["u1"],
            "consent_token": token,
        })
    assert r.status_code == 200
    assert isinstance(r.json(), list)
