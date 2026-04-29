from __future__ import annotations

from datetime import UTC, datetime
import logging

from app.domain.errors import SessionNotFoundError
from app.domain.interest import interest_band
from app.domain.models import TurnEvaluation
from app.infrastructure.session_repository import SessionRepository

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

    def finish_session(self, session_id: str) -> str:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        expected_version = session.state_version
        if session.status != "finished":
            session.status = "finished"
            session.state_version = expected_version + 1
            session.updated_at = datetime.now(tz=UTC)
            self._repository.save(session, expected_version=expected_version)
            logger.info(
                "session_finished session_id=%s turns=%s final_interest=%s final_stage=%s",
                session.session_id,
                session.turn_count,
                session.interest_score,
                session.stage,
            )
        return self.generate_report(session_id)

    def generate_report(self, session_id: str) -> str:
        session = self._repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session '{session_id}' not found.")
        objections = ", ".join(session.client_state.open_objections) or "none"
        signals = ", ".join(session.client_state.buying_signals) or "none"
        hidden_pains = ", ".join(session.persona.latent_pains) or "none"
        discovered_pains = ", ".join(session.client_state.discovered_pains) or "none"
        missed_pains = ", ".join(
            [pain for pain in session.persona.latent_pains if pain not in session.client_state.discovered_pains]
        ) or "none"
        notes = self._report_recommendations(session.turn_evaluations)
        return (
            f"Session {session.session_id}\n"
            f"Scenario: {session.scenario_id}\n"
            f"Hidden role: {session.persona.role}\n"
            f"Authority level: {session.persona.authority_level}\n"
            f"Communication style: {session.persona.communication_style}\n"
            f"Current context: {session.persona.current_business_context}\n"
            f"Turns: {session.turn_count}\n"
            f"Final interest: {session.interest_score}/100 ({interest_band(session.interest_score)})\n"
            f"Final stage: {session.stage}\n"
            f"Hidden pains: {hidden_pains}\n"
            f"Discovered pains: {discovered_pains}\n"
            f"Missed pains: {missed_pains}\n"
            f"Discovered role: {session.client_state.discovered_role or 'not identified'}\n"
            f"Discovered authority: {session.client_state.discovered_authority_level or 'not identified'}\n"
            f"Open objections: {objections}\n"
            f"Buying signals: {signals}\n"
            f"Discovery score: {self._average_score(session.turn_evaluations, 'discovery_quality_score')}/5\n"
            f"Role identification score: {self._average_score(session.turn_evaluations, 'role_identification_score')}/5\n"
            f"Pain identification score: {self._average_score(session.turn_evaluations, 'pain_identification_score')}/5\n"
            f"Relevance score: {self._average_score(session.turn_evaluations, 'relevance_score')}/5\n"
            f"Pressure score: {self._average_score(session.turn_evaluations, 'pressure_score')}/5\n"
            f"Objection handling score: {self._average_score(session.turn_evaluations, 'objection_handling_score')}/5\n"
            f"Next step timing score: {self._average_score(session.turn_evaluations, 'next_step_timing_score')}/5\n"
            f"Conversation control score: {self._average_score(session.turn_evaluations, 'conversation_control_score')}/5\n"
            f"What worked: {notes['worked']}\n"
            f"What to ask next time: {notes['missing_questions']}\n"
            f"Early pitch risk: {notes['pressure']}\n"
            f"Summary: {session.summary}"
        )

    def _average_score(self, evaluations: list[TurnEvaluation], field_name: str) -> int:
        if not evaluations:
            return 0
        total = sum(int(getattr(item, field_name)) for item in evaluations)
        return round(total / len(evaluations))

    def _report_recommendations(self, evaluations: list[TurnEvaluation]) -> dict[str, str]:
        notes = [note for item in evaluations for note in item.notes]
        worked = "; ".join(notes[:3]) or "Manager kept the conversation moving."
        pressure = "There were early pressure attempts." if any("pressure" in note.lower() for note in notes) else "No major early pressure."
        missing_questions = (
            "Ask about role, authority, current process, concrete pain, and decision criteria earlier."
        )
        return {
            "worked": worked,
            "pressure": pressure,
            "missing_questions": missing_questions,
        }
