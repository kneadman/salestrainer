from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.access.models import LandingLead
from app.api.client_ip import client_ip_from_request
from app.api.dependencies import get_app_settings, get_persona_generation_service, get_report_service, get_session_service, get_turn_service
from app.api.errors import conflict, not_found
from app.access.service import AccessService
from app.api.rate_limit import LeadRateLimitExceeded
from app.api.schemas import (
    ErrorResponse,
    FinishSessionResponse,
    LandingLeadRequest,
    LandingSubmitResponse,
    PersonaOptionDTO,
    ScenarioOptionDTO,
    SessionCreateRequest,
    SessionDetailResponse,
    SessionReportResponse,
    SessionStateResponse,
    TurnRequest,
    TurnResponse,
)
from app.application.projections import build_session_public_dto, build_turn_public_dto
from app.application.persona_generation_service import PersonaGenerationService
from app.application.report_service import ReportService
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService
from app.domain.errors import (
    SalesTrainerError,
    LLMProviderConfigurationError,
    MessageIdempotencyPersistenceError,
    PersonaGenerationError,
    SessionHistorySyncPendingError,
    SessionNotActiveError,
    SessionNotFoundError,
    StateVersionConflictError,
    UnknownPersonaError,
    UnknownScenarioError,
)
from app.domain.personas import list_personas
from app.domain.scenarios import list_scenarios, normalize_scenario_id
from app.identity.dependencies import (
    get_access_service,
    require_current_user,
    require_internal_admin,
)
from app.identity.service import CurrentSession
from app.identity.roles import is_internal_admin
from app.history.dependencies import get_history_service
from app.history.events import UsageEventType
from app.history.service import HistoryService
from app.infrastructure.db import get_db_session
from app.infrastructure.config import Settings

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


def raise_api_error(error: SalesTrainerError) -> None:
    if isinstance(error, (SessionNotFoundError, UnknownScenarioError, UnknownPersonaError)):
        raise not_found(str(error)) from error
    if isinstance(
        error,
        (
            MessageIdempotencyPersistenceError,
            SessionNotActiveError,
            StateVersionConflictError,
            SessionHistorySyncPendingError,
        ),
    ):
        raise conflict(str(error)) from error
    if isinstance(error, LLMProviderConfigurationError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, PersonaGenerationError):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    raise error


def _reconcile_pending_history_sync(
    *,
    session_id: str,
    session_service: TrainingSessionService,
    access_service: AccessService,
    history_service: HistoryService,
    current_session: CurrentSession,
) -> None:
    """Replay the latest runtime turn into durable history before more session work."""
    session = session_service.get_session(session_id)
    if session is None or session.history_sync_status == "ok":
        return
    ownership = access_service.get_session_ownership(session_id)
    try:
        history_service.reconcile_turn_processed(
            session=session,
            user_id=current_session.user.id,
            client_account_id=ownership.client_account_id,
            training_config_id=ownership.training_config_id,
        )
        session_service.clear_history_sync_pending(session_id)
    except Exception:
        logger.critical("history_turn_reconcile_failed session_id=%s", session_id, exc_info=True)
        raise conflict(
            "The previous turn was processed, but session history is still being reconciled. "
            "Please retry this action instead of resending the last message."
        ) from None


def _record_runtime_expiry(session_id: str, history_service: HistoryService) -> None:
    """Best-effort close of durable history after the runtime session key expired."""
    try:
        history_service.record_runtime_session_expired(UUID(session_id))
    except (ValueError, LookupError):
        return
    except Exception:
        logger.warning("runtime_session_expiry_record_failed session_id=%s", session_id, exc_info=True)


def _touch_runtime_session(
    *,
    session_id: str,
    session_service: TrainingSessionService,
    history_service: HistoryService,
) -> None:
    """Refresh both runtime TTL and durable last activity for one active session."""
    session_service.touch_session(session_id)
    try:
        durable_session_id = UUID(session_id)
    except ValueError as error:
        raise not_found("Session not found.") from error
    history_service.touch_runtime_session_activity(durable_session_id)


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/leads", response_model=LandingSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
def submit_landing_lead(
    request: LandingLeadRequest,
    http_request: Request,
    db_session: Session = Depends(get_db_session),
) -> LandingSubmitResponse:
    try:
        http_request.app.state.lead_rate_limiter.hit(
            ip_address=client_ip_from_request(http_request),
            email=str(request.email) if request.email else None,
            phone=request.phone if request.phone else None,
        )
    except LeadRateLimitExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        ) from error
    if request.consent_personal_data is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="consent_personal_data must be true.",
        )
    lead = LandingLead(
        name=request.name,
        email=str(request.email),
        phone=request.phone,
        company=request.company,
        role=request.role,
        sales_team_size=request.sales_team_size,
        consent_personal_data=request.consent_personal_data,
        consent_marketing=request.consent_marketing,
        comment=request.comment,
        query_params=dict(request.query_params),
        page=request.page,
        form_id=request.form_id,
        is_spam=bool(request.website and request.website.strip()),
    )
    db_session.add(lead)
    db_session.commit()
    return LandingSubmitResponse(status="accepted")


@router.get("/scenarios", response_model=list[ScenarioOptionDTO], responses=ERROR_RESPONSES)
def get_scenarios(
    settings: Settings = Depends(get_app_settings),
    access_service: AccessService = Depends(get_access_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> list[ScenarioOptionDTO]:
    scenarios = list_scenarios()
    if not is_internal_admin(current_session.user.role):
        try:
            access_service.get_default_training_config_for_user(current_session.user.id)
        except LookupError as error:
            raise not_found(str(error)) from error
        default_scenario_id = normalize_scenario_id(settings.default_training_scenario_id)
        scenarios = [scenario for scenario in scenarios if scenario.id == default_scenario_id]

    return [
        ScenarioOptionDTO(
            scenario_id=scenario.id,
            name=scenario.name,
            training_format=scenario.training_format,
            default_starting_interest=scenario.default_starting_interest,
            default_stage=scenario.default_stage,
            manager_goal=scenario.manager_goal,
            success_condition=scenario.success_condition,
            failure_condition=scenario.failure_condition,
            evaluation_focus=scenario.evaluation_focus,
            client_behavior_hint=scenario.client_behavior_hint,
        )
        for scenario in scenarios
    ]


@router.get("/personas", response_model=list[PersonaOptionDTO], responses={**ERROR_RESPONSES, 403: {"model": ErrorResponse}})
def get_personas(
    current_session: CurrentSession = Depends(require_internal_admin),
) -> list[PersonaOptionDTO]:
    return [
        PersonaOptionDTO(
            persona_id=persona.id,
            display_name=persona.display_name,
            role=persona.role,
            authority_level=persona.authority_level,
            behavior_model=persona.behavior_model,
        )
        for persona in list_personas()
    ]


@router.post(
    "/sessions",
    response_model=SessionStateResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
)
def create_session(
    request: SessionCreateRequest,
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    history_service: HistoryService = Depends(get_history_service),
    persona_generation_service: PersonaGenerationService = Depends(get_persona_generation_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionStateResponse:
    try:
        user_role = current_session.user.role
        if not is_internal_admin(user_role) and request.persona_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="persona_id is not allowed for client sessions.",
            )

        training_config = None
        if request.training_config_id is not None:
            try:
                config_id = UUID(request.training_config_id)
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid training_config_id format.",
                ) from error
            training_config = access_service.get_training_config_by_id(config_id)
            if training_config is None:
                raise not_found("Training config not found.")
            if training_config.client_account_id != current_session.user.client_account_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Training config does not belong to your organization.",
                )
            if not training_config.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Training config is disabled.",
                )

        if training_config is None:
            try:
                training_config = access_service.get_default_training_config_for_user(current_session.user.id)
            except LookupError as error:
                if is_internal_admin(user_role) and request.persona_id is not None:
                    raise not_found(
                        "Default training config is required for internal admin debug sessions."
                    ) from error
                raise not_found(
                    "Сценарий по умолчанию не назначен. Обратитесь к администратору."
                ) from error

        history_service.expire_inactive_sessions(
            client_account_id=training_config.client_account_id,
            user_id=current_session.user.id,
        )
        session = None
        if is_internal_admin(user_role) and request.persona_id is not None:
            session = session_service.start_session(
                scenario_id=request.scenario_id,
                persona_id=request.persona_id,
            )
        else:
            persona = persona_generation_service.generate_for_training_config(
                training_config=training_config,
                scenario_id=request.scenario_id,
            )
            session = session_service.start_session(
                scenario_id=request.scenario_id,
                training_config=training_config,
                persona_override=persona,
            )
        access_service.bind_session_to_user(
            session.session_id,
            current_session.user.id,
            training_config.client_account_id,
            training_config.id,
        )
        try:
            history_service.record_session_started(
                session=session,
                client_account_id=training_config.client_account_id,
                user_id=current_session.user.id,
                training_config_id=training_config.id,
            )
        except Exception:
            logger.critical("history_session_start_failed session_id=%s", session.session_id, exc_info=True)
            access_service.delete_session_ownership(session.session_id)
            session_service.delete_session(str(session.session_id))
            raise
    except SalesTrainerError as error:
        raise_api_error(error)
    except LookupError as error:
        raise not_found(str(error)) from error
    return SessionStateResponse(session=build_session_public_dto(session))


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, responses=ERROR_RESPONSES)
def get_session(
    session_id: str,
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    history_service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionDetailResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        ownership = access_service.get_session_ownership(session_id)
    except LookupError as error:
        raise not_found(str(error)) from error
    session = session_service.get_session(session_id)
    if session is None:
        _record_runtime_expiry(session_id, history_service)
        raise not_found("Session not found.")
    _touch_runtime_session(
        session_id=session_id,
        session_service=session_service,
        history_service=history_service,
    )
    history_service.record_usage_event(
        event_type=UsageEventType.SESSION_VIEWED.value,
        client_account_id=ownership.client_account_id,
        user_id=current_session.user.id,
        training_config_id=ownership.training_config_id,
        session_id=session.session_id,
    )
    return SessionDetailResponse(
        session=build_session_public_dto(session),
        turns=build_turn_public_dto(session),
    )


@router.post("/sessions/{session_id}/resume", response_model=SessionStateResponse, responses=ERROR_RESPONSES)
def resume_session(
    session_id: str,
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    history_service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionStateResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        _reconcile_pending_history_sync(
            session_id=session_id,
            session_service=session_service,
            access_service=access_service,
            history_service=history_service,
            current_session=current_session,
        )
        ownership = access_service.get_session_ownership(session_id)
        session = session_service.resume_session(session_id)
        _touch_runtime_session(
            session_id=session_id,
            session_service=session_service,
            history_service=history_service,
        )
        history_service.record_usage_event(
            event_type=UsageEventType.SESSION_RESUMED.value,
            client_account_id=ownership.client_account_id,
            user_id=current_session.user.id,
            training_config_id=ownership.training_config_id,
            session_id=session.session_id,
        )
    except SalesTrainerError as error:
        raise_api_error(error)
    except LookupError as error:
        raise not_found(str(error)) from error
    return SessionStateResponse(session=build_session_public_dto(session))


@router.post("/sessions/{session_id}/messages", response_model=TurnResponse, responses=ERROR_RESPONSES)
def post_manager_message(
    session_id: str,
    request: TurnRequest,
    turn_service: TurnService = Depends(get_turn_service),
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    history_service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> TurnResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        _reconcile_pending_history_sync(
            session_id=session_id,
            session_service=session_service,
            access_service=access_service,
            history_service=history_service,
            current_session=current_session,
        )
        if request.idempotency_key is not None:
            existing_submission = session_service.get_message_submission(session_id, request.idempotency_key)
            if existing_submission is not None:
                if existing_submission.manager_message != request.manager_message:
                    raise conflict(
                        "This idempotency key was already used for a different manager_message."
                    )
                _touch_runtime_session(
                    session_id=session_id,
                    session_service=session_service,
                    history_service=history_service,
                )
                return TurnResponse.model_validate(existing_submission.response_payload)
        ownership = access_service.get_session_ownership(session_id)
        turn_result = turn_service.process_message(
            session_id,
            request.manager_message,
            idempotency_key=request.idempotency_key,
        )
    except SalesTrainerError as error:
        if isinstance(error, SessionNotFoundError):
            _record_runtime_expiry(session_id, history_service)
        raise_api_error(error)
    except LookupError as error:
        raise not_found(str(error)) from error
    session = session_service.get_session(session_id)
    if session is None:
        _record_runtime_expiry(session_id, history_service)
        raise not_found("Session not found after turn.")
    response = (
        TurnResponse.model_validate(turn_result.response_payload)
        if turn_result.response_payload is not None
        else TurnResponse(
            session=build_session_public_dto(session),
            turns=build_turn_public_dto(session),
            client_answer=turn_result.client_answer,
            interest_before=turn_result.interest_before,
            interest_delta=turn_result.interest_delta,
            interest_after=turn_result.interest_after,
            stage_before=turn_result.stage_before,
            stage_after=turn_result.stage_after,
            turn_index=turn_result.turn_index,
        )
    )
    try:
        history_service.record_turn_processed(
            session=session,
            turn_result=turn_result,
            user_id=current_session.user.id,
            client_account_id=ownership.client_account_id,
            training_config_id=ownership.training_config_id,
        )
    except Exception:
        logger.critical("history_turn_write_failed session_id=%s", session.session_id, exc_info=True)
        session_service.mark_history_sync_pending(
            session_id,
            reason="turn_processed_history_write_failed",
        )
        raise conflict(
            "The turn was processed, but session history is still being reconciled. "
            "Please retry this action instead of resending the last message."
        ) from None
    return response


@router.post("/sessions/{session_id}/finish", response_model=FinishSessionResponse, responses=ERROR_RESPONSES)
def finish_session(
    session_id: str,
    report_service: ReportService = Depends(get_report_service),
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    history_service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> FinishSessionResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        _reconcile_pending_history_sync(
            session_id=session_id,
            session_service=session_service,
            access_service=access_service,
            history_service=history_service,
            current_session=current_session,
        )
        ownership = access_service.get_session_ownership(session_id)
        report_text = report_service.finish_session(session_id)
    except SalesTrainerError as error:
        if isinstance(error, SessionNotFoundError):
            _record_runtime_expiry(session_id, history_service)
        raise_api_error(error)
    except LookupError as error:
        raise not_found(str(error)) from error
    session = session_service.get_session(session_id)
    if session is None:
        _record_runtime_expiry(session_id, history_service)
        raise not_found("Session not found after finish.")
    report_payload = report_service.generate_report_payload_safely(session_id)
    history_service.record_session_finished_with_report(
        session=session,
        report_text=report_text,
        report_payload=report_payload,
        user_id=current_session.user.id,
        client_account_id=ownership.client_account_id,
        training_config_id=ownership.training_config_id,
    )
    return FinishSessionResponse(
        session=build_session_public_dto(session),
        report=report_text,
        report_payload=report_payload,
    )


@router.get("/sessions/{session_id}/report", response_model=SessionReportResponse, responses=ERROR_RESPONSES)
def get_report(
    session_id: str,
    report_service: ReportService = Depends(get_report_service),
    session_service: TrainingSessionService = Depends(get_session_service),
    access_service: AccessService = Depends(get_access_service),
    history_service: HistoryService = Depends(get_history_service),
    current_session: CurrentSession = Depends(require_current_user),
) -> SessionReportResponse:
    try:
        access_service.require_session_access(session_id, current_session.user.id)
        ownership = access_service.get_session_ownership(session_id)
    except LookupError as error:
        raise not_found(str(error)) from error
    session = session_service.get_session(session_id)
    if session is None:
        _record_runtime_expiry(session_id, history_service)
        raise not_found("Session not found.")
    if session.status != "finished":
        raise conflict("Session is not finished yet.")
    report_text = report_service.generate_report(session_id)
    saved_report_payload = history_service.get_saved_report_payload(session.session_id)
    if saved_report_payload is None:
        report_payload = report_service.generate_report_payload_safely(session_id)
    else:
        report_payload = saved_report_payload
    session = session_service.get_session(session_id)
    if session is None:
        _record_runtime_expiry(session_id, history_service)
        raise not_found("Session not found after report.")
    if saved_report_payload is None:
        history_service.record_report_generated(
            session=session,
            report_text=report_text,
            report_payload=report_payload,
            user_id=current_session.user.id,
            client_account_id=ownership.client_account_id,
            training_config_id=ownership.training_config_id,
        )
    return SessionReportResponse(
        session=build_session_public_dto(session),
        report=report_text,
        report_payload=report_payload,
    )
