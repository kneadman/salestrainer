from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


ToneLiteral = Literal["cold", "skeptical", "neutral", "interested", "warm", "ready_next_step"]
SessionStatus = Literal["active", "finished", "expired"]
AuthorityLevel = Literal["final_decider", "influencer", "gatekeeper", "evaluator"]
BehaviorModel = Literal[
    "skeptical_but_rational",
    "busy_and_short",
    "price_sensitive",
    "process_oriented",
    "dominant_and_direct",
    "friendly_but_distrustful",
]


class PersonaProfile(BaseModel):
    id: str
    display_name: str
    role: Literal["owner", "purchase_manager", "sales_director", "cfo", "chief_accountant"]
    industry: str
    company_size: str
    authority_level: AuthorityLevel
    behavior_model: BehaviorModel
    cares_about: list[str] = Field(default_factory=list)
    typical_objections: list[str] = Field(default_factory=list)


class ClientState(BaseModel):
    tone: ToneLiteral
    trust: int = Field(ge=0, le=100)
    irritation: int = Field(ge=0, le=100)
    urgency: int = Field(ge=0, le=100)
    price_sensitivity: int = Field(ge=0, le=100)
    open_objections: list[str] = Field(default_factory=list)
    known_pains: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class Turn(BaseModel):
    index: int
    manager_message: str = Field(min_length=1)
    client_answer: str = Field(min_length=1)
    interest_before: int = Field(ge=0, le=100)
    interest_delta: int = Field(ge=-15, le=15)
    interest_after: int = Field(ge=0, le=100)
    stage_before: str
    stage_after: str
    created_at: datetime


class StatePatch(BaseModel):
    tone: ToneLiteral | None = None
    trust_delta: int = Field(default=0, ge=-15, le=15)
    irritation_delta: int = Field(default=0, ge=-15, le=15)
    urgency_delta: int = Field(default=0, ge=-15, le=15)
    add_open_objections: list[str] = Field(default_factory=list)
    remove_open_objections: list[str] = Field(default_factory=list)
    add_known_pains: list[str] = Field(default_factory=list)
    add_buying_signals: list[str] = Field(default_factory=list)
    add_red_flags: list[str] = Field(default_factory=list)


class LLMTurnResponse(BaseModel):
    answer: str = Field(min_length=1, max_length=1000)
    interest_delta: int = Field(ge=-15, le=15)
    state_patch: StatePatch
    stage: str = Field(min_length=1)
    internal_notes: str = Field(default="", max_length=1000)


class Scenario(BaseModel):
    id: str
    name: str
    offer: str
    target_audience: str
    default_starting_interest: int = Field(ge=0, le=100)
    default_stage: str
    success_condition: str
    failure_condition: str


class TrainingSessionState(BaseModel):
    session_id: UUID
    scenario_id: str
    status: SessionStatus
    persona: PersonaProfile
    interest_score: int = Field(ge=0, le=100)
    stage: str
    client_state: ClientState
    summary: str
    recent_turns: list[Turn] = Field(default_factory=list)
    turn_count: int = 0
    state_version: int = 1
    created_at: datetime
    updated_at: datetime


class LLMTurnInput(BaseModel):
    task: Literal["simulate_next_client_reply"]
    scenario: Scenario
    persona: PersonaProfile
    current_state: dict[str, Any]
    conversation_summary: str
    recent_turns: list[dict[str, str]] = Field(default_factory=list)
    manager_message: str = Field(min_length=1)

