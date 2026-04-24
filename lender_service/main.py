import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db import engine, get_db
from shared.models import Base, CreditScore, LoanApplication, User
from shared.security import require_internal_id_from_header

_raw_origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _raw_origins.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="LIFP - Lender Dashboard API", version="1.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def get_lender_id(authorization: str | None = Header(default=None)) -> str:
    return require_internal_id_from_header(authorization)


class ApplicationOut(BaseModel):
    id: str
    internal_id: str
    lender_id: str
    amount_requested: float
    status: str
    user_type: Optional[str]
    created_at: datetime
    updated_at: datetime


class CreditReportOut(BaseModel):
    internal_id: str
    user_type: Optional[str]
    score: Optional[int]
    tier: Optional[str]
    prob_default: Optional[float]
    model_version: Optional[str]
    factors: list
    scored_at: Optional[datetime]


class StatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


class PortfolioOut(BaseModel):
    total_applications: int
    pending: int
    approved: int
    rejected: int
    disbursed: int
    repaid: int
    defaulted: int
    total_disbursed_amount: float
    default_rate_pct: float


VALID_STATUSES = {"pending", "approved", "rejected", "disbursed", "repaid", "defaulted"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "lender"}


@app.get("/v1/lender/applications", response_model=List[ApplicationOut])
def list_applications(
    status_filter: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    lender_id: str = Depends(get_lender_id),
    db: Session = Depends(get_db),
):
    q = db.query(LoanApplication, User.user_type).join(
        User, LoanApplication.internal_id == User.internal_id
    ).filter(LoanApplication.lender_id == lender_id)

    if status_filter:
        status_filter = status_filter.lower()
        if status_filter not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status_filter. Must be one of: {sorted(VALID_STATUSES)}",
            )
        q = q.filter(LoanApplication.status == status_filter)

    rows = q.order_by(LoanApplication.created_at.desc()).offset(offset).limit(limit).all()

    return [
        ApplicationOut(
            id=app.id,
            internal_id=app.internal_id,
            lender_id=app.lender_id,
            amount_requested=app.amount_requested,
            status=app.status,
            user_type=utype,
            created_at=app.created_at,
            updated_at=app.updated_at,
        )
        for app, utype in rows
    ]


@app.get("/v1/lender/credit-report/{internal_id}", response_model=CreditReportOut)
def get_credit_report(
    internal_id: str,
    lender_id: str = Depends(get_lender_id),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.internal_id == internal_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    latest_score = (
        db.query(CreditScore)
        .filter(CreditScore.internal_id == internal_id)
        .order_by(CreditScore.created_at.desc())
        .first()
    )

    return CreditReportOut(
        internal_id=internal_id,
        user_type=user.user_type,
        score=latest_score.score if latest_score else None,
        tier=latest_score.tier if latest_score else None,
        prob_default=latest_score.prob_default if latest_score else None,
        model_version=latest_score.model_version if latest_score else None,
        factors=latest_score.explanation if latest_score else [],
        scored_at=latest_score.created_at if latest_score else None,
    )


@app.put("/v1/lender/loans/{loan_id}/status")
def update_loan_status(
    loan_id: str,
    update: StatusUpdate,
    lender_id: str = Depends(get_lender_id),
    db: Session = Depends(get_db),
):
    if update.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
        )

    loan = db.query(LoanApplication).filter(
        LoanApplication.id == loan_id,
        LoanApplication.lender_id == lender_id,
    ).first()
    if not loan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan not found or not owned by this lender.",
        )

    loan.status = update.status
    loan.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"loan_id": loan_id, "new_status": update.status}


@app.get("/v1/lender/portfolio", response_model=PortfolioOut)
def portfolio_summary(
    lender_id: str = Depends(get_lender_id),
    db: Session = Depends(get_db),
):
    status_rows = (
        db.query(LoanApplication.status, func.count(LoanApplication.id))
        .filter(LoanApplication.lender_id == lender_id)
        .group_by(LoanApplication.status)
        .all()
    )

    counts = {s: 0 for s in VALID_STATUSES}
    for status_name, count_value in status_rows:
        counts[status_name] = int(count_value)

    disbursed_total = (
        db.query(func.coalesce(func.sum(LoanApplication.amount_requested), 0.0))
        .filter(
            LoanApplication.lender_id == lender_id,
            LoanApplication.status.in_(["disbursed", "repaid", "defaulted"]),
        )
        .scalar()
    )

    total = sum(counts.values())
    defaulted = counts["defaulted"]
    repaid = counts["repaid"]
    denom = defaulted + repaid
    default_rate = round((defaulted / denom * 100) if denom > 0 else 0.0, 2)

    return PortfolioOut(
        total_applications=total,
        pending=counts["pending"],
        approved=counts["approved"],
        rejected=counts["rejected"],
        disbursed=counts["disbursed"],
        repaid=counts["repaid"],
        defaulted=counts["defaulted"],
        total_disbursed_amount=round(float(disbursed_total or 0.0), 2),
        default_rate_pct=default_rate,
    )
