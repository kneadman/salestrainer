"""Add training-config persona prompt for simplified MVP LLM flow.

Revision ID: 20260504_000006
Revises: 20260503_000005
Create Date: 2026-05-04 12:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260504_000006"
down_revision = "20260503_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add business-context prompt storage to client training configs."""
    op.add_column(
        "client_training_configs",
        sa.Column("persona_generation_prompt", sa.Text(), nullable=False, server_default=sa.text("''")),
    )


def downgrade() -> None:
    """Remove business-context prompt storage from client training configs."""
    op.drop_column("client_training_configs", "persona_generation_prompt")
