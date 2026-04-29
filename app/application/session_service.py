from __future__ import annotations

from datetime import UTC, datetime
import logging
from uuid import uuid4

from app.domain.interest import interest_band
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState
from app.domain.personas import get_persona
from app.domain.scenarios import get_scenario
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)


def build_initial_client_state(persona: PersonaProfile, starting_interest: int) -> ClientState:
    return ClientState(
        tone=interest_band(starting_interest) if starting_interest <= 60 else "warm",
        trust=20,
        irritation=10,
        urgency=20,
        price_sensitivity=55 if "price" in persona.behavior_model else 45,
        open_objections=persona.typical_objections[:1],
        known_pains=[],
        buying_signals=[],
        red_flags=[],
    )


class TrainingSessionService:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def start_session(self, scenario_id: str, persona_id: str) -> TrainingSessionState:
        scenario = get_scenario(scenario_id)
        persona = get_persona(persona_id)
        now = datetime.now(tz=UTC)
        session = TrainingSessionState(
            session_id=uuid4(),
            scenario_id=scenario.id,
            status="active",
            persona=persona,
            interest_score=scenario.default_starting_interest,
            stage=scenario.default_stage,
            client_state=build_initial_client_state(persona, scenario.default_starting_interest),
            summary=f"Training started for scenario '{scenario.name}' with persona '{persona.display_name}'.",
            recent_turns=[],
            turn_count=0,
            state_version=1,
            created_at=now,
            updated_at=now,
        )
        self._repository.create(session)
        logger.info(
            "session_started session_id=%s scenario_id=%s persona_id=%s",
            session.session_id,
            scenario.id,
            persona.id,
        )
        return session

    def get_session(self, session_id: str) -> TrainingSessionState | None:
        return self._repository.get(session_id)

    def resume_session(self, session_id: str) -> TrainingSessionState:
        session = self._repository.get(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found.")
        if session.status != "active":
            raise ValueError(f"Session '{session_id}' is not active.")
        logger.info("session_resumed session_id=%s", session.session_id)
        return session
