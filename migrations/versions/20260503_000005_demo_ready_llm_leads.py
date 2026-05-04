"""Add demo-ready LLM config fields and landing leads.

Revision ID: 20260503_000005
Revises: 20260503_000004
Create Date: 2026-05-03 18:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260503_000005"
down_revision = "20260503_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend organization LLM config and persist landing form leads."""
    op.add_column("llm_provider_configs", sa.Column("persona_api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("persona_agent_id", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("persona_folder_id", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("persona_master_prompt", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("persona_json_template", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("dialogue_api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("dialogue_agent_id", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("dialogue_folder_id", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("dialogue_master_prompt", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("dialogue_json_template", sa.Text(), nullable=True))

    op.create_table(
        "landing_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("sales_team_size", sa.Text(), nullable=False),
        sa.Column("consent_personal_data", sa.Boolean(), nullable=False),
        sa.Column("consent_marketing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("query_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("page", sa.Text(), nullable=True),
        sa.Column("form_id", sa.Text(), nullable=True),
        sa.Column("is_spam", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_landing_leads_created_at", "landing_leads", [sa.text("created_at DESC")])
    op.create_index("ix_landing_leads_email", "landing_leads", ["email"])


def downgrade() -> None:
    """Remove demo-ready LLM config additions and lead storage."""
    op.drop_index("ix_landing_leads_email", table_name="landing_leads")
    op.drop_index("ix_landing_leads_created_at", table_name="landing_leads")
    op.drop_table("landing_leads")
    op.drop_column("llm_provider_configs", "dialogue_json_template")
    op.drop_column("llm_provider_configs", "dialogue_master_prompt")
    op.drop_column("llm_provider_configs", "dialogue_folder_id")
    op.drop_column("llm_provider_configs", "dialogue_agent_id")
    op.drop_column("llm_provider_configs", "dialogue_api_key_encrypted")
    op.drop_column("llm_provider_configs", "persona_json_template")
    op.drop_column("llm_provider_configs", "persona_master_prompt")
    op.drop_column("llm_provider_configs", "persona_folder_id")
    op.drop_column("llm_provider_configs", "persona_agent_id")
    op.drop_column("llm_provider_configs", "persona_api_key_encrypted")
