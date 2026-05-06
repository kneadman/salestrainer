"""Add product line to client training configs.

Revision ID: 20260506_000007
Revises: 20260504_000006
Create Date: 2026-05-06 14:45:00

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
    """Store the business product line used by persona generation input."""
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}
    if "product_line" in existing_columns:
        return
    op.add_column(
        "client_training_configs",
        sa.Column("product_line", sa.Text(), nullable=False, server_default=sa.text("''")),
    )


def downgrade() -> None:
    """Remove the training-config product line field."""
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}
    if "product_line" not in existing_columns:
        return
    op.drop_column("client_training_configs", "product_line")
