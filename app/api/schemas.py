from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InterestDTO(BaseModel):
    score: int = Field(ge=0, le=100)
    band: str


class TurnPublicDTO(BaseModel):
    turn_index: int
    manager_message: str
    client_answer: str
    interest_before: int = Field(ge=0, le=100)
    interest_delta: int = Field(ge=-15, le=15)
    interest_after: int = Field(ge=0, le=100)
    stage_before: str
    stage_after: str
    created_at: datetime


class SessionPublicDTO(BaseModel):
    session_id: str
    scenario_id: str
    status: str
    persona_name: str
    public_brief: str
    stage: str
    interest: InterestDTO
    client_state_public: dict[str, object]
    turn_count: int
    summary: str
    state_version: int


class ScenarioOptionDTO(BaseModel):
    scenario_id: str
    name: str
    offer: str
    target_audience: str


class PersonaOptionDTO(BaseModel):
    persona_id: str
    display_name: str
    role: str
    authority_level: str
    behavior_model: str


class SessionCreateRequest(BaseModel):
    scenario_id: str | None = None
    persona_id: str | None = None


class LandingLeadRequest(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    company: str | None = Field(default=None, max_length=200)
    role: str | None = Field(default=None, max_length=200)
    sales_team_size: str | None = Field(default=None, max_length=80)
    comment: str | None = Field(default=None, max_length=2000)
    marketing_consent: str | None = None
    query_params: dict[str, str] = Field(default_factory=dict)


class QuizLeadRequest(BaseModel):
    team_size: str | None = Field(default=None, max_length=80)
    onboarding_time: str | None = Field(default=None, max_length=120)
    weak_points: list[str] = Field(default_factory=list)
    materials: str | None = Field(default=None, max_length=200)
    format: str | None = Field(default=None, max_length=200)
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    company: str | None = Field(default=None, max_length=200)
    query_params: dict[str, str] = Field(default_factory=dict)


class LandingSubmitResponse(BaseModel):
    status: str


class TurnRequest(BaseModel):
    manager_message: str = Field(min_length=1, max_length=2000)


class SessionStateResponse(BaseModel):
    session: SessionPublicDTO


class SessionDetailResponse(BaseModel):
    session: SessionPublicDTO
    turns: list[TurnPublicDTO]


class TurnResponse(BaseModel):
    session: SessionPublicDTO
    turns: list[TurnPublicDTO]
    client_answer: str
    interest_before: int = Field(ge=0, le=100)
    interest_delta: int = Field(ge=-15, le=15)
    interest_after: int = Field(ge=0, le=100)
    stage_before: str
    stage_after: str
    turn_index: int


class FinishSessionResponse(BaseModel):
    session: SessionPublicDTO
    report: str


class SessionReportResponse(BaseModel):
    session: SessionPublicDTO
    report: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, object]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
