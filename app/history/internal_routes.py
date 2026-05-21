from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.history.dependencies import get_history_service
from app.history.repository import SessionListFilters
from app.history.schemas import HistorySessionSummaryDTO, TokenUsageSnapshotDTO, TokenUsageSummaryDTO, UsageSummaryDTO
from app.history.service import HistoryService
from app.identity.service import CurrentSession
from app.internal_admin.dependencies import require_internal_admin_session

router = APIRouter(prefix="/api/internal", tags=["internal-history"])


@router.get("/organizations/{organization_id}/history/sessions", response_model=list[HistorySessionSummaryDTO])
def list_organization_history_sessions(
    organization_id: UUID,
    status: str | None = None,
    scenario_id: str | None = None,
    training_config_id: UUID | None = None,
    user_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: HistoryService = Depends(get_history_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[HistorySessionSummaryDTO]:
    """Return organization session history for internal admin analytics."""
    return service.list_organization_history(
        client_account_id=organization_id,
        filters=SessionListFilters(
            status=status,
            scenario_id=scenario_id,
            training_config_id=training_config_id,
            user_id=user_id,
        ),
        limit=limit,
        offset=offset,
    )


@router.get("/organizations/{organization_id}/usage-summary", response_model=UsageSummaryDTO)
def get_organization_usage_summary(
    organization_id: UUID,
    service: HistoryService = Depends(get_history_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> UsageSummaryDTO:
    """Return basic aggregated usage metrics for an organization."""
    return service.get_client_usage_summary(client_account_id=organization_id)


@router.get("/organizations/{organization_id}/token-usage", response_model=TokenUsageSummaryDTO)
def get_organization_token_usage(
    organization_id: UUID,
    service: HistoryService = Depends(get_history_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> TokenUsageSummaryDTO:
    """Return token usage aggregates for an organization (admin only)."""
    return service.get_token_usage_summary(client_account_id=organization_id)


@router.get("/organizations/{organization_id}/token-usage-snapshots", response_model=list[TokenUsageSnapshotDTO])
def get_organization_token_usage_snapshots(
    organization_id: UUID,
    from_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    to_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    service: HistoryService = Depends(get_history_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[TokenUsageSnapshotDTO]:
    """Return daily token usage snapshots for an organization within a date range."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(tz=UTC)
    default_from = now - timedelta(days=30)
    parsed_from = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=UTC) if from_date else default_from
    parsed_to = datetime.strptime(to_date, "%Y-%m-%d").replace(tzinfo=UTC, hour=23, minute=59, second=59) if to_date else now
    return service.list_token_usage_snapshots(
        client_account_id=organization_id,
        from_date=parsed_from,
        to_date=parsed_to,
    )


@router.get("/users/{user_id}/history/sessions", response_model=list[HistorySessionSummaryDTO])
def list_user_history_sessions(
    user_id: UUID,
    status: str | None = None,
    scenario_id: str | None = None,
    training_config_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: HistoryService = Depends(get_history_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[HistorySessionSummaryDTO]:
    """Return a specific user's session history for internal admin review."""
    return service.list_user_history(
        user_id=user_id,
        filters=SessionListFilters(
            status=status,
            scenario_id=scenario_id,
            training_config_id=training_config_id,
        ),
        limit=limit,
        offset=offset,
    )
