"""Add persistent training history tables.

Revision ID: 20260503_000004
Revises: 20260502_000003
Create Date: 2026-05-03 12:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260503_000004"
down_revision = "20260502_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create persistent training history and usage analytics tables."""
    op.create_table(
        "training_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("training_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scenario_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("final_interest_score", sa.Integer(), nullable=True),
        sa.Column("final_stage", sa.Text(), nullable=True),
        sa.Column("persona_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("initial_state_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("final_state_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("public_brief", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["client_account_id"], ["client_accounts.id"]),
        sa.ForeignKeyConstraint(["training_config_id"], ["client_training_configs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_training_sessions_client_account_started", "training_sessions", ["client_account_id", sa.text("started_at DESC")])
    op.create_index("ix_training_sessions_user_started", "training_sessions", ["user_id", sa.text("started_at DESC")])
    op.create_index("ix_training_sessions_training_config_started", "training_sessions", ["training_config_id", sa.text("started_at DESC")])
    op.create_index("ix_training_sessions_status", "training_sessions", ["status"])
    op.create_index("ix_training_sessions_scenario_id", "training_sessions", ["scenario_id"])

    op.create_table(
        "training_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("manager_message", sa.Text(), nullable=False),
        sa.Column("client_answer", sa.Text(), nullable=False),
        sa.Column("interest_before", sa.Integer(), nullable=False),
        sa.Column("interest_delta", sa.Integer(), nullable=False),
        sa.Column("interest_after", sa.Integer(), nullable=False),
        sa.Column("stage_before", sa.Text(), nullable=False),
        sa.Column("stage_after", sa.Text(), nullable=False),
        sa.Column("client_state_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_payload_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_response_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evaluation_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", "turn_index", name="uq_training_turns_session_turn_index"),
    )
    op.create_index("ix_training_turns_session_turn_index", "training_turns", ["session_id", "turn_index"])
    op.create_index("ix_training_turns_created_at", "training_turns", [sa.text("created_at DESC")])

    op.create_table(
        "training_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_text", sa.Text(), nullable=False),
        sa.Column("report_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("report_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("session_id", name="uq_training_reports_session_id"),
    )

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("training_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["client_account_id"], ["client_accounts.id"]),
        sa.ForeignKeyConstraint(["training_config_id"], ["client_training_configs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_usage_events_client_account_created", "usage_events", ["client_account_id", sa.text("created_at DESC")])
    op.create_index("ix_usage_events_user_created", "usage_events", ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_usage_events_event_type_created", "usage_events", ["event_type", sa.text("created_at DESC")])
    op.create_index("ix_usage_events_session_id", "usage_events", ["session_id"])


def downgrade() -> None:
    """Drop persistent history tables in reverse dependency order."""
    op.drop_index("ix_usage_events_session_id", table_name="usage_events")
    op.drop_index("ix_usage_events_event_type_created", table_name="usage_events")
    op.drop_index("ix_usage_events_user_created", table_name="usage_events")
    op.drop_index("ix_usage_events_client_account_created", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_table("training_reports")
    op.drop_index("ix_training_turns_created_at", table_name="training_turns")
    op.drop_index("ix_training_turns_session_turn_index", table_name="training_turns")
    op.drop_table("training_turns")
    op.drop_index("ix_training_sessions_scenario_id", table_name="training_sessions")
    op.drop_index("ix_training_sessions_status", table_name="training_sessions")
    op.drop_index("ix_training_sessions_training_config_started", table_name="training_sessions")
    op.drop_index("ix_training_sessions_user_started", table_name="training_sessions")
    op.drop_index("ix_training_sessions_client_account_started", table_name="training_sessions")
    op.drop_table("training_sessions")
