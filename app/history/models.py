from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, desc, func, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from app.infrastructure.db import Base


class TrainingSessionRecord(Base):
    __tablename__ = "training_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    client_account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("client_accounts.id"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    training_config_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("client_training_configs.id"),
        nullable=True,
    )
    scenario_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    final_interest_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    initial_state_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    final_state_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    public_brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    persona_schema_version: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'persona-profile-v3.1'"))
    persona_prompt_version: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'global-yandex-persona-agent'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_training_sessions_client_account_started", "client_account_id", desc("started_at")),
        Index("ix_training_sessions_user_started", "user_id", desc("started_at")),
        Index("ix_training_sessions_training_config_started", "training_config_id", desc("started_at")),
        Index("ix_training_sessions_status", "status"),
        Index("ix_training_sessions_scenario_id", "scenario_id"),
    )


class TrainingTurnRecord(Base):
    __tablename__ = "training_turns"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    manager_message: Mapped[str] = mapped_column(Text, nullable=False)
    client_answer: Mapped[str] = mapped_column(Text, nullable=False)
    interest_before: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_after: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_before: Mapped[str] = mapped_column(Text, nullable=False)
    stage_after: Mapped[str] = mapped_column(Text, nullable=False)
    client_state_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    llm_payload_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    llm_response_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    evaluation_snapshot: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    dialogue_schema_version: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'dialogue-turn-v1'"))
    dialogue_prompt_version: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'global-yandex-dialogue-agent'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("session_id", "turn_index", name="uq_training_turns_session_turn_index"),
        Index("ix_training_turns_session_turn_index", "session_id", "turn_index"),
        Index("ix_training_turns_created_at", desc("created_at")),
    )


class TokenUsageRecord(Base):
    __tablename__ = "token_usage_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    client_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("client_accounts.id"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_token_usage_client_account_created", "client_account_id", desc("created_at")),
        Index("ix_token_usage_user_created", "user_id", desc("created_at")),
        Index("ix_token_usage_session_id", "session_id"),
    )


class TrainingReportRecord(Base):
    __tablename__ = "training_reports"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    report_text: Mapped[str] = mapped_column(Text, nullable=False)
    report_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    report_payload: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    judge_schema_version: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'judge-session-v1'"))
    judge_prompt_version: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'global-yandex-judge-agent'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UsageEventRecord(Base):
    __tablename__ = "usage_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    client_account_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("client_accounts.id"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    training_config_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("client_training_configs.id"),
        nullable=True,
    )
    session_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_usage_events_client_account_created", "client_account_id", desc("created_at")),
        Index("ix_usage_events_user_created", "user_id", desc("created_at")),
        Index("ix_usage_events_event_type_created", "event_type", desc("created_at")),
        Index("ix_usage_events_session_id", "session_id"),
    )
