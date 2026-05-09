from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ToneLiteral = Literal["cold", "skeptical", "neutral", "interested", "warm", "ready_next_step"]
SessionStatus = Literal["active", "finished", "expired"]
AuthorityLevel = Literal["final_decider", "influencer", "gatekeeper", "evaluator"]
BehaviorModel = Literal[
    "skeptical_but_rational",
    "dominant_and_direct",
    "price_sensitive",
    "analytical_and_cautious",
    "distrustful_due_to_bad_experience",
    "busy_and_short",
    "friendly_but_defensive",
    "formal_and_distant",
    "interested_but_overloaded",
    "process_oriented",
    "friendly_but_distrustful",
]


class PersonaProfile(BaseModel):
    id: str
    display_name: str = "Unknown B2B contact"
    role: Literal[
        "owner",
        "founder",
        "ceo",
        "general_director",
        "managing_partner",
        "commercial_director",
        "cfo",
        "chief_accountant",
        "operations_director",
        "sales_director",
        "purchase_manager",
    ]
    industry: str
    company_size: str
    authority_level: AuthorityLevel
    behavior_model: BehaviorModel
    target_action: str = ""
    current_accounting_model: str = "unknown"
    legal_form: str = "unknown"
    tax_system: str = "unknown"
    accounting_software: str = "unknown"
    accounting_software_mode: str = "unknown"
    primary_docs_owner: str = "unknown"
    cares_about: list[str] = Field(default_factory=list)
    typical_objections: list[str] = Field(default_factory=list)
    current_business_context: str = ""
    latent_pains: list[str] = Field(default_factory=list)
    buying_motivation: list[str] = Field(default_factory=list)
    decision_criteria: list[str] = Field(default_factory=list)
    hidden_constraints: list[str] = Field(default_factory=list)
    business_facts: list[str] = Field(default_factory=list)
    proof_sensitivity: list[str] = Field(default_factory=list)
    call_scoring_criteria: list[str] = Field(default_factory=list)
    communication_style: str = ""
    initial_openness: int = Field(default=25, ge=0, le=100)
    starting_interest: int = Field(default=25, ge=0, le=100)
    price_sensitivity: int = Field(default=50, ge=0, le=100)
    urgency: int = Field(default=20, ge=0, le=100)
    trust_baseline: int = Field(default=20, ge=0, le=100)


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
    discovered_role: str | None = None
    discovered_authority_level: str | None = None
    discovered_pains: list[str] = Field(default_factory=list)
    discovered_decision_criteria: list[str] = Field(default_factory=list)
    discovered_constraints: list[str] = Field(default_factory=list)
    discovered_current_process: list[str] = Field(default_factory=list)


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
    model_config = ConfigDict(extra="forbid")

    tone: ToneLiteral | None = None
    trust_delta: int = Field(default=0, ge=-15, le=15)
    irritation_delta: int = Field(default=0, ge=-15, le=15)
    urgency_delta: int = Field(default=0, ge=-15, le=15)
    add_open_objections: list[str] = Field(default_factory=list)
    remove_open_objections: list[str] = Field(default_factory=list)
    add_known_pains: list[str] = Field(default_factory=list)
    add_buying_signals: list[str] = Field(default_factory=list)
    add_red_flags: list[str] = Field(default_factory=list)
    set_discovered_role: str | None = None
    set_discovered_authority_level: str | None = None
    add_discovered_pains: list[str] = Field(default_factory=list)
    add_discovered_decision_criteria: list[str] = Field(default_factory=list)
    add_discovered_constraints: list[str] = Field(default_factory=list)
    add_discovered_current_process: list[str] = Field(default_factory=list)


class LLMTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=1000)
    interest_delta: int = Field(ge=-15, le=15)
    state_patch: StatePatch
    stage: str = Field(min_length=1)
    internal_notes: str = Field(default="", max_length=1000)


class Scenario(BaseModel):
    id: str
    name: str
    training_format: str
    default_starting_interest: int = Field(ge=0, le=100)
    default_stage: str
    manager_goal: str
    success_condition: str
    failure_condition: str
    evaluation_focus: list[str] = Field(default_factory=list)
    client_behavior_hint: str = ""


class PersonaGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task: Literal["generate_client_persona"] = "generate_client_persona"
    scenario: Scenario
    training_config_name: str | None = None
    persona_generation_context: str = ""
    persona_policy: dict[str, Any] = Field(default_factory=dict)
    organization_context: dict[str, Any] = Field(default_factory=dict)
    target_action: str | None = None
    allowed_roles: list[str] | None = None
    manager_training_goal: str | None = None
    difficulty_level: str | None = None
    randomization_seed: int | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1


class PersonaGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: PersonaProfile
    generation_notes: str = ""
    policy_coverage: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class TurnEvaluation(BaseModel):
    turn_index: int
    discovery_quality_score: int = Field(ge=0, le=5)
    role_identification_score: int = Field(ge=0, le=5)
    pain_identification_score: int = Field(ge=0, le=5)
    relevance_score: int = Field(ge=0, le=5)
    pressure_score: int = Field(ge=0, le=5)
    objection_handling_score: int = Field(ge=0, le=5)
    next_step_timing_score: int = Field(ge=0, le=5)
    conversation_control_score: int = Field(ge=0, le=5)
    notes: list[str] = Field(default_factory=list)


class TrainingSessionState(BaseModel):
    session_id: UUID
    scenario_id: str
    status: SessionStatus
    persona: PersonaProfile
    interest_score: int = Field(ge=0, le=100)
    stage: str
    client_state: ClientState
    summary: str
    public_brief: str = ""
    turns: list[Turn] = Field(default_factory=list)
    turn_evaluations: list[TurnEvaluation] = Field(default_factory=list)
    recent_turns: list[Turn] = Field(default_factory=list)
    turn_count: int = 0
    state_version: int = 1
    history_sync_status: Literal["ok", "pending_retry"] = "ok"
    history_sync_error: str | None = None
    created_at: datetime
    updated_at: datetime


class LLMTurnInput(BaseModel):
    task: Literal["simulate_next_client_reply"]
    scenario: Scenario
    hidden_profile: PersonaProfile
    current_state: dict[str, Any]
    discovered_facts: dict[str, Any] = Field(default_factory=dict)
    conversation_summary: str
    recent_turns: list[dict[str, str]] = Field(default_factory=list)
    manager_message: str = Field(min_length=1)
