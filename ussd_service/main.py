"""
ussd_service/main.py
USSD Gateway — Africa's Talking integration.

Handles USSD sessions for feature-phone users.
Session state is kept in Redis (TTL = 120 s per session).
All scoring data fetched from ACSE via internal HTTP.

Menu:
  *123*LIFP#
  1. Check My Credit Score
  2. My Active Loans
  3. Apply for a Loan (redirects to agent)
  4. Nearest LIFP Agent
  0. Exit
"""
import json
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import httpx
import redis
from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ACSE_URL     = os.environ.get("ACSE_URL",     "http://acse_service:8001")
SERVICE_TOKEN = os.environ.get("SERVICE_TOKEN", "")   # pre-issued service JWT

redis_client = redis.StrictRedis.from_url(
    os.environ.get("REDIS_URL", "redis://redis:6379"),
    decode_responses=True,
)
SESSION_TTL = 120  # seconds

TIER_LABEL = {
    "A": "Excellent",
    "B": "Good",
    "C": "Fair",
    "D": "Poor - needs improvement",
    "E": "Very poor - high risk",
}

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="LIFP — USSD Gateway", version="1.0.0", lifespan=lifespan)

# ── Session helpers ───────────────────────────────────────────────────────────
def _session_key(session_id: str) -> str:
    return f"ussd:session:{session_id}"

def _get_session(session_id: str) -> dict:
    raw = redis_client.get(_session_key(session_id))
    return json.loads(raw) if raw else {}

def _set_session(session_id: str, data: dict) -> None:
    redis_client.setex(_session_key(session_id), SESSION_TTL, json.dumps(data))

def _clear_session(session_id: str) -> None:
    redis_client.delete(_session_key(session_id))

# ── ACSE helpers ──────────────────────────────────────────────────────────────
def _fetch_score(internal_id: str) -> Optional[dict]:
    """Call ACSE synchronously. Returns None on any failure."""
    if not SERVICE_TOKEN:
        return None
    try:
        r = httpx.post(
            f"{ACSE_URL}/v1/score",
            json={"internal_id": internal_id, "consent_token": SERVICE_TOKEN},
            timeout=5.0,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

# ── USSD response helpers ─────────────────────────────────────────────────────
def _con(text: str) -> PlainTextResponse:
    """CON — keep session alive."""
    return PlainTextResponse(f"CON {text}")

def _end(text: str) -> PlainTextResponse:
    """END — close session."""
    return PlainTextResponse(f"END {text}")

# ── Main endpoint ─────────────────────────────────────────────────────────────
@app.post("/ussd", response_class=PlainTextResponse)
async def ussd_callback(
    sessionId:   str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text:        str = Form(""),
):
    """
    Africa's Talking USSD callback.
    `text` is cumulative: each selection appended with '*'.
    e.g. first press "1" → text="1"
         then press "2" → text="1*2"
    """
    parts = [p.strip() for p in text.split("*") if p.strip()]
    session = _get_session(sessionId)

    # ── Level 0: Main menu ────────────────────────────────────────────────────
    if not parts:
        _set_session(sessionId, {"phone": phoneNumber})
        return _con(
            "Welcome to LIFP\n"
            "Lesotho Inclusive Finance Platform\n\n"
            "1. My Credit Score\n"
            "2. My Active Loans\n"
            "3. Apply for a Loan\n"
            "4. Find LIFP Agent\n"
            "0. Exit"
        )

    choice = parts[0]

    # ── 0: Exit ───────────────────────────────────────────────────────────────
    if choice == "0":
        _clear_session(sessionId)
        return _end("Thank you for using LIFP. Goodbye!")

    # ── 1: Credit Score ───────────────────────────────────────────────────────
    if choice == "1":
        # We use the phone number as a proxy internal_id lookup
        # In production: look up internal_id from a phone→internal_id mapping table
        internal_id = session.get("internal_id")
        if not internal_id:
            if len(parts) == 1:
                return _con("Enter your LIFP PIN to view your score:")
            pin = parts[1]
            # TODO: verify PIN against identity service
            # For pilot: treat phone hash as internal_id
            import hashlib
            internal_id = hashlib.sha256(f"{phoneNumber}:{pin}".encode()).hexdigest()
            session["internal_id"] = internal_id
            _set_session(sessionId, session)

        score_data = _fetch_score(internal_id)
        if score_data:
            score = score_data["score"]
            tier  = score_data["tier"]
            label = TIER_LABEL.get(tier, tier)
            return _end(
                f"Your LIFP Credit Score:\n\n"
                f"Score: {score} / 850\n"
                f"Rating: {tier} — {label}\n\n"
                f"Visit a PostBank branch or\n"
                f"LIFP agent for loan options.\n"
                f"Model v{score_data.get('model_version', '?')}"
            )
        else:
            return _end(
                "We could not retrieve your score.\n"
                "Please visit a LIFP agent or\n"
                "check back later."
            )

    # ── 2: My Loans ───────────────────────────────────────────────────────────
    if choice == "2":
        # Placeholder — wire to lender service in next milestone
        return _end(
            "Loan status lookup is available\n"
            "at any PostBank branch or via\n"
            "the LIFP app at lifp.co.ls"
        )

    # ── 3: Apply for a Loan ───────────────────────────────────────────────────
    if choice == "3":
        return _end(
            "To apply for a loan:\n\n"
            "1. Download the LIFP app:\n"
            "   lifp.co.ls\n\n"
            "2. Visit your nearest\n"
            "   PostBank branch with\n"
            "   your national ID."
        )

    # ── 4: Find Agent ─────────────────────────────────────────────────────────
    if choice == "4":
        if len(parts) == 1:
            return _con(
                "Select your district:\n"
                "1. Maseru\n"
                "2. Leribe\n"
                "3. Berea\n"
                "4. Mafeteng\n"
                "5. Other"
            )
        district_map = {
            "1": "Maseru: PostBank HQ, Kingsway St\nTel: +266 2231 2345",
            "2": "Leribe: PostBank Hlotse Branch\nTel: +266 2240 1234",
            "3": "Berea: PostBank Teyateyaneng\nTel: +266 2250 5678",
            "4": "Mafeteng: PostBank Mafeteng Br.\nTel: +266 2270 4321",
            "5": "Visit lifp.co.ls/agents\nfor all district locations.",
        }
        district = parts[1] if len(parts) > 1 else "5"
        return _end(f"Nearest LIFP Agent:\n\n{district_map.get(district, district_map['5'])}")

    # ── Fallback ──────────────────────────────────────────────────────────────
    _clear_session(sessionId)
    return _end("Invalid option. Please dial *123*LIFP# to start again.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "ussd"}
