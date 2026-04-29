from __future__ import annotations

from app.api.schemas import InterestDTO, SessionPublicDTO, TurnPublicDTO
from app.domain.interest import interest_band
from app.domain.models import TrainingSessionState


def build_session_public_dto(session: TrainingSessionState) -> SessionPublicDTO:
    return SessionPublicDTO(
        session_id=str(session.session_id),
        scenario_id=session.scenario_id,
        status=session.status,
        persona_name="Unknown B2B contact",
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
            "known_pains": session.client_state.discovered_pains,
            "buying_signals": session.client_state.buying_signals,
            "discovered_role": session.client_state.discovered_role,
            "discovered_authority_level": session.client_state.discovered_authority_level,
            "discovered_decision_criteria": session.client_state.discovered_decision_criteria,
            "discovered_constraints": session.client_state.discovered_constraints,
            "discovered_current_process": session.client_state.discovered_current_process,
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
