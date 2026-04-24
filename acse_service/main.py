"""
acse_service/main.py  — Alternative Credit Scoring Engine
Fixes vs original:
  - Redis cache stores valid JSON (not Python str())
  - Consent token properly verified via shared JWT library (not len() check)
  - Duplicate Feature ORM removed; imported from shared.models
  - Batch scoring endpoint added  POST /v1/score/batch
  - Model health endpoint         GET  /v1/model/health
  - Deprecated @app.on_event replaced with lifespan context manager
  - CORS locked to configurable env var (not hardcoded wildcard)
  - No default credentials in DATABASE_URL fallback
"""
import json
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

import redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db import get_db
from shared.models import Feature
from shared.security import verify_access_token
from model import model_manager

# ── Redis ────────────────────────────────────────────────────────────────────
redis_client = redis.StrictRedis.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True,
)
SCORE_CACHE_TTL = int(os.environ.get("SCORE_CACHE_TTL", "3600"))

# ── CORS ─────────────────────────────────────────────────────────────────────
_raw_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_origins.split(",")]

# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    model_manager.load()
    yield

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="LIFP — ACSE", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────
class ScoreRequest(BaseModel):
    internal_id: str
    consent_token: str

class ScoreResponse(BaseModel):
    internal_id: str
    score: int
    tier: str
    prob_default: float
    model_version: str
    factors: list

class BatchScoreRequest(BaseModel):
    internal_ids: List[str]
    consent_token: str  # service-level token issued to the lender dashboard

class ModelHealthResponse(BaseModel):
    model_version: str
    feature_count: int
    status: str

# ── Helpers ───────────────────────────────────────────────────────────────────
def _validate_consent(token: str, expected_sub: Optional[str] = None) -> dict:
    """
    Verify the JWT.  Raises HTTP 403 on failure.
    Optionally asserts that token['sub'] == expected_sub.
    """
    try:
        claims = verify_access_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Invalid consent token: {exc}")
    if expected_sub and claims.get("sub") != expected_sub:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Token subject does not match internal_id.")
    return claims


def _score_one(internal_id: str, db: Session) -> dict:
    """Fetch latest features, run model, cache and return result dict."""
    cache_key = f"score:{internal_id}"
    cached = redis_client.get(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            redis_client.delete(cache_key)

    feature = (
        db.query(Feature)
        .filter(Feature.internal_id == internal_id)
        .order_by(Feature.computed_at.desc())
        .first()
    )
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No features found for {internal_id}. Has the data pipeline run?",
        )

    feat_dict = {
        c.name: getattr(feature, c.name)
        for c in Feature.__table__.columns
        if c.name not in ("id", "internal_id", "user_type", "computed_at")
    }

    result = model_manager.predict(feat_dict, user_type=feature.user_type or "individual")
    result["internal_id"] = internal_id

    redis_client.setex(cache_key, SCORE_CACHE_TTL, json.dumps(result))
    return result

# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "acse"}


@app.get("/v1/model/health", response_model=ModelHealthResponse)
def model_health():
    return {
        "model_version": model_manager.version,
        "feature_count": len(model_manager.feature_names),
        "status": "loaded" if model_manager.model is not None else "not_loaded",
    }


@app.post("/v1/score", response_model=ScoreResponse)
def score(request: ScoreRequest, db: Session = Depends(get_db)):
    _validate_consent(request.consent_token, expected_sub=request.internal_id)
    return _score_one(request.internal_id, db)


@app.post("/v1/score/batch")
def batch_score(request: BatchScoreRequest, db: Session = Depends(get_db)):
    """Score up to 100 users in one call (lender dashboard use)."""
    if len(request.internal_ids) > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Batch size must not exceed 100.")
    _validate_consent(request.consent_token)   # service-level — no sub check

    results = []
    for iid in request.internal_ids:
        try:
            results.append(_score_one(iid, db))
        except HTTPException as exc:
            results.append({"internal_id": iid, "error": exc.detail})
    return results
