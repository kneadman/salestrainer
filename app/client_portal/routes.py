from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.client_portal.schemas import ClientUserAnalyticsDTO, TeamUsageSummaryDTO, TeamUserDTO, TeamUserDetailDTO
from app.client_portal.service import ClientPortalAccessError, ClientPortalNotFoundError, ClientPortalService
from app.history.repository import SessionListFilters
from app.history.schemas import ClientHistorySessionSummaryDTO
from app.identity.dependencies import require_current_user
from app.identity.service import CurrentSession
from app.infrastructure.db import get_db_session

router = APIRouter(prefix="/api", tags=["client-portal"])


def get_client_portal_service(db_session: Session = Depends(get_db_session)) -> ClientPortalService:
    """Build the client portal service for request handlers."""
    return ClientPortalService(db_session)


def _handle_client_portal_error(error: Exception) -> None:
    """Translate client portal service errors to public HTTP responses."""
    if isinstance(error, ClientPortalAccessError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, ClientPortalNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    raise error


@router.get("/client/analytics/me", response_model=ClientUserAnalyticsDTO)
def get_my_analytics(
    service: ClientPortalService = Depends(get_client_portal_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> ClientUserAnalyticsDTO:
    """Return personal analytics for the current client user."""
    return service.get_my_analytics(user_id=current_session.user.id)


@router.get("/team/users", response_model=list[TeamUserDTO])
def list_team_users(
    service: ClientPortalService = Depends(get_client_portal_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> list[TeamUserDTO]:
    """Return same-organization users for client leads."""
    try:
        return service.list_team_users(requester=current_session.user)
    except Exception as error:
        _handle_client_portal_error(error)


@router.get("/team/usage-summary", response_model=TeamUsageSummaryDTO)
def get_team_usage_summary(
    service: ClientPortalService = Depends(get_client_portal_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> TeamUsageSummaryDTO:
    """Return organization usage analytics for client leads."""
    try:
        return service.get_team_usage_summary(requester=current_session.user)
    except Exception as error:
        _handle_client_portal_error(error)


@router.get("/team/users/{user_id}/history/sessions", response_model=list[ClientHistorySessionSummaryDTO])
def list_team_user_history(
    user_id: UUID,
    status: str | None = None,
    scenario_id: str | None = None,
    training_config_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: ClientPortalService = Depends(get_client_portal_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> list[ClientHistorySessionSummaryDTO]:
    """Return one same-organization user's history for client leads."""
    try:
        return service.list_team_user_history(
            requester=current_session.user,
            user_id=user_id,
            filters=SessionListFilters(
                status=status,
                scenario_id=scenario_id,
                training_config_id=training_config_id,
            ),
            limit=limit,
            offset=offset,
        )
    except Exception as error:
        _handle_client_portal_error(error)


@router.get("/team/users/{user_id}/analytics", response_model=TeamUserDetailDTO)
def get_team_user_analytics(
    user_id: UUID,
    service: ClientPortalService = Depends(get_client_portal_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> TeamUserDetailDTO:
    """Return one same-organization user's detail analytics for client leads."""
    try:
        return service.get_team_user_detail(requester=current_session.user, user_id=user_id)
    except Exception as error:
        _handle_client_portal_error(error)
