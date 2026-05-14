from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class HistorySessionSummaryDTO(BaseModel):
    session_id: UUID
    user_id: UUID
    user_email: str
    client_account_id: UUID
    training_config_id: UUID | None
    training_config_name: str | None = None
    scenario_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    last_activity_at: datetime
    turn_count: int
    final_interest_score: int | None = Field(default=None, ge=0, le=100)
    final_stage: str | None = None
    summary: str | None = None


class ClientHistorySessionSummaryDTO(BaseModel):
    session_id: UUID
    user_email: str
    training_config_name: str | None = None
    scenario_id: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    last_activity_at: datetime
    turn_count: int
    final_interest_score: int | None = Field(default=None, ge=0, le=100)
    final_stage: str | None = None
    summary: str | None = None


class HistoryTurnDTO(BaseModel):
    turn_index: int
    manager_message: str
    client_answer: str
    interest_before: int = Field(ge=0, le=100)
    interest_delta: int = Field(ge=-15, le=15)
    interest_after: int = Field(ge=0, le=100)
    stage_before: str
    stage_after: str
    client_state_public: dict[str, object] | None = None
    evaluation: dict[str, object] | None = None
    created_at: datetime


class HistoryReportDTO(BaseModel):
    session_id: UUID
    report: str
    report_payload: dict[str, object] | None = None
    report_version: int
    created_at: datetime
    updated_at: datetime


class HistorySessionDetailDTO(BaseModel):
    session: HistorySessionSummaryDTO
    public_brief: str | None = None
    turns: list[HistoryTurnDTO]
    report: HistoryReportDTO | None = None


class ClientHistorySessionDetailDTO(BaseModel):
    session: ClientHistorySessionSummaryDTO
    public_brief: str | None = None
    turns: list[HistoryTurnDTO]
    report: HistoryReportDTO | None = None


class UsageSummaryDTO(BaseModel):
    total_sessions: int
    finished_sessions: int
    active_sessions: int
    unique_users: int
    total_turns: int
    avg_final_interest_score: float | None
    avg_turn_count: float | None
    sessions_by_status: dict[str, int]
    sessions_by_scenario: dict[str, int]
    sessions_by_training_config: dict[str, int]
    usage_events_count: int
