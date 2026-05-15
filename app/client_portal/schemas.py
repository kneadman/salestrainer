from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.history.schemas import ClientHistorySessionSummaryDTO, UsageSummaryDTO


class MetricTrendDTO(BaseModel):
    current_7d: float | int | None
    previous_7d: float | int | None
    delta: float | int | None
    delta_percent: float | None
    direction: Literal["up", "down", "flat", "none"]


class ClientAnalyticsTrendsDTO(BaseModel):
    total_sessions: MetricTrendDTO
    finished_sessions: MetricTrendDTO
    completion_rate: MetricTrendDTO
    avg_final_interest_score: MetricTrendDTO
    avg_turn_count: MetricTrendDTO
    avg_judgement_score: MetricTrendDTO
    sessions_with_judgement: MetricTrendDTO


class ClientUserAnalyticsDTO(BaseModel):
    user_id: UUID
    user_email: str
    total_sessions: int
    finished_sessions: int
    active_sessions: int
    completion_rate: float
    avg_final_interest_score: float | None
    avg_turn_count: float | None
    avg_judgement_score: float | None
    sessions_with_judgement: int
    weakest_skill_id: str | None
    weakest_skill_title: str | None
    weakest_skill_avg_score: float | None
    strongest_skill_id: str | None
    strongest_skill_title: str | None
    strongest_skill_avg_score: float | None
    last_activity_at: datetime | None
    sessions_by_status: dict[str, int]
    sessions_by_scenario: dict[str, int]
    trends_7d: ClientAnalyticsTrendsDTO


class ClientTrainingConfigOptionDTO(BaseModel):
    id: UUID
    name: str
    is_default: bool


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
    history: list[ClientHistorySessionSummaryDTO]


class ManagerRankingItemDTO(BaseModel):
    user_id: UUID
    user_email: str
    rank: int
    score: float
    total_sessions: int
    finished_sessions: int
    completion_rate: float
    avg_final_interest_score: float | None
    avg_judgement_score: float | None
    sessions_with_judgement: int


class TeamUsageSummaryDTO(UsageSummaryDTO):
    avg_judgement_score: float | None
    sessions_with_judgement: int
    weakest_skill_id: str | None
    weakest_skill_title: str | None
    weakest_skill_avg_score: float | None
    strongest_skill_id: str | None
    strongest_skill_title: str | None
    strongest_skill_avg_score: float | None
    manager_ranking: list[ManagerRankingItemDTO]
    users: list[TeamUserDTO]
