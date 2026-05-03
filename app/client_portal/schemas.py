from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.history.schemas import HistorySessionSummaryDTO, UsageSummaryDTO


class ClientUserAnalyticsDTO(BaseModel):
    user_id: UUID
    user_email: str
    total_sessions: int
    finished_sessions: int
    active_sessions: int
    completion_rate: float
    avg_final_interest_score: float | None
    avg_turn_count: float | None
    last_activity_at: datetime | None
    sessions_by_status: dict[str, int]
    sessions_by_scenario: dict[str, int]


class TeamUserDTO(BaseModel):
    id: UUID
    email: str
    role: str
    is_active: bool
    must_change_password: bool
    total_sessions: int
    finished_sessions: int
    avg_final_interest_score: float | None
    last_activity_at: datetime | None


class TeamUserDetailDTO(BaseModel):
    user: TeamUserDTO
    analytics: ClientUserAnalyticsDTO
    history: list[HistorySessionSummaryDTO]


class TeamUsageSummaryDTO(UsageSummaryDTO):
    users: list[TeamUserDTO]
