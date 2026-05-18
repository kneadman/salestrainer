"""Add seed_config JSONB column to client_training_configs.

Revision ID: 20260518_000010
Revises: 20260508_000009
Create Date: 2026-05-18 11:34:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "20260518_000010"
down_revision = "20260508_000009"
branch_labels = None
depends_on = None


def _jsonb_type(bind: sa.engine.Connection) -> sa.types.TypeEngine[object]:
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    """Add nullable seed_config column for structured persona-generation seeds."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}

    with op.batch_alter_table("client_training_configs") as batch_op:
        if "seed_config" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "seed_config",
                    _jsonb_type(bind),
                    nullable=True,
                )
            )


def downgrade() -> None:
    """Remove seed_config column."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("client_training_configs")}

    with op.batch_alter_table("client_training_configs") as batch_op:
        if "seed_config" in existing_columns:
            batch_op.drop_column("seed_config")
