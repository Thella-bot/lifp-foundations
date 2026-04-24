import json
import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

import redis
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from model import model_manager
from shared.db import get_db
from shared.models import Feature
from shared.security import verify_access_token

redis_client = redis.StrictRedis.from_url(
    os.environ.get("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True,
)
SCORE_CACHE_TTL = int(os.environ.get("SCORE_CACHE_TTL", "3600"))
BATCH_SCORE_MAX = int(os.environ.get("BATCH_SCORE_MAX", "100"))

_raw_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_origins.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_manager.load()
    yield


app = FastAPI(title="LIFP - ACSE", version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ScoreRequest(BaseModel):
    internal_id: str = Field(min_length=32, max_length=128)
    consent_token: str = Field(min_length=16, max_length=4096)


class ScoreResponse(BaseModel):
    internal_id: str
    score: int
    tier: str
    prob_default: float
    model_version: str
    factors: list


class BatchScoreRequest(BaseModel):
    internal_ids: List[str] = Field(min_length=1, max_length=200)
    consent_token: str = Field(min_length=16, max_length=4096)


class ModelHealthResponse(BaseModel):
    model_version: str
    feature_count: int
    status: str


def _validate_consent(token: str, expected_sub: Optional[str] = None) -> dict:
    try:
        return verify_access_token(token, expected_sub=expected_sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid consent token.")


def _safe_cache_get(cache_key: str) -> Optional[dict]:
    try:
        cached = redis_client.get(cache_key)
    except redis.RedisError:
        return None

    if not cached:
        return None

    try:
        return json.loads(cached)
    except json.JSONDecodeError:
        try:
            redis_client.delete(cache_key)
        except redis.RedisError:
            pass
        return None


def _safe_cache_set(cache_key: str, payload: dict) -> None:
    try:
        redis_client.setex(cache_key, SCORE_CACHE_TTL, json.dumps(payload))
    except redis.RedisError:
        # Cache failure should not fail score response.
        return


def _score_one(internal_id: str, db: Session) -> dict:
    cache_key = f"score:{internal_id}"
    cached = _safe_cache_get(cache_key)
    if cached:
        return cached

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

    _safe_cache_set(cache_key, result)
    return result


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
    if len(request.internal_ids) > BATCH_SCORE_MAX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size must not exceed {BATCH_SCORE_MAX}.",
        )
    _validate_consent(request.consent_token)

    deduped_ids = list(dict.fromkeys(request.internal_ids))
    results = []
    for iid in deduped_ids:
        try:
            results.append(_score_one(iid, db))
        except HTTPException as exc:
            results.append({"internal_id": iid, "error": exc.detail})
    return results
