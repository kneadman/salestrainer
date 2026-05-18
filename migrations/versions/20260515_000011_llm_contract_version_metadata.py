"""Persist internal LLM contract version metadata.

Revision ID: 20260515_000011
Revises: 20260514_000010
Create Date: 2026-05-15 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260515_000011"
down_revision = "20260514_000010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add durable internal version labels for persona, dialogue, and judge contracts."""
    op.add_column(
        "training_sessions",
        sa.Column(
            "persona_schema_version",
            sa.Text(),
            nullable=False,
            server_default="persona-profile-v3.1",
        ),
    )
    op.add_column(
        "training_sessions",
        sa.Column(
            "persona_prompt_version",
            sa.Text(),
            nullable=False,
            server_default="global-yandex-persona-agent",
        ),
    )
    op.add_column(
        "training_turns",
        sa.Column(
            "dialogue_schema_version",
            sa.Text(),
            nullable=False,
            server_default="dialogue-turn-v1",
        ),
    )
    op.add_column(
        "training_turns",
        sa.Column(
            "dialogue_prompt_version",
            sa.Text(),
            nullable=False,
            server_default="global-yandex-dialogue-agent",
        ),
    )
    op.add_column(
        "training_reports",
        sa.Column(
            "judge_schema_version",
            sa.Text(),
            nullable=False,
            server_default="judge-session-v1",
        ),
    )
    op.add_column(
        "training_reports",
        sa.Column(
            "judge_prompt_version",
            sa.Text(),
            nullable=False,
            server_default="global-yandex-judge-agent",
        ),
    )


def downgrade() -> None:
    """Remove durable internal version labels."""
    op.drop_column("training_reports", "judge_prompt_version")
    op.drop_column("training_reports", "judge_schema_version")
    op.drop_column("training_turns", "dialogue_prompt_version")
    op.drop_column("training_turns", "dialogue_schema_version")
    op.drop_column("training_sessions", "persona_prompt_version")
    op.drop_column("training_sessions", "persona_schema_version")
