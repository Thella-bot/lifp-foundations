"""
identity_service/main.py
Identity bridge for mock e-KYC and consent management.
"""

import hashlib
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from identity_service.auth import create_access_token, verify_token
from shared.db import engine, get_db
from shared.models import Base, Consent, User

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set.")

_raw_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="LIFP - Identity Bridge", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def _hash_uin(uin: str) -> str:
    return hashlib.sha256(uin.encode()).hexdigest()


def _require_internal_id_from_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required.")

    try:
        claims = verify_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
    return claims["sub"]


class MockLoginRequest(BaseModel):
    uin: str
    user_type: Literal["msme", "individual"] = "individual"


class TokenResponse(BaseModel):
    access_token: str
    internal_id: str
    token_type: str = "bearer"


class ConsentRequest(BaseModel):
    purpose: str
    valid_days: int = 365


class ConsentRevoke(BaseModel):
    purpose: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "identity"}


@app.post("/v1/auth/token", response_model=TokenResponse)
def mock_login(request: MockLoginRequest, db: Session = Depends(get_db)):
    uin = request.uin.strip()
    if len(uin) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="uin is too short")

    internal_id = _hash_uin(uin)

    user = db.query(User).filter(User.internal_id == internal_id).first()
    if not user:
        user = User(internal_id=internal_id, user_type=request.user_type)
        db.add(user)
        db.commit()

    token = create_access_token(internal_id)
    return TokenResponse(access_token=token, internal_id=internal_id)


@app.post("/v1/consent/grant")
def grant_consent(
    request: ConsentRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    internal_id = _require_internal_id_from_token(authorization)
    now = datetime.now(timezone.utc)
    valid_until = now + timedelta(days=request.valid_days)

    consent = (
        db.query(Consent)
        .filter(Consent.internal_id == internal_id, Consent.purpose == request.purpose)
        .first()
    )
    if consent:
        consent.granted = True
        consent.granted_at = now
        consent.valid_until = valid_until
        consent.revoked_at = None
    else:
        consent = Consent(
            internal_id=internal_id,
            purpose=request.purpose,
            granted=True,
            granted_at=now,
            valid_until=valid_until,
        )
        db.add(consent)

    db.commit()
    return {"message": f"Consent granted for '{request.purpose}'", "valid_until": valid_until}


@app.post("/v1/consent/revoke")
def revoke_consent(
    request: ConsentRevoke,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    internal_id = _require_internal_id_from_token(authorization)
    now = datetime.now(timezone.utc)

    consent = (
        db.query(Consent)
        .filter(Consent.internal_id == internal_id, Consent.purpose == request.purpose)
        .first()
    )
    if not consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent record not found.")

    consent.granted = False
    consent.revoked_at = now
    db.commit()
    return {"message": f"Consent for '{request.purpose}' revoked."}


@app.get("/v1/consent/status")
def consent_status(
    purpose: str,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    internal_id = _require_internal_id_from_token(authorization)
    now = datetime.now(timezone.utc)

    consent = (
        db.query(Consent)
        .filter(
            Consent.internal_id == internal_id,
            Consent.purpose == purpose,
            Consent.granted.is_(True),
            Consent.valid_until > now,
            Consent.revoked_at.is_(None),
        )
        .first()
    )
    return {"has_consent": bool(consent)}
