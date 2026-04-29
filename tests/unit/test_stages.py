from app.domain.models import ClientState
from app.domain.stages import normalize_stage_name, resolve_next_stage


def make_state() -> ClientState:
    return ClientState(
        tone="neutral",
        trust=40,
        irritation=10,
        urgency=20,
        price_sensitivity=50,
        open_objections=[],
        known_pains=[],
        buying_signals=[],
        red_flags=[],
    )


def test_resolve_next_stage_blocks_finished_success_when_interest_is_too_low() -> None:
    state = make_state()
    assert resolve_next_stage(
        "trust_building",
        "finished_success",
        interest_score=55,
        client_state=state,
    ) == "trust_building"


def test_resolve_next_stage_allows_next_step_when_thresholds_are_met() -> None:
    state = make_state()
    state.buying_signals.append("Asked for next step")
    state.discovered_role = "owner"
    state.discovered_pains.append("Conversion is leaking between stages.")
    assert resolve_next_stage(
        "trust_building",
        "next_step_negotiation",
        interest_score=72,
        client_state=state,
    ) == "next_step_negotiation"


def test_resolve_next_stage_allows_finished_failed_when_state_is_bad() -> None:
    state = make_state()
    state.irritation = 75
    assert resolve_next_stage(
        "objection_handling",
        "finished_failed",
        interest_score=18,
        client_state=state,
    ) == "finished_failed"


def test_normalize_stage_name_maps_provider_aliases() -> None:
    assert normalize_stage_name("initial_contact") == "first_contact"
    assert normalize_stage_name("next_step") == "next_step_negotiation"
