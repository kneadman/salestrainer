"""Expire active training sessions before introducing inactivity TTL.

Revision ID: 20260514_000010
Revises: 20260508_000009
Create Date: 2026-05-14 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260514_000010"
down_revision = "20260508_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Close all currently active durable sessions as expired."""
    op.execute(
        sa.text(
            """
            UPDATE training_sessions
            SET status = 'expired',
                finished_at = COALESCE(finished_at, last_activity_at, started_at),
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'active'
            """
        )
    )


def downgrade() -> None:
    """Do not reopen expired sessions during downgrade."""
    return None
