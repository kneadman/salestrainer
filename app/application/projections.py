from __future__ import annotations

from app.api.schemas import FactsPanelDTO, FactsPanelItemDTO, InterestDTO, SessionPublicDTO, TurnPublicDTO
from app.domain.interest import interest_band
from app.domain.models import RevealedFact, TrainingSessionState, Turn

_FACTS_PANEL_LABELS = {
    "role": "Роль",
    "authority": "Полномочия",
    "current_process": "Текущий процесс",
    "decision_criterion": "Критерии решения",
    "constraint": "Ограничения",
    "buying_signal": "Сигналы интереса",
    "pain": "Выявленные боли",
    "objection": "Возражения",
}


def build_facts_panel_dto(revealed_facts: list[RevealedFact]) -> FactsPanelDTO:
    """Build a display-ready facts panel from already-sanitized revealed facts only."""
    return FactsPanelDTO(
        items=[
            FactsPanelItemDTO(
                category=fact.category,
                label=_FACTS_PANEL_LABELS[fact.category],
                text=fact.text,
                turn_index=fact.turn_index,
            )
            for fact in revealed_facts
        ]
    )


def build_session_public_dto(session: TrainingSessionState) -> SessionPublicDTO:
    return SessionPublicDTO(
        session_id=str(session.session_id),
        scenario_id=session.scenario_id,
        status=session.status,
        public_brief=session.public_brief,
        stage=session.stage,
        interest=InterestDTO(
            score=session.interest_score,
            band=interest_band(session.interest_score),
        ),
        client_state_public={
            "tone": session.client_state.tone,
            "trust": session.client_state.trust,
            "visible_objections": session.client_state.open_objections,
            "buying_signals": session.client_state.buying_signals,
            "revealed_facts": [
                fact.model_dump(mode="json")
                for fact in session.client_state.revealed_facts
            ],
        },
        facts_panel=build_facts_panel_dto(session.client_state.revealed_facts),
        turn_count=session.turn_count,
        summary=session.summary,
        state_version=session.state_version,
        training_config_id=str(session.training_config_id) if session.training_config_id else None,
    )


def build_turn_public_dto(session: TrainingSessionState) -> list[TurnPublicDTO]:
    return [
        TurnPublicDTO(
            turn_index=turn.index,
            manager_message=turn.manager_message,
            client_answer=turn.client_answer,
            interest_before=turn.interest_before,
            interest_delta=turn.interest_delta,
            interest_after=turn.interest_after,
            stage_before=turn.stage_before,
            stage_after=turn.stage_after,
            created_at=turn.created_at,
        )
        for turn in session.turns
    ]


def build_turn_response_payload(
    session: TrainingSessionState,
    *,
    turn: Turn,
    interest_before: int,
    stage_before: str,
) -> dict[str, object]:
    """Build the public-safe turn response payload used by both normal and idempotent replies."""
    return {
        "session": build_session_public_dto(session).model_dump(mode="json"),
        "turns": [turn_dto.model_dump(mode="json") for turn_dto in build_turn_public_dto(session)],
        "client_answer": turn.client_answer,
        "interest_before": interest_before,
        "interest_delta": turn.interest_delta,
        "interest_after": turn.interest_after,
        "stage_before": stage_before,
        "stage_after": session.stage,
        "turn_index": turn.index,
    }
