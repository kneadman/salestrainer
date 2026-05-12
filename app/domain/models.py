from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ToneLiteral = Literal["cold", "skeptical", "neutral", "interested", "warm", "ready_next_step"]
SessionStatus = Literal["active", "finished", "expired"]
AuthorityLevel = Literal["final_decider"]
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
Role = Literal[
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


class PersonaProfile(BaseModel):
    """Universal B2B persona schema v3.1.

    Strictly validated hidden profile used by the simulator.
    Legacy accounting fields are rejected via ``extra="forbid"``.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=120)
    display_name: str = Field(..., min_length=1, max_length=300)
    role: Role
    industry: str = Field(..., min_length=1, max_length=120)
    company_size: str = Field(..., min_length=1, max_length=80)
    authority_level: AuthorityLevel = "final_decider"
    behavior_model: BehaviorModel
    target_action: str = Field(..., min_length=1, max_length=120)

    current_business_context: str = Field(..., min_length=1, max_length=3000)
    business_facts: list[str] = Field(..., min_length=2, max_length=5)
    cares_about: list[str] = Field(..., min_length=3, max_length=6)

    current_solution: str = Field(..., min_length=1, max_length=1000)
    alternative_solutions: list[str] = Field(..., min_length=2, max_length=4)
    information_gaps: list[str] = Field(..., min_length=2, max_length=4)

    latent_pains: list[str] = Field(..., min_length=2, max_length=5)
    buying_motivation: list[str] = Field(..., min_length=2, max_length=4)
    decision_criteria: list[str] = Field(..., min_length=3, max_length=5)
    hidden_constraints: list[str] = Field(..., min_length=1, max_length=3)
    typical_objections: list[str] = Field(..., min_length=2, max_length=5)
    proof_sensitivity: list[str] = Field(..., min_length=2, max_length=4)
    call_scoring_criteria: list[str] = Field(..., min_length=3, max_length=6)
    communication_style: str = Field(..., min_length=1, max_length=2000)

    initial_openness: int = Field(..., ge=0, le=100)
    starting_interest: int = Field(..., ge=0, le=100)
    price_sensitivity: int = Field(..., ge=0, le=100)
    urgency: int = Field(..., ge=0, le=100)
    trust_baseline: int = Field(..., ge=0, le=100)

    @field_validator(
        "business_facts",
        "cares_about",
        "alternative_solutions",
        "information_gaps",
        "latent_pains",
        "buying_motivation",
        "decision_criteria",
        "hidden_constraints",
        "typical_objections",
        "proof_sensitivity",
        "call_scoring_criteria",
    )
    @classmethod
    def string_lists_must_not_contain_blank_items(cls, value: list[str]) -> list[str]:
        if any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError("List fields must contain only non-empty strings.")
        return value

    @field_validator("alternative_solutions")
    @classmethod
    def alternative_solutions_must_include_status_quo(cls, value: list[str]) -> list[str]:
        normalized = " | ".join(item.lower() for item in value)
        status_quo_markers = [
            "статус-кво",
            "ничего не менять",
            "как сейчас",
            "текущий процесс",
            "оставить текущ",
            "продолжать",
            "продолжить",
            "оставить всё",
            "оставить все",
            "без изменений",
            "не менять",
            "сохранить текущ",
            "сохранить как есть",
            "текущим подрядчиком",
            "текущий подрядчик",
            "текущим поставщиком",
            "текущий поставщик",
            "status quo",
            "status-quo",
        ]
        if not any(marker in normalized for marker in status_quo_markers):
            raise ValueError("alternative_solutions must include status quo.")
        return value


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


class PersonaGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona: PersonaProfile
    generation_notes: str = Field(default="", max_length=2000)
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
    recent_message_submissions: list["MessageSubmissionRecord"] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_persona_in_session(cls, data: Any) -> Any:
        """Normalize legacy persona payloads inside session JSON so old Redis records remain loadable."""
        if not isinstance(data, dict):
            return data
        persona = data.get("persona")
        if isinstance(persona, dict):
            data = dict(data)
            data["persona"] = normalize_legacy_persona_payload(persona)
        return data


class MessageSubmissionRecord(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=200)
    manager_message: str = Field(min_length=1, max_length=2000)
    response_payload: dict[str, Any]
    created_at: datetime


class LLMTurnInput(BaseModel):
    task: Literal["simulate_next_client_reply"]
    scenario: Scenario
    hidden_profile: PersonaProfile
    current_state: dict[str, Any]
    discovered_facts: dict[str, Any] = Field(default_factory=dict)
    conversation_summary: str
    recent_turns: list[dict[str, str]] = Field(default_factory=list)
    manager_message: str = Field(min_length=1)


def _map_legacy_current_solution(persona: dict[str, Any]) -> str | None:
    """Derive a human-readable current_solution from legacy bookkeeping fields."""
    model = persona.get("current_accounting_model")
    software = persona.get("accounting_software")
    software_mode = persona.get("accounting_software_mode")
    docs_owner = persona.get("primary_docs_owner")

    if model in {"director_self", "owner_does_accounting"}:
        return "Excel + ручной учёт собственником"
    if model == "inhouse_accountant":
        return "штатный бухгалтер"
    if model in {"remote_accountant", "private_accountant"}:
        return "частный или удалённый бухгалтер"
    if model in {"outsourced", "outsourced_accounting"}:
        return "текущий бухгалтерский аутсорсер"
    if model == "mixed":
        return "смешанная модель: часть процессов внутри, часть на подрядчике"
    if model == "unknown":
        return None

    parts: list[str] = []
    if isinstance(software, str) and software and software != "unknown":
        parts.append(software)
    if isinstance(software_mode, str) and software_mode and software_mode != "unknown":
        parts.append(software_mode)
    if isinstance(docs_owner, str) and docs_owner and docs_owner != "unknown":
        parts.append(f"ответственный за процесс: {docs_owner}")

    if parts:
        return " + ".join(parts)

    return None


def normalize_legacy_persona_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a legacy persona dict (pre-v3.1) to the universal v3.1 shape.

    This is intentionally kept outside ``PersonaProfile`` so that the model
    itself can reject unknown fields with ``extra="forbid"`` while runtime
    session repositories can still load historical JSON from Redis/PostgreSQL.
    """
    legacy_keys = [
        "current_accounting_model",
        "legal_form",
        "tax_system",
        "accounting_software",
        "accounting_software_mode",
        "primary_docs_owner",
    ]
    if not any(key in raw for key in legacy_keys):
        return raw

    raw = raw.copy()

    # Старые runtime-сессии могли содержать influencer/gatekeeper/evaluator.
    # Новая схема v3.1 допускает только final_decider.
    raw["authority_level"] = "final_decider"

    if "current_solution" not in raw:
        mapped = _map_legacy_current_solution(raw)
        raw["current_solution"] = mapped or (
            "legacy-персона: текущее решение не было сохранено в старой схеме"
        )

    raw.setdefault(
        "alternative_solutions",
        [
            "статус-кво: продолжать как сейчас",
            "обсудить альтернативный подход",
        ],
    )
    raw.setdefault(
        "information_gaps",
        [
            "legacy-персона: информационные пробелы не были сохранены в старой схеме",
            "требует уточнения в диалоге",
        ],
    )

    for key in legacy_keys:
        raw.pop(key, None)

    return raw
