"""Merge seed_config and llm_contract_version branches

Revision ID: 36cd653492e7
Revises: 20260515_000011, 20260518_000010
Create Date: 2026-05-18 14:10:53.074083

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '36cd653492e7'
down_revision = ('20260515_000011', '20260518_000010')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
