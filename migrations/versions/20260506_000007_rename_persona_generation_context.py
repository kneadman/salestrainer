"""Compatibility bridge after removing product-line migration.

Revision ID: 20260506_000007
Revises: 20260504_000006
Create Date: 2026-05-06 17:00:00

"""
from __future__ import annotations

revision = "20260506_000007"
down_revision = "20260504_000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Keep a stable revision chain for databases already stamped at 20260506_000007."""
    return None


def downgrade() -> None:
    """Compatibility bridge downgrade is a no-op."""
    return None
