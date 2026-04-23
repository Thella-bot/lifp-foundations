import os
import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from model import model_manager

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://lifp:lifp_pass@localhost:5432/lifpdb"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Feature(Base):
    __tablename__ = "features"
    user_id = Column(String, primary_key=True)
    total_trans = Column(Float)
    freq_per_week = Column(Float)
    days_since_last = Column(Float)
    active_months = Column(Float)
    cash_in = Column(Float)
    cash_out = Column(Float)
    net_cash_flow = Column(Float)
    ratio_out_in = Column(Float)
    avg_cash_in = Column(Float)
    avg_cash_out = Column(Float)
    std_amount = Column(Float)
    airtime_count = Column(Float)
    airtime_total = Column(Float)
    bill_count = Column(Float)
    bill_total = Column(Float)
    merchant_count = Column(Float)
    merchant_total = Column(Float)
    airtime_ratio = Column(Float)
    merchant_ratio = Column(Float)
    max_gap = Column(Float)
    median_gap = Column(Float)
    trend_slope = Column(Float)

app = FastAPI(title="LIFP ACSE", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.StrictRedis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
)

class ScoreRequest(BaseModel):
    internal_id: str
    consent_token: str

class ScoreResponse(BaseModel):
    internal_id: str
    score: int
    tier: str
    prob_default: float
    factors: list

@app.on_event("startup")
async def startup():
    model_manager.load()

@app.get("/health")
def health():
    return {"status": "ok", "service": "acse"}

@app.post("/v1/score", response_model=ScoreResponse)
def get_credit_score(request: ScoreRequest):
    # Very basic consent check – just verify token is not empty
    if not request.consent_token or len(request.consent_token) < 10:
        raise HTTPException(status_code=403, detail="Invalid consent token")

    # Check cache
    cache_key = f"score:{request.internal_id}"
    cached = redis_client.get(cache_key)
    if cached:
        import json
        return json.loads(cached)

    # Fetch features from PostgreSQL
    db = SessionLocal()
    feature = db.query(Feature).filter(Feature.user_id == request.internal_id).first()
    db.close()
    if not feature:
        raise HTTPException(status_code=404, detail="User features not found")

    feat_dict = {
        col.name: getattr(feature, col.name)
        for col in Feature.__table__.columns if col.name != "user_id"
    }

    result = model_manager.predict(feat_dict)
    result["internal_id"] = request.internal_id

    # Cache for 1 hour
    redis_client.setex(cache_key, 3600, str(result))
    return result