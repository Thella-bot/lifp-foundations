"""Initial schema — all core tables.

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("internal_id",    sa.String(64),  primary_key=True),
        sa.Column("user_type",      sa.String(20),  nullable=False, server_default="individual"),
        sa.Column("consent_version",sa.Integer(),   nullable=False, server_default="1"),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_user_type", "users", ["user_type"])

    # ── features ──────────────────────────────────────────────────────────────
    op.create_table(
        "features",
        sa.Column("id",             sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("internal_id",    sa.String(64),  sa.ForeignKey("users.internal_id"), nullable=False),
        sa.Column("user_type",      sa.String(20),  nullable=False, server_default="individual"),
        sa.Column("computed_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        # transaction volume
        sa.Column("total_trans",    sa.Float()),
        sa.Column("freq_per_week",  sa.Float()),
        sa.Column("days_since_last",sa.Float()),
        sa.Column("active_months",  sa.Float()),
        # cash flow
        sa.Column("cash_in",        sa.Float()),
        sa.Column("cash_out",       sa.Float()),
        sa.Column("net_cash_flow",  sa.Float()),
        sa.Column("ratio_out_in",   sa.Float()),
        sa.Column("avg_cash_in",    sa.Float()),
        sa.Column("avg_cash_out",   sa.Float()),
        sa.Column("std_amount",     sa.Float()),
        # behaviour
        sa.Column("airtime_count",  sa.Float()),
        sa.Column("airtime_total",  sa.Float()),
        sa.Column("bill_count",     sa.Float()),
        sa.Column("bill_total",     sa.Float()),
        sa.Column("merchant_count", sa.Float()),
        sa.Column("merchant_total", sa.Float()),
        sa.Column("airtime_ratio",  sa.Float()),
        sa.Column("merchant_ratio", sa.Float()),
        # regularity
        sa.Column("max_gap",        sa.Float()),
        sa.Column("median_gap",     sa.Float()),
        sa.Column("trend_slope",    sa.Float()),
    )
    op.create_index("ix_features_internal_id",  "features", ["internal_id"])
    op.create_index("ix_features_computed_at",  "features", ["computed_at"])
    op.create_unique_constraint(
        "uq_feature_user_time", "features", ["internal_id", "computed_at"]
    )

    # ── credit_scores ─────────────────────────────────────────────────────────
    op.create_table(
        "credit_scores",
        sa.Column("id",            sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("internal_id",   sa.String(64),  sa.ForeignKey("users.internal_id"), nullable=False),
        sa.Column("score",         sa.Integer(),   nullable=False),
        sa.Column("tier",          sa.String(1),   nullable=False),
        sa.Column("prob_default",  sa.Float(),     nullable=False),
        sa.Column("explanation",   JSONB(),        server_default="[]"),
        sa.Column("model_version", sa.String(50),  nullable=False, server_default="unknown"),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_credit_scores_internal_id", "credit_scores", ["internal_id"])

    # ── consents ──────────────────────────────────────────────────────────────
    op.create_table(
        "consents",
        sa.Column("id",          sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("internal_id", sa.String(64),  sa.ForeignKey("users.internal_id"), nullable=False),
        sa.Column("purpose",     sa.String(100), nullable=False),
        sa.Column("granted",     sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("granted_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at",  sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_consents_internal_id", "consents", ["internal_id"])
    op.create_unique_constraint(
        "uq_consent_user_purpose", "consents", ["internal_id", "purpose"]
    )

    # ── loan_applications ─────────────────────────────────────────────────────
    op.create_table(
        "loan_applications",
        sa.Column("id",               sa.String(36),  primary_key=True),
        sa.Column("internal_id",      sa.String(64),  sa.ForeignKey("users.internal_id"), nullable=False),
        sa.Column("lender_id",        sa.String(100), nullable=False),
        sa.Column("amount_requested", sa.Float(),     nullable=False),
        sa.Column("status",           sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("created_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_loan_applications_internal_id", "loan_applications", ["internal_id"])
    op.create_index("ix_loan_applications_lender_id",   "loan_applications", ["lender_id"])
    op.create_index("ix_loan_applications_status",      "loan_applications", ["status"])


def downgrade() -> None:
    op.drop_table("loan_applications")
    op.drop_table("consents")
    op.drop_table("credit_scores")
    op.drop_table("features")
    op.drop_table("users")
