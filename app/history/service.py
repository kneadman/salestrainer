from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.application.turn_service import TurnResult
from app.domain.models import TrainingSessionState
from app.history.events import UsageEventType
from app.history.projections import report_dto, session_summary_dto, turn_dto
from app.history.repository import HistoryRepository, SessionListFilters
from app.history.schemas import (
    HistoryReportDTO,
    HistorySessionDetailDTO,
    HistorySessionSummaryDTO,
    UsageSummaryDTO,
)
from app.identity.roles import UserRole, normalize_role


class HistoryNotFoundError(LookupError):
    pass


class HistoryAccessDeniedError(LookupError):
    pass


class HistoryService:
    def __init__(self, repository: HistoryRepository) -> None:
        """Keep the repository that owns all persistent history database access."""
        self._repository = repository

    def record_session_started(
        self,
        *,
        session: TrainingSessionState,
        client_account_id: UUID,
        user_id: UUID,
        training_config_id: UUID | None,
    ) -> None:
        """Persist the initial history row and usage event for a new API session."""
        self._repository.create_session_with_event(
            session_kwargs={
                "id": session.session_id,
                "client_account_id": client_account_id,
                "user_id": user_id,
                "training_config_id": training_config_id,
                "scenario_id": session.scenario_id,
                "status": session.status,
                "started_at": session.created_at,
                "last_activity_at": session.updated_at,
                "persona_snapshot": session.persona.model_dump(mode="json"),
                "initial_state_snapshot": self._session_snapshot(session),
                "public_brief": session.public_brief,
                "summary": session.summary,
            },
            event_kwargs=self._usage_event_kwargs(
                event_type=UsageEventType.SESSION_STARTED.value,
                client_account_id=client_account_id,
                user_id=user_id,
                training_config_id=training_config_id,
                session_id=session.session_id,
                event_payload={"scenario_id": session.scenario_id},
            ),
        )

    def record_turn_processed(
        self,
        *,
        session: TrainingSessionState,
        turn_result: TurnResult,
        user_id: UUID,
        client_account_id: UUID,
        training_config_id: UUID | None,
    ) -> None:
        """Persist one processed turn and update the durable session rollup fields."""
        turn = session.turns[-1]
        evaluation = session.turn_evaluations[-1] if session.turn_evaluations else None
        self._repository.record_turn_with_rollup_and_event(
            session_id=session.session_id,
            turn_kwargs={
                "session_id": session.session_id,
                "turn_index": turn.index,
                "manager_message": turn.manager_message,
                "client_answer": turn.client_answer,
                "interest_before": turn.interest_before,
                "interest_delta": turn.interest_delta,
                "interest_after": turn.interest_after,
                "stage_before": turn.stage_before,
                "stage_after": turn.stage_after,
                "client_state_snapshot": session.client_state.model_dump(mode="json"),
                "llm_payload_snapshot": self._safe_payload_snapshot(turn_result.llm_payload),
                "llm_response_snapshot": self._safe_response_snapshot(turn_result.llm_response),
                "evaluation_snapshot": evaluation.model_dump(mode="json") if evaluation is not None else None,
                "created_at": turn.created_at,
            },
            rollup={
                "turn_count": session.turn_count,
                "last_activity_at": session.updated_at,
                "summary": session.summary,
                "final_interest_score": session.interest_score,
                "final_stage": session.stage,
                "final_state_snapshot": self._session_snapshot(session),
            },
            event_kwargs=self._usage_event_kwargs(
                event_type=UsageEventType.TURN_PROCESSED.value,
                client_account_id=client_account_id,
                user_id=user_id,
                training_config_id=training_config_id,
                session_id=session.session_id,
                event_payload={"turn_index": turn.index, "interest_after": turn.interest_after, "stage_after": turn.stage_after},
            ),
        )

    def record_session_finished(
        self,
        *,
        session: TrainingSessionState,
        user_id: UUID,
        client_account_id: UUID,
        training_config_id: UUID | None,
    ) -> None:
        """Persist the final session state and a finish usage event."""
        finished_at = session.updated_at or datetime.now(tz=UTC)
        self._repository.finish_session(
            session_id=session.session_id,
            finished_at=finished_at,
            final_interest_score=session.interest_score,
            final_stage=session.stage,
            final_state_snapshot=self._session_snapshot(session),
            summary=session.summary,
            turn_count=session.turn_count,
        )
        self.record_usage_event(
            event_type=UsageEventType.SESSION_FINISHED.value,
            client_account_id=client_account_id,
            user_id=user_id,
            training_config_id=training_config_id,
            session_id=session.session_id,
            event_payload={"turn_count": session.turn_count, "final_interest_score": session.interest_score, "final_stage": session.stage},
        )

    def record_report_generated(
        self,
        *,
        session: TrainingSessionState,
        report_text: str,
        report_payload: dict[str, object] | None = None,
        user_id: UUID,
        client_account_id: UUID,
        training_config_id: UUID | None,
    ) -> HistoryReportDTO:
        """Save the final report and record report generation as usage."""
        report = self._repository.upsert_report(
            session_id=session.session_id,
            report_text=report_text,
            report_payload=report_payload
            or {
                "status": session.status,
                "turn_count": session.turn_count,
                "final_interest_score": session.interest_score,
                "final_stage": session.stage,
            },
        )
        self.record_usage_event(
            event_type=UsageEventType.REPORT_GENERATED.value,
            client_account_id=client_account_id,
            user_id=user_id,
            training_config_id=training_config_id,
            session_id=session.session_id,
            event_payload={"report_version": report.report_version},
        )
        return report_dto(report)

    def record_usage_event(
        self,
        *,
        event_type: str,
        client_account_id: UUID | None = None,
        user_id: UUID | None = None,
        training_config_id: UUID | None = None,
        session_id: UUID | None = None,
        event_payload: dict[str, object] | None = None,
    ) -> None:
        """Record one usage event through the repository."""
        self._repository.create_usage_event(
            event_type=event_type,
            client_account_id=client_account_id,
            user_id=user_id,
            training_config_id=training_config_id,
            session_id=session_id,
            event_payload=event_payload or {},
        )

    def record_session_finished_with_report(
        self,
        *,
        session: TrainingSessionState,
        report_text: str,
        report_payload: dict[str, object] | None = None,
        user_id: UUID,
        client_account_id: UUID,
        training_config_id: UUID | None,
    ) -> HistoryReportDTO:
        """Persist finish state, final report, and usage events in one commit."""
        finished_at = session.updated_at or datetime.now(tz=UTC)
        report = self._repository.finish_session_with_report_and_events(
            session_id=session.session_id,
            finish={
                "status": "finished",
                "finished_at": finished_at,
                "last_activity_at": finished_at,
                "final_interest_score": session.interest_score,
                "final_stage": session.stage,
                "final_state_snapshot": self._session_snapshot(session),
                "summary": session.summary,
                "turn_count": session.turn_count,
            },
            report_text=report_text,
            report_payload=report_payload
            or {
                "status": session.status,
                "turn_count": session.turn_count,
                "final_interest_score": session.interest_score,
                "final_stage": session.stage,
            },
            finish_event_kwargs=self._usage_event_kwargs(
                event_type=UsageEventType.SESSION_FINISHED.value,
                client_account_id=client_account_id,
                user_id=user_id,
                training_config_id=training_config_id,
                session_id=session.session_id,
                event_payload={"turn_count": session.turn_count, "final_interest_score": session.interest_score, "final_stage": session.stage},
            ),
            report_event_kwargs=self._usage_event_kwargs(
                event_type=UsageEventType.REPORT_GENERATED.value,
                client_account_id=client_account_id,
                user_id=user_id,
                training_config_id=training_config_id,
                session_id=session.session_id,
                event_payload={"report_version": 1},
            ),
        )
        return report_dto(report)

    def _usage_event_kwargs(
        self,
        *,
        event_type: str,
        client_account_id: UUID | None = None,
        user_id: UUID | None = None,
        training_config_id: UUID | None = None,
        session_id: UUID | None = None,
        event_payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Build UsageEventRecord kwargs without committing separately."""
        return {
            "event_type": event_type,
            "client_account_id": client_account_id,
            "user_id": user_id,
            "training_config_id": training_config_id,
            "session_id": session_id,
            "event_payload": event_payload or {},
        }

    def get_user_history(
        self,
        *,
        requester_user_id: UUID,
        requester_client_account_id: UUID,
        requester_role: str,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[HistorySessionSummaryDTO]:
        """Return history scoped by requester role without exposing hidden snapshots."""
        normalized_role = normalize_role(requester_role)
        if normalized_role == UserRole.CLIENT_MANAGER:
            rows = self._repository.list_sessions_for_user(
                user_id=requester_user_id,
                filters=SessionListFilters(
                    status=filters.status,
                    scenario_id=filters.scenario_id,
                    training_config_id=filters.training_config_id,
                    user_id=requester_user_id,
                ),
                limit=limit,
                offset=offset,
            )
        elif normalized_role == UserRole.CLIENT_LEAD:
            rows = self._repository.list_sessions_for_client_account(
                client_account_id=requester_client_account_id,
                filters=filters,
                limit=limit,
                offset=offset,
            )
        else:
            rows = self._repository.list_all_sessions(filters=filters, limit=limit, offset=offset)
        self.record_usage_event(
            event_type=UsageEventType.HISTORY_VIEWED.value,
            client_account_id=requester_client_account_id,
            user_id=requester_user_id,
            event_payload={"limit": limit, "offset": offset},
        )
        return [session_summary_dto(record, user_email=email) for record, email in rows]

    def get_session_history_detail(
        self,
        *,
        session_id: UUID,
        requester_user_id: UUID,
        requester_client_account_id: UUID,
        requester_role: str,
    ) -> HistorySessionDetailDTO:
        """Return public-safe detail for a session after enforcing requester access."""
        record = self._require_access(
            session_id=session_id,
            requester_user_id=requester_user_id,
            requester_client_account_id=requester_client_account_id,
            requester_role=requester_role,
        )
        self.record_usage_event(
            event_type=UsageEventType.SESSION_VIEWED.value,
            client_account_id=record.client_account_id,
            user_id=requester_user_id,
            training_config_id=record.training_config_id,
            session_id=record.id,
        )
        email = self._repository.get_user_email(record.user_id) or ""
        report = self._repository.get_report(record.id)
        return HistorySessionDetailDTO(
            session=session_summary_dto(record, user_email=email),
            public_brief=record.public_brief,
            turns=[turn_dto(turn) for turn in self._repository.list_turns_for_session(record.id)],
            report=report_dto(report) if report is not None else None,
        )

    def get_saved_report(
        self,
        *,
        session_id: UUID,
        requester_user_id: UUID,
        requester_client_account_id: UUID,
        requester_role: str,
    ) -> HistoryReportDTO:
        """Return a saved report after enforcing requester access."""
        self._require_access(
            session_id=session_id,
            requester_user_id=requester_user_id,
            requester_client_account_id=requester_client_account_id,
            requester_role=requester_role,
        )
        report = self._repository.get_report(session_id)
        if report is None:
            raise HistoryNotFoundError("Report not found.")
        return report_dto(report)

    def get_saved_report_payload(self, session_id: UUID) -> dict[str, object] | None:
        """Return saved structured report payload when it already exists."""
        report = self._repository.get_report(session_id)
        if report is None:
            return None
        return report.report_payload

    def list_organization_history(
        self,
        *,
        client_account_id: UUID,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[HistorySessionSummaryDTO]:
        """Return organization-scoped history for internal admin endpoints."""
        rows = self._repository.list_sessions_for_client_account(
            client_account_id=client_account_id,
            filters=filters,
            limit=limit,
            offset=offset,
        )
        return [session_summary_dto(record, user_email=email) for record, email in rows]

    def list_user_history(
        self,
        *,
        user_id: UUID,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[HistorySessionSummaryDTO]:
        """Return one user's history for internal admin endpoints."""
        rows = self._repository.list_sessions_for_user(user_id=user_id, filters=filters, limit=limit, offset=offset)
        return [session_summary_dto(record, user_email=email) for record, email in rows]

    def get_client_usage_summary(self, *, client_account_id: UUID) -> UsageSummaryDTO:
        """Return basic organization usage metrics as an API DTO."""
        return UsageSummaryDTO.model_validate(self._repository.usage_summary(client_account_id))

    def _require_access(
        self,
        *,
        session_id: UUID,
        requester_user_id: UUID,
        requester_client_account_id: UUID,
        requester_role: str,
    ):
        """Enforce manager/lead visibility rules for client-facing history reads."""
        record = self._repository.get_session(session_id)
        if record is None:
            raise HistoryNotFoundError("Session not found.")
        normalized_role = normalize_role(requester_role)
        if normalized_role == UserRole.CLIENT_MANAGER and record.user_id != requester_user_id:
            raise HistoryAccessDeniedError("Session not found.")
        if normalized_role == UserRole.CLIENT_LEAD and record.client_account_id != requester_client_account_id:
            raise HistoryAccessDeniedError("Session not found.")
        return record

    def _session_snapshot(self, session: TrainingSessionState) -> dict[str, object]:
        """Build a bounded state snapshot that excludes the hidden persona object."""
        return {
            "status": session.status,
            "scenario_id": session.scenario_id,
            "interest_score": session.interest_score,
            "stage": session.stage,
            "client_state": session.client_state.model_dump(mode="json"),
            "turn_count": session.turn_count,
            "state_version": session.state_version,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

    def _safe_payload_snapshot(self, payload: dict[str, object] | None) -> dict[str, object] | None:
        """Strip hidden profile and provider internals from a debug LLM payload snapshot."""
        if payload is None:
            return None
        return {
            "task": payload.get("task"),
            "scenario": payload.get("scenario"),
            "current_state": payload.get("current_state"),
            "discovered_facts": payload.get("discovered_facts"),
            "conversation_summary": payload.get("conversation_summary"),
            "recent_turns": payload.get("recent_turns"),
            "manager_message": payload.get("manager_message"),
        }

    def _safe_response_snapshot(self, response: dict[str, object] | None) -> dict[str, object] | None:
        """Strip internal notes from a debug LLM response snapshot before persistence."""
        if response is None:
            return None
        return {
            "answer": response.get("answer"),
            "interest_delta": response.get("interest_delta"),
            "state_patch": response.get("state_patch"),
            "stage": response.get("stage"),
        }
