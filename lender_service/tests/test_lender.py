"""
lender_service/tests/test_lender.py
Tests for the Lender Dashboard API.

Run:  PYTHONPATH=. SECRET_KEY=testsecret pytest lender_service/tests/ -v
"""
import os, sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-padding!!")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "testdb")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lender_service.main import app
from shared.models import LoanApplication, User, CreditScore

client = TestClient(app)
SECRET_KEY = os.environ["SECRET_KEY"]

def _token(sub: str = "lender-001") -> str:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": sub, "aud": "lifp", "exp": now + timedelta(hours=1)},
        SECRET_KEY, algorithm="HS256",
    )

def _auth(sub="lender-001"):
    return {"Authorization": f"Bearer {_token(sub)}"}


def test_health():
    assert client.get("/health").status_code == 200


def test_applications_requires_auth():
    r = client.get("/v1/lender/applications")
    assert r.status_code == 422   # missing Authorization header


def test_applications_invalid_token():
    r = client.get("/v1/lender/applications",
                   headers={"Authorization": "Bearer notavalidtoken"})
    assert r.status_code == 401


def test_applications_empty():
    mock_db = MagicMock()
    mock_db.query.return_value.join.return_value.filter.return_value\
        .order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    with patch("lender_service.main.get_db", return_value=iter([mock_db])):
        r = client.get("/v1/lender/applications", headers=_auth())
    assert r.status_code == 200
    assert r.json() == []


def test_credit_report_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    with patch("lender_service.main.get_db", return_value=iter([mock_db])):
        r = client.get("/v1/lender/credit-report/unknown-id", headers=_auth())
    assert r.status_code == 404


def test_update_loan_status_invalid():
    mock_db = MagicMock()
    mock_loan = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_loan
    with patch("lender_service.main.get_db", return_value=iter([mock_db])):
        r = client.put("/v1/lender/loans/abc/status",
                       headers=_auth(),
                       json={"status": "flying"})
    assert r.status_code == 400


def test_update_loan_status_valid():
    mock_db = MagicMock()
    mock_loan = MagicMock()
    mock_loan.id = "loan-1"
    mock_loan.status = "pending"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_loan
    with patch("lender_service.main.get_db", return_value=iter([mock_db])):
        r = client.put("/v1/lender/loans/loan-1/status",
                       headers=_auth(),
                       json={"status": "approved"})
    assert r.status_code == 200
    assert r.json()["new_status"] == "approved"


def test_portfolio_empty():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    with patch("lender_service.main.get_db", return_value=iter([mock_db])):
        r = client.get("/v1/lender/portfolio", headers=_auth())
    assert r.status_code == 200
    body = r.json()
    assert body["total_applications"] == 0
    assert body["default_rate_pct"] == 0.0
