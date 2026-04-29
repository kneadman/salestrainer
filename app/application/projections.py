from __future__ import annotations

from app.api.schemas import InterestDTO, SessionPublicDTO, TurnPublicDTO
from app.domain.interest import interest_band
from app.domain.models import TrainingSessionState


def build_session_public_dto(session: TrainingSessionState) -> SessionPublicDTO:
    return SessionPublicDTO(
        session_id=str(session.session_id),
        scenario_id=session.scenario_id,
        status=session.status,
        persona_name=session.persona.display_name,
        stage=session.stage,
        interest=InterestDTO(
            score=session.interest_score,
            band=interest_band(session.interest_score),
        ),
        client_state_public={
            "tone": session.client_state.tone,
            "visible_objections": session.client_state.open_objections,
            "known_pains": session.client_state.known_pains,
            "buying_signals": session.client_state.buying_signals,
        },
        turn_count=session.turn_count,
        summary=session.summary,
        state_version=session.state_version,
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
