from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.errors import not_found
from app.history.dependencies import get_history_service
from app.history.repository import SessionListFilters
from app.history.schemas import ClientHistorySessionDetailDTO, ClientHistorySessionSummaryDTO, HistoryReportDTO
from app.history.service import HistoryService
from app.identity.dependencies import require_current_user
from app.identity.service import CurrentSession

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/sessions", response_model=list[ClientHistorySessionSummaryDTO])
def list_history_sessions(
    status: str | None = None,
    scenario_id: str | None = None,
    training_config_id: UUID | None = None,
    user_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> list[ClientHistorySessionSummaryDTO]:
    """Return history visible to the current user according to their client role."""
    history = service.get_user_history(
        requester_user_id=current_session.user.id,
        requester_client_account_id=current_session.user.client_account_id,
        requester_role=current_session.user.role,
        filters=SessionListFilters(
            status=status,
            scenario_id=scenario_id,
            training_config_id=training_config_id,
            user_id=user_id,
        ),
        limit=limit,
        offset=offset,
    )
    return [ClientHistorySessionSummaryDTO.model_validate(item.model_dump()) for item in history]


@router.get("/sessions/{session_id}", response_model=ClientHistorySessionDetailDTO)
def get_history_session(
    session_id: UUID,
    service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> ClientHistorySessionDetailDTO:
    """Return public-safe session history detail for an allowed requester."""
    try:
        detail = service.get_session_history_detail(
            session_id=session_id,
            requester_user_id=current_session.user.id,
            requester_client_account_id=current_session.user.client_account_id,
            requester_role=current_session.user.role,
        )
        return ClientHistorySessionDetailDTO(
            session=ClientHistorySessionSummaryDTO.model_validate(detail.session.model_dump()),
            public_brief=detail.public_brief,
            turns=detail.turns,
            report=detail.report,
        )
    except LookupError as error:
        raise not_found(str(error)) from error


@router.get("/sessions/{session_id}/report", response_model=HistoryReportDTO)
def get_history_report(
    session_id: UUID,
    service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> HistoryReportDTO:
    """Return the saved persistent report for an allowed requester."""
    try:
        return service.get_saved_report(
            session_id=session_id,
            requester_user_id=current_session.user.id,
            requester_client_account_id=current_session.user.client_account_id,
            requester_role=current_session.user.role,
        )
    except LookupError as error:
        raise not_found(str(error)) from error
