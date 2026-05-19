"""Add token_usage_records table

Revision ID: 20260519_000012
Revises: 36cd653492e7
Create Date: 2026-05-19 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260519_000012"
down_revision = "36cd653492e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "token_usage_records",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("client_account_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_account_id"], ["client_accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_token_usage_client_account_created",
        "token_usage_records",
        ["client_account_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_token_usage_user_created",
        "token_usage_records",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_token_usage_session_id",
        "token_usage_records",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_token_usage_session_id", table_name="token_usage_records")
    op.drop_index("ix_token_usage_user_created", table_name="token_usage_records")
    op.drop_index("ix_token_usage_client_account_created", table_name="token_usage_records")
    op.drop_table("token_usage_records")
