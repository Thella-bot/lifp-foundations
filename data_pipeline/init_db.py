"""
data_pipeline/init_db.py
Database initialiser + synthetic data seeder.

Changes vs original:
  - Duplicate ORM models removed; imported from shared.models (single source of truth)
  - deprecated declarative_base import removed
  - user_type column seeded for both msme and individual users
  - Feature rows now include computed_at so multiple snapshots can coexist
  - Pinned requirements (see requirements.txt)
"""
import hashlib
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db import SessionLocal, engine
from shared.models import Base, Feature, User


def _hash(val: str) -> str:
    return hashlib.sha256(val.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _gen_features(rng: np.random.Generator, user_type: str) -> dict:
    """
    Generate a realistic synthetic feature row.
    MSMEs tend to have higher merchant activity; individuals have more
    bill payments and smaller, more regular transactions.
    """
    is_msme = user_type == "msme"

    total_trans    = rng.integers(30, 300 if is_msme else 150)
    freq_per_week  = round(float(total_trans) / 52, 2)
    days_since_last = float(rng.integers(0, 14))
    active_months  = float(rng.integers(3, 12))

    cash_in        = round(float(rng.uniform(2000, 50000 if is_msme else 15000)), 2)
    cash_out       = round(float(rng.uniform(1000, cash_in * 0.95)), 2)
    net_cash_flow  = round(cash_in - cash_out, 2)
    ratio_out_in   = round(cash_out / cash_in, 4) if cash_in > 0 else 1.0
    avg_cash_in    = round(cash_in / max(active_months, 1), 2)
    avg_cash_out   = round(cash_out / max(active_months, 1), 2)
    std_amount     = round(float(rng.uniform(100, 3000 if is_msme else 1000)), 2)

    airtime_count  = float(rng.integers(1, 20))
    airtime_total  = round(airtime_count * float(rng.uniform(5, 50)), 2)
    bill_count     = float(rng.integers(0 if is_msme else 1, 10))
    bill_total     = round(bill_count * float(rng.uniform(50, 300)), 2)
    merchant_count = float(rng.integers(10 if is_msme else 0, 100 if is_msme else 20))
    merchant_total = round(merchant_count * float(rng.uniform(20, 500 if is_msme else 100)), 2)
    airtime_ratio  = round(airtime_total / max(cash_out, 1), 4)
    merchant_ratio = round(merchant_total / max(cash_out, 1), 4)

    max_gap    = float(rng.integers(1, 30))
    median_gap = round(float(rng.uniform(1, max_gap)), 2)
    trend_slope = round(float(rng.uniform(-0.5, 0.5)), 4)

    return dict(
        total_trans=total_trans, freq_per_week=freq_per_week,
        days_since_last=days_since_last, active_months=active_months,
        cash_in=cash_in, cash_out=cash_out, net_cash_flow=net_cash_flow,
        ratio_out_in=ratio_out_in, avg_cash_in=avg_cash_in, avg_cash_out=avg_cash_out,
        std_amount=std_amount,
        airtime_count=airtime_count, airtime_total=airtime_total,
        bill_count=bill_count, bill_total=bill_total,
        merchant_count=merchant_count, merchant_total=merchant_total,
        airtime_ratio=airtime_ratio, merchant_ratio=merchant_ratio,
        max_gap=max_gap, median_gap=median_gap, trend_slope=trend_slope,
    )


def seed(n_msme: int = 250, n_individual: int = 250, seed_val: int = 42):
    """Create all tables and seed synthetic users + features."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    rng = np.random.default_rng(seed_val)

    users_added = 0
    feats_added = 0

    specs = [("msme", n_msme), ("individual", n_individual)]
    for user_type, count in specs:
        for i in range(count):
            uid = _hash(f"{user_type}-{i}")
            if not db.query(User).filter(User.internal_id == uid).first():
                db.add(User(internal_id=uid, user_type=user_type))
                users_added += 1

            feat_data = _gen_features(rng, user_type)
            db.add(Feature(
                internal_id=uid,
                user_type=user_type,
                computed_at=_now() - timedelta(hours=random.randint(0, 24)),
                **feat_data,
            ))
            feats_added += 1

    db.commit()
    db.close()
    print(f"[seed] {users_added} users added, {feats_added} feature rows added.")


if __name__ == "__main__":
    seed()
