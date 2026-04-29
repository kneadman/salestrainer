from __future__ import annotations

from datetime import UTC, datetime
import logging
from uuid import uuid4

from app.domain.persona_generation import PersonaGenerator
from app.domain.interest import interest_band
from app.domain.errors import SessionNotActiveError, SessionNotFoundError
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState
from app.domain.personas import get_persona
from app.domain.scenarios import get_scenario
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)

DEFAULT_PUBLIC_BRIEF = (
    "Вы начали первичный B2B-диалог с потенциальным клиентом. "
    "Роль, полномочия и контекст клиента неизвестны. "
    "Выясните их через вопросы и выведите разговор к следующему шагу."
)


def build_initial_client_state(persona: PersonaProfile, starting_interest: int) -> ClientState:
    return ClientState(
        tone=interest_band(starting_interest) if starting_interest <= 60 else "warm",
        trust=persona.trust_baseline,
        irritation=10,
        urgency=persona.urgency,
        price_sensitivity=persona.price_sensitivity,
        open_objections=persona.typical_objections[:1],
        known_pains=[],
        buying_signals=[],
        red_flags=[],
    )


class TrainingSessionService:
    def __init__(
        self,
        repository: SessionRepository,
        *,
        persona_generator: PersonaGenerator | None = None,
        default_scenario_id: str = "generic_b2b_first_contact",
    ) -> None:
        self._repository = repository
        self._persona_generator = persona_generator or PersonaGenerator()
        self._default_scenario_id = default_scenario_id

    def start_session(
        self,
        scenario_id: str | None = None,
        persona_id: str | None = None,
    ) -> TrainingSessionState:
        scenario = get_scenario(scenario_id or self._default_scenario_id)
        persona = get_persona(persona_id) if persona_id else self._persona_generator.generate()
        starting_interest = persona.starting_interest or scenario.default_starting_interest
        now = datetime.now(tz=UTC)
        session = TrainingSessionState(
            session_id=uuid4(),
            scenario_id=scenario.id,
            status="active",
            persona=persona,
            interest_score=starting_interest,
            stage=scenario.default_stage,
            client_state=build_initial_client_state(persona, starting_interest),
            summary=(
                f"Training started for scenario '{scenario.name}'. "
                "The client's role and context are still unknown to the manager."
            ),
            public_brief=DEFAULT_PUBLIC_BRIEF,
            turns=[],
            turn_evaluations=[],
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
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        if session.status != "active":
            raise SessionNotActiveError(f"Session '{session_id}' is not active.")
        logger.info("session_resumed session_id=%s", session.session_id)
        return session
