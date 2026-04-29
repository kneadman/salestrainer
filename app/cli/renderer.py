from __future__ import annotations

from app.cli.commands import COMMANDS
from app.domain.interest import interest_band
from app.domain.models import TrainingSessionState
from app.domain.personas import list_personas
from app.domain.scenarios import list_scenarios


def render_help() -> str:
    lines = ["Commands:"]
    lines.extend(f"  {command:<8} {description}" for command, description in COMMANDS.items())
    return "\n".join(lines)


def render_scenarios() -> str:
    lines = ["Available scenarios:"]
    for index, scenario in enumerate(list_scenarios(), start=1):
        lines.append(f"  {index}. {scenario.name} [{scenario.id}]")
    return "\n".join(lines)


def render_personas() -> str:
    lines = ["Available personas:"]
    for index, persona in enumerate(list_personas(), start=1):
        lines.append(f"  {index}. {persona.display_name} [{persona.id}]")
    return "\n".join(lines)


def render_state(session: TrainingSessionState) -> str:
    state = session.client_state
    objections = ", ".join(state.open_objections) or "none"
    pains = ", ".join(state.known_pains) or "none"
    signals = ", ".join(state.buying_signals) or "none"
    return (
        f"Session: {session.session_id}\n"
        f"Scenario: {session.scenario_id}\n"
        f"Status: {session.status}\n"
        f"Persona: {session.persona.display_name}\n"
        f"Interest: {session.interest_score}/100 ({interest_band(session.interest_score)})\n"
        f"Stage: {session.stage}\n"
        f"Tone: {state.tone}\n"
        f"Trust/Irritation/Urgency: {state.trust}/{state.irritation}/{state.urgency}\n"
        f"Open objections: {objections}\n"
        f"Known pains: {pains}\n"
        f"Buying signals: {signals}\n"
        f"Turns: {session.turn_count}\n"
        f"Summary: {session.summary}"
    )


def render_history(session: TrainingSessionState, limit: int = 5) -> str:
    if not session.recent_turns:
        return "No turns yet."
    lines = ["Recent turns:"]
    for turn in session.recent_turns[-limit:]:
        lines.append(f"  #{turn.index} Manager: {turn.manager_message}")
        lines.append(f"     Client:  {turn.client_answer}")
        lines.append(
            f"     Interest: {turn.interest_before} -> {turn.interest_after} ({turn.interest_delta:+d})"
        )
    return "\n".join(lines)


def render_debug_block(title: str, payload: object) -> str:
    return f"[DEBUG] {title}: {payload}"
