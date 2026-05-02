"""Add internal admin foundation tables and role migration.

Revision ID: 20260502_000003
Revises: 20260501_000002
Create Date: 2026-05-02 12:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260502_000003"
down_revision = "20260501_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'client_manager' WHERE role = 'client_user'")
    op.alter_column("users", "role", server_default=sa.text("'client_manager'"))

    op.create_table(
        "llm_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("folder_id", sa.Text(), nullable=True),
        sa.Column("agent_id", sa.Text(), nullable=True),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("model_or_agent_label", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["client_account_id"], ["client_accounts.id"]),
    )
    op.add_column(
        "client_training_configs",
        sa.Column("llm_provider_config_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_client_training_configs_llm_provider_config_id",
        "client_training_configs",
        "llm_provider_configs",
        ["llm_provider_config_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_client_training_configs_llm_provider_config_id",
        "client_training_configs",
        type_="foreignkey",
    )
    op.drop_column("client_training_configs", "llm_provider_config_id")
    op.drop_table("llm_provider_configs")
    op.alter_column("users", "role", server_default=sa.text("'client_user'"))
