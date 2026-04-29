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
    scenario_id: str
    persona_id: str


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
