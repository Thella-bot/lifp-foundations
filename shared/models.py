"""
shared/models.py
Single source of truth for all SQLAlchemy ORM models.
Both acse_service and data_pipeline import from here.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Float,
    ForeignKey, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.db import Base

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    internal_id    = Column(String(64), primary_key=True)   # SHA-256 of UIN
    user_type      = Column(
        Enum("msme", "individual", name="user_type_enum"),
        nullable=False,
        default="individual",
    )
    consent_version = Column(Integer, default=1, nullable=False)
    created_at     = Column(DateTime(timezone=True), default=_now, nullable=False)

    features       = relationship("Feature",       back_populates="user")
    credit_scores  = relationship("CreditScore",   back_populates="user")
    consents       = relationship("Consent",        back_populates="user")
    loan_applications = relationship("LoanApplication", back_populates="user")


# ---------------------------------------------------------------------------
# Features  (one row per user per computation run)
# ---------------------------------------------------------------------------

class Feature(Base):
    __tablename__ = "features"
    __table_args__ = (
        UniqueConstraint("internal_id", "computed_at", name="uq_feature_user_time"),
    )

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    internal_id    = Column(String(64), ForeignKey("users.internal_id"), nullable=False, index=True)
    user_type      = Column(String(20), nullable=False, default="individual")
    computed_at    = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    # Transaction volume
    total_trans    = Column(Float)
    freq_per_week  = Column(Float)
    days_since_last = Column(Float)
    active_months  = Column(Float)

    # Cash flow
    cash_in        = Column(Float)
    cash_out       = Column(Float)
    net_cash_flow  = Column(Float)
    ratio_out_in   = Column(Float)
    avg_cash_in    = Column(Float)
    avg_cash_out   = Column(Float)
    std_amount     = Column(Float)

    # Behaviour categories
    airtime_count  = Column(Float)
    airtime_total  = Column(Float)
    bill_count     = Column(Float)
    bill_total     = Column(Float)
    merchant_count = Column(Float)
    merchant_total = Column(Float)
    airtime_ratio  = Column(Float)
    merchant_ratio = Column(Float)

    # Regularity
    max_gap        = Column(Float)
    median_gap     = Column(Float)
    trend_slope    = Column(Float)

    user = relationship("User", back_populates="features")


# ---------------------------------------------------------------------------
# Credit Scores
# ---------------------------------------------------------------------------

class CreditScore(Base):
    __tablename__ = "credit_scores"

    id            = Column(BigInteger, primary_key=True, autoincrement=True)
    internal_id   = Column(String(64), ForeignKey("users.internal_id"), nullable=False, index=True)
    score         = Column(Integer, nullable=False)
    tier          = Column(String(1), nullable=False)
    prob_default  = Column(Float, nullable=False)
    explanation   = Column(JSON, default=list)    # SHAP factor list
    model_version = Column(String(50), nullable=False, default="unknown")
    created_at    = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User", back_populates="credit_scores")


# ---------------------------------------------------------------------------
# Consents
# ---------------------------------------------------------------------------

class Consent(Base):
    __tablename__ = "consents"

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    internal_id = Column(String(64), ForeignKey("users.internal_id"), nullable=False, index=True)
    purpose     = Column(String(100), nullable=False)
    granted     = Column(Boolean, nullable=False, default=True)
    granted_at  = Column(DateTime(timezone=True), default=_now)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    revoked_at  = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("internal_id", "purpose", name="uq_consent_user_purpose"),
    )

    user = relationship("User", back_populates="consents")


# ---------------------------------------------------------------------------
# Loan Applications
# ---------------------------------------------------------------------------

class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id               = Column(String(36), primary_key=True, default=_uuid)
    internal_id      = Column(String(64), ForeignKey("users.internal_id"), nullable=False, index=True)
    lender_id        = Column(String(100), nullable=False)
    amount_requested = Column(Float, nullable=False)
    status           = Column(
        Enum("pending", "approved", "rejected", "disbursed", "repaid", "defaulted",
             name="loan_status_enum"),
        default="pending",
        nullable=False,
    )
    created_at  = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at  = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User", back_populates="loan_applications")
