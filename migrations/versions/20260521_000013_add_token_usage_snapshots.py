"""Add token_usage_snapshots table

Revision ID: 20260521_000013
Revises: 20260519_000012
Create Date: 2026-05-21 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260521_000013"
down_revision = "20260519_000012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_usage_snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("client_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_account_id"], ["client_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_account_id", "snapshot_date", name="uq_token_usage_snapshots_org_date"),
    )
    op.create_index(
        "ix_token_usage_snapshots_client_account_date",
        "token_usage_snapshots",
        ["client_account_id", sa.text("snapshot_date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_token_usage_snapshots_client_account_date", table_name="token_usage_snapshots")
    op.drop_table("token_usage_snapshots")
