from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


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
    training_format: str
    default_starting_interest: int
    default_stage: str
    manager_goal: str
    success_condition: str
    failure_condition: str
    evaluation_focus: list[str]
    client_behavior_hint: str


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
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=80)
    company: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=200)
    sales_team_size: str = Field(min_length=1, max_length=80)
    consent_personal_data: bool
    consent_marketing: bool = False
    comment: str | None = Field(default=None, max_length=2000)
    query_params: dict[str, str] = Field(default_factory=dict)
    page: str | None = Field(default=None, max_length=80)
    form_id: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=500)

    @field_validator("query_params")
    @classmethod
    def whitelist_query_params(cls, value: dict[str, str]) -> dict[str, str]:
        """Keep only known attribution keys from the public landing form."""
        allowed_keys = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "ref"}
        return {key: str(item)[:300] for key, item in value.items() if key in allowed_keys}


class LandingSubmitResponse(BaseModel):
    status: str


class TurnRequest(BaseModel):
    manager_message: str = Field(min_length=1, max_length=2000)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


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
    report_payload: dict[str, object] | None = None


class SessionReportResponse(BaseModel):
    session: SessionPublicDTO
    report: str
    report_payload: dict[str, object] | None = None


class SpeechTranscriptionResponse(BaseModel):
    text: str
    raw_text: str
    normalized: bool
    duration_ms: int | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, object]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorBody
