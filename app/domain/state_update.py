from __future__ import annotations

from app.domain.interest import clamp
from app.domain.models import ClientState, StatePatch


def _append_unique(items: list[str], additions: list[str]) -> None:
    for item in additions:
        if item not in items:
            items.append(item)


def apply_state_patch(client_state: ClientState, patch: StatePatch) -> ClientState:
    updated = client_state.model_copy(deep=True)
    updated.trust = clamp(updated.trust + patch.trust_delta)
    updated.irritation = clamp(updated.irritation + patch.irritation_delta)
    updated.urgency = clamp(updated.urgency + patch.urgency_delta)
    if patch.tone is not None:
        updated.tone = patch.tone
    _append_unique(updated.open_objections, patch.add_open_objections)
    for objection in patch.remove_open_objections:
        if objection in updated.open_objections:
            updated.open_objections.remove(objection)
    _append_unique(updated.known_pains, patch.add_known_pains)
    _append_unique(updated.buying_signals, patch.add_buying_signals)
    _append_unique(updated.red_flags, patch.add_red_flags)
    if patch.set_discovered_role is not None:
        updated.discovered_role = patch.set_discovered_role
    if patch.set_discovered_authority_level is not None:
        updated.discovered_authority_level = patch.set_discovered_authority_level
    _append_unique(updated.discovered_pains, patch.add_discovered_pains)
    _append_unique(updated.known_pains, patch.add_discovered_pains)
    _append_unique(updated.discovered_decision_criteria, patch.add_discovered_decision_criteria)
    _append_unique(updated.discovered_constraints, patch.add_discovered_constraints)
    _append_unique(updated.discovered_current_process, patch.add_discovered_current_process)
    return updated
