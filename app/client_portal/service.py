from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.history.models import TrainingSessionRecord
from app.history.projections import session_summary_dto
from app.history.repository import HistoryRepository, SessionListFilters
from app.history.schemas import HistorySessionSummaryDTO, UsageSummaryDTO
from app.identity.models import User
from app.identity.roles import UserRole, normalize_role
from app.client_portal.schemas import ClientUserAnalyticsDTO, TeamUsageSummaryDTO, TeamUserDTO, TeamUserDetailDTO


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

    def list_team_users(self, *, requester: User) -> list[TeamUserDTO]:
        """Return same-organization users for a client lead."""
        self._require_client_lead(requester)
        users = self._list_users_for_account(requester.client_account_id)
        return [self._team_user_dto(user) for user in users]

    def get_team_usage_summary(self, *, requester: User) -> TeamUsageSummaryDTO:
        """Return organization usage summary for a client lead."""
        self._require_client_lead(requester)
        summary = UsageSummaryDTO.model_validate(self._history.usage_summary(requester.client_account_id))
        return TeamUsageSummaryDTO(
            **summary.model_dump(),
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
    ) -> list[HistorySessionSummaryDTO]:
        """Return one same-organization user's history for a client lead."""
        self._require_client_lead(requester)
        user = self._require_same_account_user(user_id=user_id, client_account_id=requester.client_account_id)
        rows = self._history.list_sessions_for_user(user_id=user.id, filters=filters, limit=limit, offset=offset)
        return [session_summary_dto(record, user_email=email) for record, email in rows]

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
        return ClientUserAnalyticsDTO(
            user_id=user.id,
            user_email=user.email,
            total_sessions=total_sessions,
            finished_sessions=finished_sessions,
            active_sessions=active_sessions,
            completion_rate=(finished_sessions / total_sessions) if total_sessions else 0.0,
            avg_final_interest_score=float(avg_interest) if avg_interest is not None else None,
            avg_turn_count=float(avg_turns) if avg_turns is not None else None,
            last_activity_at=last_activity,
            sessions_by_status=self._group_counts(TrainingSessionRecord.status, user_filter),
            sessions_by_scenario=self._group_counts(TrainingSessionRecord.scenario_id, user_filter),
        )

    def _scalar_int(self, statement) -> int:
        """Execute a scalar aggregate and normalize null to zero."""
        value = self._session.scalar(statement)
        return int(value or 0)

    def _group_counts(self, column: object, condition: object) -> dict[str, int]:
        """Return grouped user analytics counts as JSON-friendly mapping."""
        statement = select(column, func.count()).where(condition).group_by(column).order_by(desc(func.count()))
        return {str(key): int(value) for key, value in self._session.execute(statement) if key is not None}
