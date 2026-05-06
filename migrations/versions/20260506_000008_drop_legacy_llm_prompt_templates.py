"""Drop legacy LLM provider prompt/template fields.

Revision ID: 20260506_000008
Revises: 20260506_000007
Create Date: 2026-05-06 17:10:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260506_000008"
down_revision = "20260506_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove legacy prompt/template columns from llm_provider_configs."""
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("llm_provider_configs")}

    for column_name in (
        "dialogue_json_template",
        "dialogue_master_prompt",
        "persona_json_template",
        "persona_master_prompt",
    ):
        if column_name in existing_columns:
            op.drop_column("llm_provider_configs", column_name)


def downgrade() -> None:
    """Restore legacy prompt/template columns on llm_provider_configs."""
    inspector = inspect(op.get_bind())
    existing_columns = {column["name"] for column in inspector.get_columns("llm_provider_configs")}

    for column_name in (
        "persona_master_prompt",
        "persona_json_template",
        "dialogue_master_prompt",
        "dialogue_json_template",
    ):
        if column_name not in existing_columns:
            op.add_column("llm_provider_configs", sa.Column(column_name, sa.Text(), nullable=True))
