"""checks, their scores and the audit log

Revision ID: 0001
Revises:
Create Date: 2026-09-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.String(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("connection", sa.String(), nullable=False),
        sa.Column("destination", sa.String(), nullable=False),
        sa.Column("travel_month", sa.String(), nullable=False),
        sa.Column("inbound_hour", sa.Integer(), nullable=False),
        sa.Column("outbound_hour", sa.Integer(), nullable=False),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("flights", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("note", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_checks_check_id", "checks", ["check_id"], unique=True)
    op.create_index("ix_checks_connection", "checks", ["connection"])
    op.create_index("ix_checks_travel_month", "checks", ["travel_month"])
    op.create_table(
        "check_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.String(), sa.ForeignKey("checks.check_id"), nullable=False),
        sa.Column("outcome_month", sa.String(), nullable=False),
        sa.Column("realized_rate", sa.Float(), nullable=False),
        sa.Column("pairs", sa.Integer(), nullable=False),
        sa.Column("absolute_error", sa.Float(), nullable=False),
        sa.Column("inside_interval", sa.Boolean(), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_check_scores_check_id", "check_scores", ["check_id"], unique=True)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
    )
    op.create_index("ix_audit_log_at", "audit_log", ["at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_at", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_check_scores_check_id", table_name="check_scores")
    op.drop_table("check_scores")
    op.drop_index("ix_checks_travel_month", table_name="checks")
    op.drop_index("ix_checks_connection", table_name="checks")
    op.drop_index("ix_checks_check_id", table_name="checks")
    op.drop_table("checks")
