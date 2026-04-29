from __future__ import annotations

from app.domain.models import ClientState


STAGES = {
    "first_contact",
    "value_clarification",
    "objection_handling",
    "need_discovery",
    "trust_building",
    "next_step_negotiation",
    "finished_success",
    "finished_failed",
}

STAGE_ALIASES = {
    "initial_contact": "first_contact",
    "discovery": "need_discovery",
    "qualification": "need_discovery",
    "value_discussion": "value_clarification",
    "next_step": "next_step_negotiation",
    "closed_won": "finished_success",
    "closed_lost": "finished_failed",
}


def normalize_stage_name(stage: str) -> str:
    normalized = stage.strip().lower()
    return STAGE_ALIASES.get(normalized, normalized)


def resolve_next_stage(
    current_stage: str,
    proposed_stage: str,
    *,
    interest_score: int,
    client_state: ClientState,
) -> str:
    current_stage = normalize_stage_name(current_stage)
    proposed_stage = normalize_stage_name(proposed_stage)
    if proposed_stage not in STAGES:
        return current_stage
    if proposed_stage == current_stage:
        return current_stage
    if proposed_stage == "finished_success":
        if current_stage == "next_step_negotiation" and interest_score >= 70 and bool(client_state.buying_signals):
            return proposed_stage
        return current_stage
    if proposed_stage == "next_step_negotiation":
        if interest_score >= 70 and bool(client_state.buying_signals):
            return proposed_stage
        return current_stage
    if proposed_stage == "finished_failed":
        if interest_score <= 20 or client_state.irritation >= 70 or bool(client_state.red_flags):
            return proposed_stage
        return current_stage

    allowed_forward = {
        "first_contact": {"value_clarification", "need_discovery", "objection_handling"},
        "value_clarification": {"objection_handling", "need_discovery", "trust_building"},
        "objection_handling": {"need_discovery", "trust_building", "value_clarification"},
        "need_discovery": {"trust_building", "objection_handling", "value_clarification"},
        "trust_building": {"next_step_negotiation", "need_discovery", "objection_handling"},
        "next_step_negotiation": {"trust_building"},
    }
    if proposed_stage in allowed_forward.get(current_stage, set()):
        return proposed_stage
    return current_stage
