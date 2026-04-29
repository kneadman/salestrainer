from app.domain.models import ClientState, StatePatch
from app.domain.state_update import apply_state_patch


def test_apply_state_patch_updates_numeric_fields_with_clamp() -> None:
    state = ClientState(
        tone="cold",
        trust=95,
        irritation=2,
        urgency=1,
        price_sensitivity=50,
    )
    patch = StatePatch(trust_delta=10, irritation_delta=-10, urgency_delta=10)
    updated = apply_state_patch(state, patch)
    assert updated.trust == 100
    assert updated.irritation == 0
    assert updated.urgency == 11


def test_apply_state_patch_adds_and_removes_unique_entries() -> None:
    state = ClientState(
        tone="skeptical",
        trust=20,
        irritation=10,
        urgency=20,
        price_sensitivity=50,
        open_objections=["Need proof"],
        known_pains=["Low conversion"],
        buying_signals=["Asked one question"],
        red_flags=[],
    )
    patch = StatePatch(
        add_open_objections=["Need proof", "No time"],
        remove_open_objections=["Need proof"],
        add_known_pains=["Low conversion", "Lead leakage"],
        add_buying_signals=["Asked one question", "Requested specifics"],
        add_red_flags=["Manager is generic", "Manager is generic"],
    )
    updated = apply_state_patch(state, patch)
    assert updated.open_objections == ["No time"]
    assert updated.known_pains == ["Low conversion", "Lead leakage"]
    assert updated.buying_signals == ["Asked one question", "Requested specifics"]
    assert updated.red_flags == ["Manager is generic"]


def test_apply_state_patch_handles_empty_patch_without_breaking_state() -> None:
    state = ClientState(
        tone="neutral",
        trust=20,
        irritation=10,
        urgency=20,
        price_sensitivity=50,
    )
    updated = apply_state_patch(state, StatePatch())
    assert updated == state

