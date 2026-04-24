"""
identity_service/auth.py
Token creation and verification helpers.
Kept as a thin module so the production MOSIP OAuth2 flow can be wired here
without touching main.py.

CHANGES vs original:
  - UIN is never placed in JWT claims (was: {"uin": uin} — now removed)
  - create_mock_token renamed to create_access_token for clarity
  - verify_token uses shared.security so algorithm/key live in one place
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt

SECRET_KEY     = os.environ.get("SECRET_KEY")
ALGORITHM      = "HS256"
TOKEN_AUDIENCE = "lifp"
MOSIP_ISSUER   = os.environ.get("MOSIP_ISSUER", "https://mosip.lifp.co.ls")
EXPIRE_MINUTES = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "60"))


def create_access_token(internal_id: str, extra_claims: Optional[dict] = None) -> str:
    """
    Issue a signed JWT whose subject is internal_id (SHA-256 of UIN).
    The raw UIN is NEVER included in the payload.
    """
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set.")
    now = datetime.now(timezone.utc)
    payload = {
        "iss": MOSIP_ISSUER,
        "sub": internal_id,   # ← hashed ID only
        "aud": TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=EXPIRE_MINUTES),
    }
    if extra_claims:
        # Safety guard: never allow UIN to slip in via extra_claims
        extra_claims.pop("uin", None)
        payload.update(extra_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    """
    Decode and verify a LIFP JWT.  Raises jose.JWTError on failure.
    Callers should catch JWTError and translate to HTTP 403.
    """
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set.")
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], audience=TOKEN_AUDIENCE)
