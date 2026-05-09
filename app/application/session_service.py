from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any
from uuid import uuid4

from app.access.models import RuntimeTrainingConfig
from app.domain.persona_generation import UniversalFakePersonaGenerator
from app.domain.interest import interest_band
from app.domain.errors import SessionHistorySyncPendingError, SessionNotActiveError, SessionNotFoundError
from app.domain.models import ClientState, MessageSubmissionRecord, PersonaProfile, TrainingSessionState
from app.domain.personas import get_persona
from app.domain.scenarios import get_scenario
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)
MAX_RECENT_MESSAGE_SUBMISSIONS = 20

DEFAULT_PUBLIC_BRIEF = (
    "Вы начали первичный B2B-диалог с потенциальным клиентом. "
    "Роль, полномочия и ситуация клиента неизвестны. "
    "Задавайте правильные вопросы и отрабатывайте возражения, чтобы склонить клиента на свою сторону."
)


def build_initial_client_state(persona: PersonaProfile, starting_interest: int) -> ClientState:
    """Build public runtime state from the hidden persona without revealing hidden facts."""
    return ClientState(
        tone=interest_band(starting_interest) if starting_interest <= 60 else "warm",
        trust=persona.trust_baseline,
        irritation=10,
        urgency=persona.urgency,
        price_sensitivity=persona.price_sensitivity,
        open_objections=[],
        known_pains=[],
        buying_signals=[],
        red_flags=[],
    )


class TrainingSessionService:
    def __init__(
        self,
        repository: SessionRepository,
        *,
        persona_generator: UniversalFakePersonaGenerator | None = None,
        default_scenario_id: str = "first_contact_discovery",
    ) -> None:
        """Keep runtime repository and local persona fallback for CLI/debug flows."""
        self._repository = repository
        self._persona_generator = persona_generator or UniversalFakePersonaGenerator()
        self._default_scenario_id = default_scenario_id

    def start_session(
        self,
        scenario_id: str | None = None,
        persona_id: str | None = None,
        training_config: RuntimeTrainingConfig | None = None,
        persona_override: PersonaProfile | None = None,
    ) -> TrainingSessionState:
        """Start a runtime session with either generated, preset, or externally generated persona."""
        resolved_scenario_id = scenario_id or self._default_scenario_id

        scenario = get_scenario(resolved_scenario_id)
        if persona_override is not None:
            persona = persona_override
        elif training_config is not None:
            persona = self._persona_generator.generate(scenario=scenario, persona_policy={})
        else:
            persona = (
                get_persona(persona_id)
                if persona_id
                else self._persona_generator.generate(scenario=scenario)
            )
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
        """Return a runtime session snapshot if it still exists in the session repository."""
        return self._repository.get(session_id)

    def delete_session(self, session_id: str) -> None:
        """Remove a runtime session during API-side compensation or cleanup."""
        self._repository.delete(session_id)

    def resume_session(self, session_id: str) -> TrainingSessionState:
        """Resume an active runtime session or raise a domain error."""
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        if session.status != "active":
            raise SessionNotActiveError(f"Session '{session_id}' is not active.")
        logger.info("session_resumed session_id=%s", session.session_id)
        return session

    def mark_history_sync_pending(self, session_id: str, *, reason: str) -> TrainingSessionState:
        """Persist a runtime flag that blocks new work until history is reconciled."""
        session = self._require_session(session_id)
        expected_version = session.state_version
        session.history_sync_status = "pending_retry"
        session.history_sync_error = reason
        session.state_version = expected_version + 1
        session.updated_at = datetime.now(tz=UTC)
        self._repository.save(session, expected_version=expected_version)
        logger.warning("session_history_sync_pending session_id=%s reason=%s", session.session_id, reason)
        return session

    def clear_history_sync_pending(self, session_id: str) -> TrainingSessionState:
        """Clear the runtime history-sync flag after successful reconciliation."""
        session = self._require_session(session_id)
        expected_version = session.state_version
        session.history_sync_status = "ok"
        session.history_sync_error = None
        session.state_version = expected_version + 1
        session.updated_at = datetime.now(tz=UTC)
        self._repository.save(session, expected_version=expected_version)
        logger.info("session_history_sync_restored session_id=%s", session.session_id)
        return session

    def require_history_sync_ready(self, session_id: str) -> TrainingSessionState:
        """Return the runtime session when it is not blocked by pending history sync."""
        session = self.resume_session(session_id)
        if session.history_sync_status != "ok":
            raise SessionHistorySyncPendingError(
                "The previous turn was processed, but session history is still being reconciled. "
                "Please retry this action instead of resending the last message."
            )
        return session

    def get_message_submission(self, session_id: str, idempotency_key: str) -> MessageSubmissionRecord | None:
        """Return one saved message submission record for the runtime session when present."""
        session = self._require_session(session_id)
        for record in reversed(session.recent_message_submissions):
            if record.idempotency_key == idempotency_key:
                return record
        return None

    def save_message_submission(
        self,
        session_id: str,
        *,
        idempotency_key: str,
        manager_message: str,
        response_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist one recent idempotent message result and return the stored response payload."""
        session = self._require_session(session_id)
        expected_version = session.state_version
        now = datetime.now(tz=UTC)
        existing_records = [
            record for record in session.recent_message_submissions
            if record.idempotency_key != idempotency_key
        ]
        updated_payload = {
            **response_payload,
            "session": {
                **dict(response_payload["session"]),
                "state_version": expected_version + 1,
            },
        }
        session.recent_message_submissions = [
            *existing_records[-(MAX_RECENT_MESSAGE_SUBMISSIONS - 1):],
            MessageSubmissionRecord(
                idempotency_key=idempotency_key,
                manager_message=manager_message,
                response_payload=updated_payload,
                created_at=now,
            ),
        ]
        session.state_version = expected_version + 1
        session.updated_at = now
        self._repository.save(session, expected_version=expected_version)
        return updated_payload

    def _require_session(self, session_id: str) -> TrainingSessionState:
        """Load a runtime session or raise a not-found domain error."""
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        return session
