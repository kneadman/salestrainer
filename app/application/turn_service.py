from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from pydantic import BaseModel, Field

from app.application.evaluator import evaluate_turn
from app.application.session_service import MAX_RECENT_MESSAGE_SUBMISSIONS
from app.application.summary_compressor import FakeSummaryCompressor, SummaryCompressor
from app.domain.errors import (
    MessageIdempotencyPersistenceError,
    SessionHistorySyncPendingError,
    SessionNotActiveError,
    SessionNotFoundError,
)
from app.domain.interest import apply_interest_delta, interest_band
from app.domain.models import LLMTurnInput, MessageSubmissionRecord, TrainingSessionState, Turn
from app.domain.scenarios import get_scenario
from app.domain.stages import resolve_next_stage
from app.domain.state_update import apply_state_patch
from app.infrastructure.llm_client import LLMClient
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class TurnResult(BaseModel):
    session_id: str
    client_answer: str
    interest_before: int
    interest_delta: int
    interest_after: int
    interest_band: str
    stage_before: str
    stage_after: str
    turn_index: int
    summary: str
    visible_objections: list[str] = Field(default_factory=list)
    response_payload: dict[str, Any] | None = None
    llm_payload: dict[str, Any] | None = None
    llm_response: dict[str, Any] | None = None


class TurnService:
    def __init__(
        self,
        repository: SessionRepository,
        llm_client: LLMClient,
        recent_turn_limit: int = 6,
        debug_mode: bool = False,
        summary_compressor: SummaryCompressor | None = None,
    ) -> None:
        self._repository = repository
        self._llm_client = llm_client
        self._recent_turn_limit = recent_turn_limit
        self._debug_mode = debug_mode
        self._summary_compressor = summary_compressor or FakeSummaryCompressor()

    def process_message(
        self,
        session_id: str,
        manager_message: str,
        *,
        idempotency_key: str | None = None,
    ) -> TurnResult:
        session = self._require_active_session(session_id)
        expected_version = session.state_version
        interest_before = session.interest_score
        stage_before = session.stage
        llm_input = LLMTurnInput(
            task="simulate_next_client_reply",
            scenario=get_scenario(session.scenario_id),
            hidden_profile=session.persona,
            current_state={
                "interest_score": session.interest_score,
                "interest_band": interest_band(session.interest_score),
                "stage": session.stage,
                "client_state": session.client_state.model_dump(mode="json"),
            },
            discovered_facts={
                "role": session.client_state.discovered_role,
                "authority_level": session.client_state.discovered_authority_level,
                "pains": session.client_state.discovered_pains,
                "decision_criteria": session.client_state.discovered_decision_criteria,
                "constraints": session.client_state.discovered_constraints,
                "current_process": session.client_state.discovered_current_process,
            },
            conversation_summary=session.summary,
            recent_turns=[
                {"manager": turn.manager_message, "client": turn.client_answer}
                for turn in session.recent_turns
            ],
            manager_message=manager_message,
        )
        payload_dump = llm_input.model_dump(mode="json")
        llm_response = self._llm_client.generate_client_turn(llm_input)
        response_dump = llm_response.model_dump(mode="json")
        updated_client_state = apply_state_patch(session.client_state, llm_response.state_patch)
        interest_after = apply_interest_delta(session.interest_score, llm_response.interest_delta)
        resolved_stage = resolve_next_stage(
            stage_before,
            llm_response.stage,
            interest_score=interest_after,
            client_state=updated_client_state,
        )
        now = datetime.now(tz=UTC)
        turn = Turn(
            index=session.turn_count + 1,
            manager_message=manager_message,
            client_answer=llm_response.answer,
            interest_before=interest_before,
            interest_delta=llm_response.interest_delta,
            interest_after=interest_after,
            stage_before=stage_before,
            stage_after=resolved_stage,
            created_at=now,
        )
        full_turns = [*session.turns, turn]
        recent_turns = [*session.recent_turns, turn][-self._recent_turn_limit :]
        overflow_turns = [*session.recent_turns, turn][:-self._recent_turn_limit]
        evaluation = evaluate_turn(
            turn_index=turn.index,
            manager_message=manager_message,
            client_state=updated_client_state,
            hidden_profile=session.persona,
        )
        session.interest_score = interest_after
        session.stage = resolved_stage
        session.client_state = updated_client_state
        session.turns = full_turns
        session.turn_evaluations = [*session.turn_evaluations, evaluation]
        session.recent_turns = recent_turns
        session.turn_count += 1
        session.state_version = expected_version + 1
        session.updated_at = now
        session.summary = self._update_summary(
            session,
            latest_internal_notes=llm_response.internal_notes,
            overflow_turns=overflow_turns,
        )
        response_payload = self._build_response_payload(
            session,
            turn=turn,
            interest_before=interest_before,
            stage_before=stage_before,
        )
        if idempotency_key is not None:
            session.recent_message_submissions = self._append_message_submission(
                session,
                idempotency_key=idempotency_key,
                manager_message=manager_message,
                response_payload=response_payload,
                created_at=now,
            )
        try:
            self._repository.save(session, expected_version=expected_version)
        except Exception as error:
            logger.critical(
                "turn_runtime_save_failed session_id=%s turn_index=%s idempotency_key=%s",
                session.session_id,
                turn.index,
                idempotency_key,
                exc_info=True,
            )
            if idempotency_key is not None:
                raise MessageIdempotencyPersistenceError(
                    "The turn could not be safely persisted for idempotent retry. "
                    "Please retry this action instead of resending the last message."
                ) from error
            raise
        logger.info(
            "turn_processed session_id=%s turn_index=%s interest_before=%s interest_after=%s stage_before=%s stage_after=%s",
            session.session_id,
            turn.index,
            interest_before,
            interest_after,
            stage_before,
            session.stage,
        )
        return TurnResult(
            session_id=str(session.session_id),
            client_answer=turn.client_answer,
            interest_before=interest_before,
            interest_delta=turn.interest_delta,
            interest_after=interest_after,
            interest_band=interest_band(interest_after),
            stage_before=stage_before,
            stage_after=session.stage,
            turn_index=turn.index,
            summary=session.summary,
            visible_objections=session.client_state.open_objections,
            response_payload=response_payload,
            llm_payload=payload_dump if self._debug_mode else None,
            llm_response=response_dump if self._debug_mode else None,
        )

    def _require_active_session(self, session_id: str) -> TrainingSessionState:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        if session.status != "active":
            raise SessionNotActiveError(f"Session '{session_id}' is not active.")
        if session.history_sync_status != "ok":
            raise SessionHistorySyncPendingError(
                "The previous turn was processed, but session history is still being reconciled. "
                "Please retry this action instead of resending the last message."
            )
        return session

    def _build_summary(self, session: TrainingSessionState, internal_notes: str) -> str:
        notes = internal_notes.strip() or "No extra notes."
        last_turn = session.recent_turns[-1] if session.recent_turns else None
        if last_turn is None:
            return notes
        summary = (
            f"Stage: {session.stage}. "
            f"Interest: {session.interest_score}/100 ({interest_band(session.interest_score)}). "
            f"Last manager move: {last_turn.manager_message[:120]}. "
            f"Client reaction: {last_turn.client_answer[:120]}. "
            f"Notes: {notes[:180]}"
        )
        return summary[:500]

    def _update_summary(
        self,
        session: TrainingSessionState,
        *,
        latest_internal_notes: str,
        overflow_turns: list[Turn],
    ) -> str:
        if overflow_turns:
            return self._summary_compressor.compress(
                existing_summary=session.summary,
                overflow_turns=overflow_turns,
                session=session,
                latest_internal_notes=latest_internal_notes,
            )
        return self._build_summary(session, latest_internal_notes)

    def _build_response_payload(
        self,
        session: TrainingSessionState,
        *,
        turn: Turn,
        interest_before: int,
        stage_before: str,
    ) -> dict[str, Any]:
        """Build the public-safe turn response payload stored for idempotent retries."""
        return {
            "session": {
                "session_id": str(session.session_id),
                "scenario_id": session.scenario_id,
                "status": session.status,
                "persona_name": session.persona.display_name,
                "public_brief": session.public_brief,
                "stage": session.stage,
                "interest": {
                    "score": session.interest_score,
                    "band": interest_band(session.interest_score),
                },
                "client_state_public": {
                    "tone": session.client_state.tone,
                    "trust": session.client_state.trust,
                    "visible_objections": session.client_state.open_objections,
                    "known_pains": session.client_state.known_pains,
                    "buying_signals": session.client_state.buying_signals,
                    "discovered_role": session.client_state.discovered_role,
                    "discovered_authority_level": session.client_state.discovered_authority_level,
                    "discovered_decision_criteria": session.client_state.discovered_decision_criteria,
                    "discovered_constraints": session.client_state.discovered_constraints,
                    "discovered_current_process": session.client_state.discovered_current_process,
                },
                "turn_count": session.turn_count,
                "summary": session.summary,
                "state_version": session.state_version,
            },
            "turns": [
                {
                    "turn_index": session_turn.index,
                    "manager_message": session_turn.manager_message,
                    "client_answer": session_turn.client_answer,
                    "interest_before": session_turn.interest_before,
                    "interest_delta": session_turn.interest_delta,
                    "interest_after": session_turn.interest_after,
                    "stage_before": session_turn.stage_before,
                    "stage_after": session_turn.stage_after,
                    "created_at": session_turn.created_at,
                }
                for session_turn in session.turns
            ],
            "client_answer": turn.client_answer,
            "interest_before": interest_before,
            "interest_delta": turn.interest_delta,
            "interest_after": turn.interest_after,
            "stage_before": stage_before,
            "stage_after": session.stage,
            "turn_index": turn.index,
        }

    def _append_message_submission(
        self,
        session: TrainingSessionState,
        *,
        idempotency_key: str,
        manager_message: str,
        response_payload: dict[str, Any],
        created_at: datetime,
    ) -> list[MessageSubmissionRecord]:
        """Return the bounded submission cache including the latest idempotent message result."""
        existing_records = [
            record for record in session.recent_message_submissions
            if record.idempotency_key != idempotency_key
        ]
        return [
            *existing_records[-(MAX_RECENT_MESSAGE_SUBMISSIONS - 1):],
            MessageSubmissionRecord(
                idempotency_key=idempotency_key,
                manager_message=manager_message,
                response_payload=response_payload,
                created_at=created_at,
            ),
        ]
