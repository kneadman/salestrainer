"""Add persona_pool_entries table.

Revision ID: 20260527_000015
Revises: 20260526_000014
Create Date: 2026-05-27 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260527_000015"
down_revision = "20260526_000014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "persona_pool_entries",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("training_config_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("client_account_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("context_hash", sa.Text(), nullable=False),
        sa.Column("persona", sa.JSON(), nullable=False),
        sa.Column(
            "persona_schema_version",
            sa.Text(),
            nullable=False,
            server_default="persona-profile-v3.1",
        ),
        sa.Column("persona_prompt_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["training_config_id"], ["client_training_configs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["client_account_id"], ["client_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_persona_pool_lookup",
        "persona_pool_entries",
        ["training_config_id", "scenario_id", "context_hash", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_persona_pool_lookup", table_name="persona_pool_entries")
    op.drop_table("persona_pool_entries")
