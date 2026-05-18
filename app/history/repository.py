from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, desc, distinct, func, select, update
from sqlalchemy.orm import Session

from app.domain.contract_versions import JUDGE_PROMPT_VERSION, JUDGE_SCHEMA_VERSION
from app.history.models import (
    TrainingReportRecord,
    TrainingSessionRecord,
    TrainingTurnRecord,
    UsageEventRecord,
)
from app.access.models import ClientTrainingConfig
from app.identity.models import User


@dataclass(frozen=True)
class SessionListFilters:
    status: str | None = None
    scenario_id: str | None = None
    training_config_id: UUID | None = None
    user_id: UUID | None = None


class HistoryRepository:
    def __init__(self, session: Session) -> None:
        """Keep the SQLAlchemy session used for all persistent history queries."""
        self._session = session

    def create_session(
        self,
        *,
        session_id: UUID,
        client_account_id: UUID,
        user_id: UUID,
        training_config_id: UUID | None,
        scenario_id: str,
        status: str,
        started_at: datetime,
        last_activity_at: datetime,
        persona_snapshot: dict[str, object],
        initial_state_snapshot: dict[str, object],
        public_brief: str | None,
        summary: str | None,
    ) -> TrainingSessionRecord:
        """Insert the durable session row that mirrors a newly created runtime session."""
        record = TrainingSessionRecord(
            id=session_id,
            client_account_id=client_account_id,
            user_id=user_id,
            training_config_id=training_config_id,
            scenario_id=scenario_id,
            status=status,
            started_at=started_at,
            last_activity_at=last_activity_at,
            persona_snapshot=persona_snapshot,
            initial_state_snapshot=initial_state_snapshot,
            public_brief=public_brief,
            summary=summary,
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get_session(self, session_id: UUID) -> TrainingSessionRecord | None:
        """Load one persistent session by its runtime-compatible UUID."""
        return self._session.get(TrainingSessionRecord, session_id)

    def update_session_after_turn(
        self,
        *,
        session_id: UUID,
        turn_count: int,
        last_activity_at: datetime,
        summary: str,
        final_interest_score: int,
        final_stage: str,
        final_state_snapshot: dict[str, object],
    ) -> TrainingSessionRecord | None:
        """Update session-level summary fields after a processed manager turn."""
        record = self.get_session(session_id)
        if record is None:
            return None
        record.turn_count = turn_count
        record.last_activity_at = last_activity_at
        record.summary = summary
        record.final_interest_score = final_interest_score
        record.final_stage = final_stage
        record.final_state_snapshot = final_state_snapshot
        self._session.commit()
        self._session.refresh(record)
        return record

    def finish_session(
        self,
        *,
        session_id: UUID,
        finished_at: datetime,
        final_interest_score: int,
        final_stage: str,
        final_state_snapshot: dict[str, object],
        summary: str,
        turn_count: int,
    ) -> TrainingSessionRecord | None:
        """Mark a persistent session as finished and store final state fields."""
        record = self.get_session(session_id)
        if record is None:
            return None
        record.status = "finished"
        record.finished_at = finished_at
        record.last_activity_at = finished_at
        record.final_interest_score = final_interest_score
        record.final_stage = final_stage
        record.final_state_snapshot = final_state_snapshot
        record.summary = summary
        record.turn_count = turn_count
        self._session.commit()
        self._session.refresh(record)
        return record

    def expire_session(self, *, session_id: UUID, expired_at: datetime | None = None) -> TrainingSessionRecord | None:
        """Mark one active persistent session as expired without exposing hidden runtime state."""
        record = self.get_session(session_id)
        if record is None or record.status != "active":
            return record
        record.status = "expired"
        record.finished_at = expired_at or record.last_activity_at
        self._session.commit()
        self._session.refresh(record)
        return record

    def touch_session_activity(self, *, session_id: UUID, touched_at: datetime) -> TrainingSessionRecord | None:
        """Refresh durable last activity for one active persistent session."""
        record = self.get_session(session_id)
        if record is None or record.status != "active":
            return record
        record.last_activity_at = touched_at
        record.updated_at = touched_at
        self._session.commit()
        self._session.refresh(record)
        return record

    def expire_active_sessions(
        self,
        *,
        last_activity_before: datetime,
        client_account_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> int:
        """Bulk-expire active persistent sessions whose durable last activity is stale."""
        conditions = [
            TrainingSessionRecord.status == "active",
            TrainingSessionRecord.last_activity_at < last_activity_before,
        ]
        if client_account_id is not None:
            conditions.append(TrainingSessionRecord.client_account_id == client_account_id)
        if user_id is not None:
            conditions.append(TrainingSessionRecord.user_id == user_id)
        statement = (
            update(TrainingSessionRecord)
            .where(and_(*conditions))
            .values(
                status="expired",
                finished_at=TrainingSessionRecord.last_activity_at,
                updated_at=func.now(),
            )
            .execution_options(synchronize_session=False)
        )
        result = self._session.execute(statement)
        self._session.commit()
        return int(result.rowcount or 0)

    def append_turn(
        self,
        *,
        session_id: UUID,
        turn_index: int,
        manager_message: str,
        client_answer: str,
        interest_before: int,
        interest_delta: int,
        interest_after: int,
        stage_before: str,
        stage_after: str,
        client_state_snapshot: dict[str, object] | None,
        llm_payload_snapshot: dict[str, object] | None,
        llm_response_snapshot: dict[str, object] | None,
        evaluation_snapshot: dict[str, object] | None,
        created_at: datetime,
    ) -> TrainingTurnRecord:
        """Append one durable turn row for a processed runtime turn."""
        record = TrainingTurnRecord(
            session_id=session_id,
            turn_index=turn_index,
            manager_message=manager_message,
            client_answer=client_answer,
            interest_before=interest_before,
            interest_delta=interest_delta,
            interest_after=interest_after,
            stage_before=stage_before,
            stage_after=stage_after,
            client_state_snapshot=client_state_snapshot,
            llm_payload_snapshot=llm_payload_snapshot,
            llm_response_snapshot=llm_response_snapshot,
            evaluation_snapshot=evaluation_snapshot,
            created_at=created_at,
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def upsert_report(
        self,
        *,
        session_id: UUID,
        report_text: str,
        report_payload: dict[str, object] | None = None,
        report_version: int = 1,
        judge_schema_version: str = JUDGE_SCHEMA_VERSION,
        judge_prompt_version: str = JUDGE_PROMPT_VERSION,
    ) -> TrainingReportRecord:
        """Create or replace the saved final report for one session."""
        record = self.get_report(session_id)
        if record is None:
            record = TrainingReportRecord(
                session_id=session_id,
                report_text=report_text,
                report_payload=report_payload,
                report_version=report_version,
                judge_schema_version=judge_schema_version,
                judge_prompt_version=judge_prompt_version,
            )
            self._session.add(record)
        else:
            record.report_text = report_text
            record.report_payload = report_payload
            record.report_version = report_version
            record.judge_schema_version = judge_schema_version
            record.judge_prompt_version = judge_prompt_version
        self._session.commit()
        self._session.refresh(record)
        return record

    def create_usage_event(
        self,
        *,
        event_type: str,
        client_account_id: UUID | None = None,
        user_id: UUID | None = None,
        training_config_id: UUID | None = None,
        session_id: UUID | None = None,
        event_payload: dict[str, object] | None = None,
    ) -> UsageEventRecord:
        """Insert one minimal usage event for future analytics."""
        record = UsageEventRecord(
            client_account_id=client_account_id,
            user_id=user_id,
            training_config_id=training_config_id,
            session_id=session_id,
            event_type=event_type,
            event_payload=event_payload or {},
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def create_session_with_event(
        self,
        *,
        session_kwargs: dict[str, object],
        event_kwargs: dict[str, object],
    ) -> TrainingSessionRecord:
        """Create a history session and its usage event in one database commit."""
        record = TrainingSessionRecord(**session_kwargs)
        event = UsageEventRecord(**event_kwargs)
        self._session.add_all([record, event])
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._session.refresh(record)
        return record

    def record_turn_with_rollup_and_event(
        self,
        *,
        turn_kwargs: dict[str, object],
        session_id: UUID,
        rollup: dict[str, object],
        event_kwargs: dict[str, object],
    ) -> TrainingTurnRecord:
        """Append a turn, update session rollup, and write usage in one commit."""
        session_record = self.get_session(session_id)
        if session_record is None:
            raise LookupError("History session not found.")
        turn = TrainingTurnRecord(**turn_kwargs)
        for field, value in rollup.items():
            setattr(session_record, field, value)
        event = UsageEventRecord(**event_kwargs)
        self._session.add_all([turn, event])
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._session.refresh(turn)
        return turn

    def get_turn(self, session_id: UUID, turn_index: int) -> TrainingTurnRecord | None:
        """Load one durable turn by its session-local turn index."""
        statement = select(TrainingTurnRecord).where(
            TrainingTurnRecord.session_id == session_id,
            TrainingTurnRecord.turn_index == turn_index,
        )
        return self._session.scalar(statement)

    def finish_session_with_report_and_events(
        self,
        *,
        session_id: UUID,
        finish: dict[str, object],
        report_text: str,
        report_payload: dict[str, object],
        finish_event_kwargs: dict[str, object],
        report_event_kwargs: dict[str, object],
        report_version: int = 1,
        judge_schema_version: str = JUDGE_SCHEMA_VERSION,
        judge_prompt_version: str = JUDGE_PROMPT_VERSION,
    ) -> TrainingReportRecord:
        """Mark a session finished, upsert report, and write finish/report events in one commit."""
        session_record = self.get_session(session_id)
        if session_record is None:
            raise LookupError("History session not found.")
        for field, value in finish.items():
            setattr(session_record, field, value)
        report = self.get_report(session_id)
        if report is None:
            report = TrainingReportRecord(
                session_id=session_id,
                report_text=report_text,
                report_payload=report_payload,
                report_version=report_version,
                judge_schema_version=judge_schema_version,
                judge_prompt_version=judge_prompt_version,
            )
            self._session.add(report)
        else:
            report.report_text = report_text
            report.report_payload = report_payload
            report.report_version = report_version
            report.judge_schema_version = judge_schema_version
            report.judge_prompt_version = judge_prompt_version
        self._session.add_all([UsageEventRecord(**finish_event_kwargs), UsageEventRecord(**report_event_kwargs)])
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._session.refresh(report)
        return report

    def list_sessions_for_user(
        self,
        *,
        user_id: UUID,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[tuple[TrainingSessionRecord, str]]:
        """List persistent sessions owned by one user with public email attached."""
        statement = self._base_list_statement().where(TrainingSessionRecord.user_id == user_id)
        return self._list_sessions(statement, filters=filters, limit=limit, offset=offset)

    def list_sessions_for_client_account(
        self,
        *,
        client_account_id: UUID,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[tuple[TrainingSessionRecord, str]]:
        """List persistent sessions belonging to one client account."""
        statement = self._base_list_statement().where(TrainingSessionRecord.client_account_id == client_account_id)
        return self._list_sessions(statement, filters=filters, limit=limit, offset=offset)

    def list_all_sessions(
        self,
        *,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[tuple[TrainingSessionRecord, str]]:
        """List persistent sessions without tenant filtering for internal admin use."""
        return self._list_sessions(self._base_list_statement(), filters=filters, limit=limit, offset=offset)

    def list_turns_for_session(self, session_id: UUID) -> list[TrainingTurnRecord]:
        """Load all durable turns for one session in conversation order."""
        statement = (
            select(TrainingTurnRecord)
            .where(TrainingTurnRecord.session_id == session_id)
            .order_by(TrainingTurnRecord.turn_index.asc())
        )
        return list(self._session.scalars(statement))

    def get_report(self, session_id: UUID) -> TrainingReportRecord | None:
        """Load the saved report for one session when it exists."""
        statement = select(TrainingReportRecord).where(TrainingReportRecord.session_id == session_id)
        return self._session.scalar(statement)

    def get_user_email(self, user_id: UUID) -> str | None:
        """Load the email needed for history summary DTOs."""
        return self._session.scalar(select(User.email).where(User.id == user_id))

    def training_config_names(self, training_config_ids: set[UUID]) -> dict[UUID, str]:
        """Return safe display names for training config ids used in history rows."""
        if not training_config_ids:
            return {}
        statement = select(ClientTrainingConfig.id, ClientTrainingConfig.name).where(ClientTrainingConfig.id.in_(training_config_ids))
        return {config_id: name for config_id, name in self._session.execute(statement)}

    def usage_summary(self, client_account_id: UUID) -> dict[str, object]:
        """Aggregate basic organization usage metrics from history and event tables."""
        session_filter = TrainingSessionRecord.client_account_id == client_account_id
        total_sessions = self._count(select(func.count()).select_from(TrainingSessionRecord).where(session_filter))
        finished_sessions = self._count(
            select(func.count()).select_from(TrainingSessionRecord).where(session_filter, TrainingSessionRecord.status == "finished")
        )
        active_sessions = self._count(
            select(func.count()).select_from(TrainingSessionRecord).where(session_filter, TrainingSessionRecord.status == "active")
        )
        unique_users = self._count(
            select(func.count(distinct(TrainingSessionRecord.user_id))).select_from(TrainingSessionRecord).where(session_filter)
        )
        total_turns = self._count(select(func.coalesce(func.sum(TrainingSessionRecord.turn_count), 0)).where(session_filter))
        avg_final_interest = self._session.scalar(
            select(func.avg(TrainingSessionRecord.final_interest_score)).where(
                session_filter,
                TrainingSessionRecord.final_interest_score.is_not(None),
            )
        )
        avg_turn_count = self._session.scalar(select(func.avg(TrainingSessionRecord.turn_count)).where(session_filter))
        events_count = self._count(
            select(func.count()).select_from(UsageEventRecord).where(UsageEventRecord.client_account_id == client_account_id)
        )
        return {
            "total_sessions": total_sessions,
            "finished_sessions": finished_sessions,
            "active_sessions": active_sessions,
            "unique_users": unique_users,
            "total_turns": total_turns,
            "avg_final_interest_score": float(avg_final_interest) if avg_final_interest is not None else None,
            "avg_turn_count": float(avg_turn_count) if avg_turn_count is not None else None,
            "sessions_by_status": self._group_counts(TrainingSessionRecord.status, session_filter),
            "sessions_by_scenario": self._group_counts(TrainingSessionRecord.scenario_id, session_filter),
            "sessions_by_training_config": self._group_counts(TrainingSessionRecord.training_config_id, session_filter),
            "usage_events_count": events_count,
        }

    def _base_list_statement(self) -> Select[tuple[TrainingSessionRecord, str]]:
        """Build the shared session listing query with user email joined in."""
        return select(TrainingSessionRecord, User.email).join(User, User.id == TrainingSessionRecord.user_id)

    def _list_sessions(
        self,
        statement: Select[tuple[TrainingSessionRecord, str]],
        *,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[tuple[TrainingSessionRecord, str]]:
        """Apply optional history filters, ordering, limit, and offset to a list query."""
        conditions = []
        if filters.status is not None:
            conditions.append(TrainingSessionRecord.status == filters.status)
        if filters.scenario_id is not None:
            conditions.append(TrainingSessionRecord.scenario_id == filters.scenario_id)
        if filters.training_config_id is not None:
            conditions.append(TrainingSessionRecord.training_config_id == filters.training_config_id)
        if filters.user_id is not None:
            conditions.append(TrainingSessionRecord.user_id == filters.user_id)
        if conditions:
            statement = statement.where(and_(*conditions))
        statement = statement.order_by(desc(TrainingSessionRecord.started_at)).limit(limit).offset(offset)
        return list(self._session.execute(statement))

    def _count(self, statement: Select[tuple[object]]) -> int:
        """Run a count-like scalar statement and normalize null to zero."""
        value = self._session.scalar(statement)
        return int(value or 0)

    def _group_counts(self, column: object, condition: object) -> dict[str, int]:
        """Return grouped counts as JSON-friendly string-keyed mapping."""
        statement = select(column, func.count()).where(condition).group_by(column)
        return {str(key): int(value) for key, value in self._session.execute(statement) if key is not None}
