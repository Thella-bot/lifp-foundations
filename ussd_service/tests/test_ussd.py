"""
ussd_service/tests/test_ussd.py
Tests for the USSD gateway.
Run: PYTHONPATH=. pytest ussd_service/tests/ -v
"""
import os, sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-padding!!")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Patch redis before import
import redis as _r
_r.StrictRedis.from_url = MagicMock(return_value=MagicMock(
    get=MagicMock(return_value=None),
    setex=MagicMock(),
    delete=MagicMock(),
))

from ussd_service.main import app

client = TestClient(app)

def _post(text="", session="sess-001", phone="+26650000001"):
    return client.post("/ussd", data={
        "sessionId": session,
        "serviceCode": "*123*LIFP#",
        "phoneNumber": phone,
        "text": text,
    })


def test_health():
    assert client.get("/health").status_code == 200


def test_main_menu():
    r = _post("")
    assert r.status_code == 200
    assert r.text.startswith("CON")
    assert "Credit Score" in r.text
    assert "Active Loans" in r.text


def test_exit():
    r = _post("0")
    assert r.text.startswith("END")
    assert "Goodbye" in r.text


def test_apply_redirects_to_app():
    r = _post("3")
    assert r.text.startswith("END")
    assert "lifp.co.ls" in r.text.lower() or "PostBank" in r.text


def test_agent_submenu():
    r = _post("4")
    assert r.text.startswith("CON")
    assert "Maseru" in r.text


def test_agent_district_selection():
    r = _post("4*1")
    assert r.text.startswith("END")
    assert "Maseru" in r.text


def test_invalid_option():
    r = _post("9")
    assert r.text.startswith("END")
    assert "Invalid" in r.text


def test_score_prompts_for_pin():
    r = _post("1")
    assert r.text.startswith("CON")
    assert "PIN" in r.text


def test_score_with_mock_acse():
    mock_score = {
        "score": 690, "tier": "B", "prob_default": 0.18,
        "model_version": "dummy-0.1.0", "factors": [],
    }
    with patch("ussd_service.main._fetch_score", return_value=mock_score):
        with patch("ussd_service.main._get_session",
                   return_value={"phone": "+26650000001", "internal_id": "abc123"}):
            r = _post("1*1234")
    assert r.text.startswith("END")
    assert "690" in r.text
    assert "Good" in r.text
