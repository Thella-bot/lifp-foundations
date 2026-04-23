import os
import time
import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth import create_mock_token, verify_token, hash_uin

app = FastAPI(title="LIFP Identity Bridge", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.StrictRedis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
)

class TokenResponse(BaseModel):
    access_token: str
    internal_id: str
    token_type: str = "bearer"
    expires_in: int

class ConsentRequest(BaseModel):
    internal_id: str
    purpose: str
    valid_until: int

consent_store = {}

@app.get("/health")
def health():
    return {"status": "ok", "service": "identity"}

@app.get("/v1/auth/login", response_model=TokenResponse)
def login(uin: str = "USER_0001"):
    token = create_mock_token(uin)
    internal_id = hash_uin(uin)
    # Store in Redis with 1 h expiry
    redis_client.setex(f"auth:{internal_id}", 3600, token)
    return TokenResponse(
        access_token=token,
        internal_id=internal_id,
        expires_in=3600
    )

@app.post("/v1/consent/grant")
def grant_consent(req: ConsentRequest):
    consent_store[req.internal_id] = {
        "purpose": req.purpose,
        "valid_until": req.valid_until
    }
    return {"status": "consent_granted"}

@app.get("/v1/consent/check/{internal_id}")
def check_consent(internal_id: str):
    consent = consent_store.get(internal_id)
    if not consent or consent["valid_until"] < int(time.time()):
        return {"consent": False}
    return {"consent": True, "purpose": consent["purpose"]}

@app.get("/v1/verify")
def verify_access_token(token: str):
    try:
        claims = verify_token(token)
        return {"active": True, "internal_id": claims["sub"], "claims": claims}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")