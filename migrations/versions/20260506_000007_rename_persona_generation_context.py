"""Rename persona prompt to context and drop product_line.

Revision ID: 20260506_000007
Revises: 20260504_000006
Create Date: 2026-05-06 17:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260506_000007"
down_revision = "20260504_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename persona_generation_prompt and remove the accidental product_line column."""
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}
    if "persona_generation_prompt" in existing_columns and "persona_generation_context" not in existing_columns:
        op.alter_column(
            "client_training_configs",
            "persona_generation_prompt",
            new_column_name="persona_generation_context",
        )
    if "product_line" in existing_columns:
        op.drop_column("client_training_configs", "product_line")


def downgrade() -> None:
    """Restore product_line and rename persona_generation_context back to persona_generation_prompt."""
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}
    if "product_line" not in existing_columns:
        op.add_column(
            "client_training_configs",
            sa.Column("product_line", sa.Text(), nullable=False, server_default=sa.text("''")),
        )
    if "persona_generation_context" in existing_columns and "persona_generation_prompt" not in existing_columns:
        op.alter_column(
            "client_training_configs",
            "persona_generation_context",
            new_column_name="persona_generation_prompt",
        )
