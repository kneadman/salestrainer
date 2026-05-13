from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.domain.judgement_models import JudgeSessionOutput
from app.history.models import TrainingSessionRecord
from app.history.models import TrainingReportRecord
from app.history.projections import client_session_summary_dto
from app.history.repository import HistoryRepository, SessionListFilters
from app.history.schemas import ClientHistorySessionSummaryDTO, UsageSummaryDTO
from app.identity.models import User
from app.identity.roles import UserRole, normalize_role
from app.client_portal.schemas import (
    ClientAnalyticsTrendsDTO,
    ClientUserAnalyticsDTO,
    MetricTrendDTO,
    TeamUsageSummaryDTO,
    TeamUserDTO,
    TeamUserDetailDTO,
)


class ClientPortalAccessError(PermissionError):
    pass


class ClientPortalNotFoundError(LookupError):
    pass


class ClientPortalService:
    def __init__(self, session: Session) -> None:
        """Keep the request-scoped DB session for client portal queries."""
        self._session = session
        self._history = HistoryRepository(session)

    def get_my_analytics(self, *, user_id: UUID) -> ClientUserAnalyticsDTO:
        """Return analytics for the current authenticated user only."""
        user = self._get_user(user_id)
        return self._user_analytics(user)

    def get_user_analytics_for_admin(self, *, user_id: UUID) -> ClientUserAnalyticsDTO:
        """Return analytics for one user so internal admin services can reuse one analytics source."""
        user = self._get_user(user_id)
        return self._user_analytics(user)

    def list_team_users(self, *, requester: User) -> list[TeamUserDTO]:
        """Return same-organization users for a client lead."""
        self._require_client_lead(requester)
        users = self._list_users_for_account(requester.client_account_id)
        # TODO: This performs per-user analytics and judgement aggregation; replace with bulk aggregation for larger teams.
        return [self._team_user_dto(user) for user in users]

    def get_team_usage_summary(self, *, requester: User) -> TeamUsageSummaryDTO:
        """Return organization usage summary for a client lead."""
        self._require_client_lead(requester)
        summary = UsageSummaryDTO.model_validate(self._history.usage_summary(requester.client_account_id))
        judgement_analytics = self._judgement_analytics_for_account(requester.client_account_id)
        return TeamUsageSummaryDTO(
            **summary.model_dump(),
            avg_judgement_score=judgement_analytics["avg_judgement_score"],
            sessions_with_judgement=judgement_analytics["sessions_with_judgement"],
            users=self.list_team_users(requester=requester),
        )

    def list_team_user_history(
        self,
        *,
        requester: User,
        user_id: UUID,
        filters: SessionListFilters,
        limit: int,
        offset: int,
    ) -> list[ClientHistorySessionSummaryDTO]:
        """Return one same-organization user's history for a client lead."""
        self._require_client_lead(requester)
        user = self._require_same_account_user(user_id=user_id, client_account_id=requester.client_account_id)
        rows = self._history.list_sessions_for_user(user_id=user.id, filters=filters, limit=limit, offset=offset)
        return [client_session_summary_dto(record, user_email=email) for record, email in rows]

    def get_team_user_detail(self, *, requester: User, user_id: UUID) -> TeamUserDetailDTO:
        """Return one same-organization user's analytics and latest history."""
        self._require_client_lead(requester)
        user = self._require_same_account_user(user_id=user_id, client_account_id=requester.client_account_id)
        history = self.list_team_user_history(
            requester=requester,
            user_id=user.id,
            filters=SessionListFilters(),
            limit=25,
            offset=0,
        )
        return TeamUserDetailDTO(
            user=self._team_user_dto(user),
            analytics=self._user_analytics(user),
            history=history,
        )

    def _require_client_lead(self, user: User) -> None:
        """Reject non-leads from team endpoints."""
        if normalize_role(user.role) != UserRole.CLIENT_LEAD:
            raise ClientPortalAccessError("Client lead role is required.")

    def _get_user(self, user_id: UUID) -> User:
        """Load a user or raise a controlled not-found error."""
        user = self._session.get(User, user_id)
        if user is None:
            raise ClientPortalNotFoundError("User not found.")
        return user

    def _require_same_account_user(self, *, user_id: UUID, client_account_id: UUID) -> User:
        """Load a user and enforce same-organization access."""
        user = self._get_user(user_id)
        if user.client_account_id != client_account_id:
            raise ClientPortalNotFoundError("User not found.")
        return user

    def _list_users_for_account(self, client_account_id: UUID) -> list[User]:
        """List client account users in stable email order."""
        statement = select(User).where(User.client_account_id == client_account_id).order_by(User.email.asc())
        return list(self._session.scalars(statement))

    def _team_user_dto(self, user: User) -> TeamUserDTO:
        """Project a user and their aggregate training metrics without secrets."""
        analytics = self._user_analytics(user)
        return TeamUserDTO(
            id=user.id,
            email=user.email,
            role=normalize_role(user.role).value,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            total_sessions=analytics.total_sessions,
            finished_sessions=analytics.finished_sessions,
            avg_final_interest_score=analytics.avg_final_interest_score,
            last_activity_at=analytics.last_activity_at,
        )

    def _user_analytics(self, user: User) -> ClientUserAnalyticsDTO:
        """Aggregate personal analytics from persistent training history."""
        user_filter = TrainingSessionRecord.user_id == user.id
        total_sessions = self._scalar_int(select(func.count()).select_from(TrainingSessionRecord).where(user_filter))
        finished_sessions = self._scalar_int(
            select(func.count()).select_from(TrainingSessionRecord).where(user_filter, TrainingSessionRecord.status == "finished")
        )
        active_sessions = self._scalar_int(
            select(func.count()).select_from(TrainingSessionRecord).where(user_filter, TrainingSessionRecord.status == "active")
        )
        avg_interest = self._session.scalar(
            select(func.avg(TrainingSessionRecord.final_interest_score)).where(
                user_filter,
                TrainingSessionRecord.final_interest_score.is_not(None),
            )
        )
        avg_turns = self._session.scalar(select(func.avg(TrainingSessionRecord.turn_count)).where(user_filter))
        last_activity = self._session.scalar(select(func.max(TrainingSessionRecord.last_activity_at)).where(user_filter))
        judgement_analytics = self._judgement_analytics_for_user(user.id)
        trends = self._user_analytics_trends(user.id)
        return ClientUserAnalyticsDTO(
            user_id=user.id,
            user_email=user.email,
            total_sessions=total_sessions,
            finished_sessions=finished_sessions,
            active_sessions=active_sessions,
            completion_rate=(finished_sessions / total_sessions) if total_sessions else 0.0,
            avg_final_interest_score=float(avg_interest) if avg_interest is not None else None,
            avg_turn_count=float(avg_turns) if avg_turns is not None else None,
            avg_judgement_score=judgement_analytics["avg_judgement_score"],
            sessions_with_judgement=judgement_analytics["sessions_with_judgement"],
            weakest_skill_id=judgement_analytics["weakest_skill_id"],
            weakest_skill_title=judgement_analytics["weakest_skill_title"],
            weakest_skill_avg_score=judgement_analytics["weakest_skill_avg_score"],
            last_activity_at=last_activity,
            sessions_by_status=self._group_counts(TrainingSessionRecord.status, user_filter),
            sessions_by_scenario=self._group_counts(TrainingSessionRecord.scenario_id, user_filter),
            trends_7d=trends,
        )

    def _user_analytics_trends(self, user_id: UUID) -> ClientAnalyticsTrendsDTO:
        """Build current-vs-previous 7-day trends from persistent session history."""
        now = datetime.now(UTC)
        current_start = now - timedelta(days=7)
        previous_start = now - timedelta(days=14)
        current_session_metrics = self._session_window_metrics(user_id=user_id, start_at=current_start)
        previous_session_metrics = self._session_window_metrics(
            user_id=user_id,
            start_at=previous_start,
            end_at=current_start,
        )
        current_judgement_metrics = self._judgement_window_metrics(user_id=user_id, start_at=current_start)
        previous_judgement_metrics = self._judgement_window_metrics(
            user_id=user_id,
            start_at=previous_start,
            end_at=current_start,
        )
        return ClientAnalyticsTrendsDTO(
            total_sessions=self._trend_metric(
                current_session_metrics["total_sessions"],
                previous_session_metrics["total_sessions"],
                value_type="int",
            ),
            finished_sessions=self._trend_metric(
                current_session_metrics["finished_sessions"],
                previous_session_metrics["finished_sessions"],
                value_type="int",
            ),
            completion_rate=self._trend_metric(
                current_session_metrics["completion_rate"],
                previous_session_metrics["completion_rate"],
                value_type="float",
            ),
            avg_final_interest_score=self._trend_metric(
                current_session_metrics["avg_final_interest_score"],
                previous_session_metrics["avg_final_interest_score"],
                value_type="float",
            ),
            avg_turn_count=self._trend_metric(
                current_session_metrics["avg_turn_count"],
                previous_session_metrics["avg_turn_count"],
                value_type="float",
            ),
            avg_judgement_score=self._trend_metric(
                current_judgement_metrics["avg_judgement_score"],
                previous_judgement_metrics["avg_judgement_score"],
                value_type="float",
            ),
            sessions_with_judgement=self._trend_metric(
                current_judgement_metrics["sessions_with_judgement"],
                previous_judgement_metrics["sessions_with_judgement"],
                value_type="int",
            ),
        )

    def _judgement_analytics_for_user(self, user_id: UUID) -> dict[str, float | int | str | None]:
        """Aggregate judgement payload metrics for one user from saved persistent reports."""
        statement = (
            select(TrainingReportRecord.report_payload)
            .join(TrainingSessionRecord, TrainingReportRecord.session_id == TrainingSessionRecord.id)
            .where(
                TrainingSessionRecord.user_id == user_id,
                TrainingReportRecord.report_payload.is_not(None),
            )
        )
        return self._aggregate_judgement_payloads(self._session.scalars(statement))

    def _judgement_analytics_for_account(self, client_account_id: UUID) -> dict[str, float | int | str | None]:
        """Aggregate judgement payload metrics for one client account from saved persistent reports."""
        statement = (
            select(TrainingReportRecord.report_payload)
            .join(TrainingSessionRecord, TrainingReportRecord.session_id == TrainingSessionRecord.id)
            .where(
                TrainingSessionRecord.client_account_id == client_account_id,
                TrainingReportRecord.report_payload.is_not(None),
            )
        )
        return self._aggregate_judgement_payloads(self._session.scalars(statement))

    def _aggregate_judgement_payloads(self, payloads) -> dict[str, float | int | str | None]:
        """Compute lightweight aggregates from valid saved JudgeSessionOutput payloads only."""
        parsed_payloads = [payload for payload in (self._parse_judge_payload(item) for item in payloads) if payload is not None]
        if not parsed_payloads:
            return {
                "avg_judgement_score": None,
                "sessions_with_judgement": 0,
                "weakest_skill_id": None,
                "weakest_skill_title": None,
                "weakest_skill_avg_score": None,
            }
        skill_totals: dict[str, dict[str, float | int | str]] = {}
        for payload in parsed_payloads:
            for skill in payload.skill_scores:
                aggregate = skill_totals.setdefault(
                    skill.id,
                    {"title": skill.title, "score_sum": 0.0, "count": 0},
                )
                aggregate["score_sum"] = float(aggregate["score_sum"]) + float(skill.score)
                aggregate["count"] = int(aggregate["count"]) + 1
        weakest_skill_id = None
        weakest_skill_title = None
        weakest_skill_avg_score = None
        if skill_totals:
            weakest_skill_id, weakest_skill_data = min(
                skill_totals.items(),
                key=lambda item: (float(item[1]["score_sum"]) / int(item[1]["count"]), item[0]),
            )
            weakest_skill_title = str(weakest_skill_data["title"])
            weakest_skill_avg_score = float(weakest_skill_data["score_sum"]) / int(weakest_skill_data["count"])
        return {
            "avg_judgement_score": sum(payload.overall_score for payload in parsed_payloads) / len(parsed_payloads),
            "sessions_with_judgement": len(parsed_payloads),
            "weakest_skill_id": weakest_skill_id,
            "weakest_skill_title": weakest_skill_title,
            "weakest_skill_avg_score": weakest_skill_avg_score,
        }

    def _parse_judge_payload(self, payload: object) -> JudgeSessionOutput | None:
        """Validate one saved report payload and ignore unknown or incompatible shapes."""
        if not isinstance(payload, dict):
            return None
        try:
            return JudgeSessionOutput.model_validate(payload)
        except ValidationError:
            return None

    def _session_window_metrics(
        self,
        *,
        user_id: UUID,
        start_at: datetime,
        end_at: datetime | None = None,
    ) -> dict[str, float | int | None]:
        """Aggregate one time window from session rows only, without report joins."""
        statement = select(TrainingSessionRecord).where(
            TrainingSessionRecord.user_id == user_id,
            TrainingSessionRecord.started_at >= start_at,
        )
        if end_at is not None:
            statement = statement.where(TrainingSessionRecord.started_at < end_at)
        total_sessions = 0
        finished_sessions = 0
        turn_counts: list[int] = []
        interest_scores: list[int] = []
        for session_record in self._session.scalars(statement):
            total_sessions += 1
            if session_record.status == "finished":
                finished_sessions += 1
            turn_counts.append(int(session_record.turn_count))
            if session_record.final_interest_score is not None:
                interest_scores.append(int(session_record.final_interest_score))
        return {
            "total_sessions": total_sessions,
            "finished_sessions": finished_sessions,
            "completion_rate": (finished_sessions / total_sessions) if total_sessions else None,
            "avg_final_interest_score": self._average_or_none(interest_scores),
            "avg_turn_count": self._average_or_none(turn_counts),
        }

    def _judgement_window_metrics(
        self,
        *,
        user_id: UUID,
        start_at: datetime,
        end_at: datetime | None = None,
    ) -> dict[str, float | int | None]:
        """Aggregate one time window from report payloads only, deduplicated by session id."""
        statement = (
            select(TrainingReportRecord.session_id, TrainingReportRecord.report_payload)
            .join(TrainingSessionRecord, TrainingReportRecord.session_id == TrainingSessionRecord.id)
            .where(
                TrainingSessionRecord.user_id == user_id,
                TrainingSessionRecord.started_at >= start_at,
                TrainingReportRecord.report_payload.is_not(None),
            )
        )
        if end_at is not None:
            statement = statement.where(TrainingSessionRecord.started_at < end_at)
        seen_session_ids: set[UUID] = set()
        judgement_scores: list[float] = []
        for session_id, report_payload in self._session.execute(statement):
            if session_id in seen_session_ids:
                continue
            seen_session_ids.add(session_id)
            parsed_payload = self._parse_judge_payload(report_payload)
            if parsed_payload is not None:
                judgement_scores.append(float(parsed_payload.overall_score))
        return {
            "avg_judgement_score": self._average_or_none(judgement_scores),
            "sessions_with_judgement": len(judgement_scores),
        }

    def _average_or_none(self, values: list[int] | list[float]) -> float | None:
        """Return a numeric average only when the window contains source data."""
        if not values:
            return None
        return float(sum(values) / len(values))

    def _trend_metric(
        self,
        current_value: float | int | None,
        previous_value: float | int | None,
        *,
        value_type: str,
    ) -> MetricTrendDTO:
        """Translate two window values into delta, percent, and direction."""
        if current_value is None and previous_value is None:
            return MetricTrendDTO(
                current_7d=None,
                previous_7d=None,
                delta=None,
                delta_percent=None,
                direction="none",
            )
        current_numeric = float(current_value) if current_value is not None else 0.0
        previous_numeric = float(previous_value) if previous_value is not None else 0.0
        delta_numeric = current_numeric - previous_numeric
        if value_type == "int":
            current_result = None if current_value is None else int(current_value)
            previous_result = None if previous_value is None else int(previous_value)
            delta_result = int(round(delta_numeric))
        else:
            current_result = None if current_value is None else float(current_value)
            previous_result = None if previous_value is None else float(previous_value)
            delta_result = float(delta_numeric)
        if delta_numeric > 0:
            direction = "up"
        elif delta_numeric < 0:
            direction = "down"
        elif current_value is None and previous_value is None:
            direction = "none"
        else:
            direction = "flat"
        return MetricTrendDTO(
            current_7d=current_result,
            previous_7d=previous_result,
            delta=delta_result,
            delta_percent=None if previous_numeric == 0 else (delta_numeric / previous_numeric) * 100,
            direction=direction,
        )

    def _scalar_int(self, statement) -> int:
        """Execute a scalar aggregate and normalize null to zero."""
        value = self._session.scalar(statement)
        return int(value or 0)

    def _group_counts(self, column: object, condition: object) -> dict[str, int]:
        """Return grouped user analytics counts as JSON-friendly mapping."""
        statement = select(column, func.count()).where(condition).group_by(column).order_by(desc(func.count()))
        return {str(key): int(value) for key, value in self._session.execute(statement) if key is not None}
