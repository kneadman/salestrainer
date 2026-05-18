from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.identity.service import CurrentSession
from app.internal_admin.dependencies import get_internal_admin_service, require_internal_admin_session
from app.internal_admin.schemas import (
    AdminUserAnalyticsDetailDTO,
    AuditLogDTO,
    LLMProviderConfigCreateRequest,
    LLMProviderConfigDTO,
    LLMProviderConfigUpdateRequest,
    OrganizationCreateRequest,
    OrganizationDTO,
    OrganizationUpdateRequest,
    PasswordResetRequest,
    TrainingConfigCreateRequest,
    TrainingConfigDTO,
    TrainingConfigUpdateRequest,
    UserCreateRequest,
    UserDTO,
    UserTrainingConfigAssignmentDTO,
    UserUpdateRequest,
)
from app.identity.security import PasswordValidationError
from app.internal_admin.service import ConflictError, InternalAdminService, NotFoundError, ValidationError

router = APIRouter(prefix="/api/internal", tags=["internal-admin"])


def _handle_error(error: Exception) -> None:
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    if isinstance(error, (ValidationError, PasswordValidationError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    raise error


@router.get("/organizations", response_model=list[OrganizationDTO])
def list_organizations(
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[OrganizationDTO]:
    return service.list_organizations()


@router.post("/organizations", response_model=OrganizationDTO, status_code=status.HTTP_201_CREATED)
def create_organization(
    request: OrganizationCreateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> OrganizationDTO:
    try:
        return service.create_organization(actor_user_id=current_session.user.id, name=request.name, slug=request.slug)
    except Exception as error:
        _handle_error(error)


@router.get("/organizations/{organization_id}", response_model=OrganizationDTO)
def get_organization(
    organization_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> OrganizationDTO:
    try:
        return service.get_organization(organization_id)
    except Exception as error:
        _handle_error(error)


@router.patch("/organizations/{organization_id}", response_model=OrganizationDTO)
def update_organization(
    organization_id: UUID,
    request: OrganizationUpdateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> OrganizationDTO:
    try:
        return service.update_organization(
            actor_user_id=current_session.user.id,
            organization_id=organization_id,
            name=request.name,
            slug=request.slug,
        )
    except Exception as error:
        _handle_error(error)


@router.post("/organizations/{organization_id}/disable", response_model=OrganizationDTO)
def disable_organization(
    organization_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> OrganizationDTO:
    try:
        return service.set_organization_active(actor_user_id=current_session.user.id, organization_id=organization_id, is_active=False)
    except Exception as error:
        _handle_error(error)


@router.post("/organizations/{organization_id}/enable", response_model=OrganizationDTO)
def enable_organization(
    organization_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> OrganizationDTO:
    try:
        return service.set_organization_active(actor_user_id=current_session.user.id, organization_id=organization_id, is_active=True)
    except Exception as error:
        _handle_error(error)


@router.get("/organizations/{organization_id}/users", response_model=list[UserDTO])
def list_users(
    organization_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[UserDTO]:
    try:
        return service.list_users(organization_id)
    except Exception as error:
        _handle_error(error)


@router.get("/organizations/{organization_id}/users/{user_id}/analytics", response_model=AdminUserAnalyticsDetailDTO)
def get_organization_user_analytics(
    organization_id: UUID,
    user_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> AdminUserAnalyticsDetailDTO:
    try:
        return service.get_user_analytics_detail(organization_id=organization_id, user_id=user_id)
    except Exception as error:
        _handle_error(error)


@router.post("/organizations/{organization_id}/users", response_model=UserDTO, status_code=status.HTTP_201_CREATED)
def create_user(
    organization_id: UUID,
    request: UserCreateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> UserDTO:
    try:
        return service.create_user(
            actor_user_id=current_session.user.id,
            organization_id=organization_id,
            email=request.email,
            password=request.password,
            role=request.role,
        )
    except Exception as error:
        _handle_error(error)


@router.get("/users/{user_id}", response_model=UserDTO)
def get_user(
    user_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> UserDTO:
    try:
        return service.get_user(user_id)
    except Exception as error:
        _handle_error(error)


@router.patch("/users/{user_id}", response_model=UserDTO)
def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> UserDTO:
    try:
        updates = request.model_dump(exclude_unset=True)
        kwargs: dict[str, object] = {
            "actor_user_id": current_session.user.id,
            "user_id": user_id,
            "email": request.email,
            "role": request.role,
        }
        if "default_training_config_id" in updates:
            kwargs["default_training_config_id"] = request.default_training_config_id
        return service.update_user(**kwargs)  # type: ignore[arg-type]
    except Exception as error:
        _handle_error(error)


@router.post("/users/{user_id}/reset-password", response_model=UserDTO)
def reset_password(
    user_id: UUID,
    request: PasswordResetRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> UserDTO:
    try:
        return service.reset_user_password(actor_user_id=current_session.user.id, user_id=user_id, password=request.password)
    except Exception as error:
        _handle_error(error)


@router.post("/users/{user_id}/disable", response_model=UserDTO)
def disable_user(
    user_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> UserDTO:
    try:
        return service.set_user_active(actor_user_id=current_session.user.id, user_id=user_id, is_active=False)
    except Exception as error:
        _handle_error(error)


@router.post("/users/{user_id}/enable", response_model=UserDTO)
def enable_user(
    user_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> UserDTO:
    try:
        return service.set_user_active(actor_user_id=current_session.user.id, user_id=user_id, is_active=True)
    except Exception as error:
        _handle_error(error)


@router.get("/organizations/{organization_id}/training-configs", response_model=list[TrainingConfigDTO])
def list_training_configs(
    organization_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[TrainingConfigDTO]:
    try:
        return service.list_training_configs(organization_id)
    except Exception as error:
        _handle_error(error)


@router.post("/organizations/{organization_id}/training-configs", response_model=TrainingConfigDTO, status_code=status.HTTP_201_CREATED)
def create_training_config(
    organization_id: UUID,
    request: TrainingConfigCreateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> TrainingConfigDTO:
    try:
        return service.create_training_config(
            actor_user_id=current_session.user.id,
            organization_id=organization_id,
            name=request.name,
            persona_generation_context=request.persona_generation_context,
        )
    except Exception as error:
        _handle_error(error)


@router.get("/training-configs/{config_id}", response_model=TrainingConfigDTO)
def get_training_config(
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> TrainingConfigDTO:
    try:
        return service.get_training_config(config_id)
    except Exception as error:
        _handle_error(error)


@router.patch("/training-configs/{config_id}", response_model=TrainingConfigDTO)
def update_training_config(
    config_id: UUID,
    request: TrainingConfigUpdateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> TrainingConfigDTO:
    try:
        updates = request.model_dump(exclude_unset=True)
        return service.update_training_config(actor_user_id=current_session.user.id, config_id=config_id, **updates)
    except Exception as error:
        _handle_error(error)


@router.post("/training-configs/{config_id}/disable", response_model=TrainingConfigDTO)
def disable_training_config(
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> TrainingConfigDTO:
    try:
        return service.set_training_config_active(actor_user_id=current_session.user.id, config_id=config_id, is_active=False)
    except Exception as error:
        _handle_error(error)


@router.post("/training-configs/{config_id}/enable", response_model=TrainingConfigDTO)
def enable_training_config(
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> TrainingConfigDTO:
    try:
        return service.set_training_config_active(actor_user_id=current_session.user.id, config_id=config_id, is_active=True)
    except Exception as error:
        _handle_error(error)


@router.get("/users/{user_id}/training-configs", response_model=list[UserTrainingConfigAssignmentDTO])
def list_user_training_configs(
    user_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[UserTrainingConfigAssignmentDTO]:
    try:
        return service.list_user_training_configs(user_id)
    except Exception as error:
        _handle_error(error)


@router.post("/users/{user_id}/training-configs/{config_id}/assign", response_model=UserTrainingConfigAssignmentDTO)
def assign_training_config(
    user_id: UUID,
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> UserTrainingConfigAssignmentDTO:
    try:
        return service.assign_training_config(actor_user_id=current_session.user.id, user_id=user_id, config_id=config_id)
    except Exception as error:
        _handle_error(error)


@router.post("/users/{user_id}/training-configs/{config_id}/unassign")
def unassign_training_config(
    user_id: UUID,
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> dict[str, str]:
    try:
        return service.unassign_training_config(actor_user_id=current_session.user.id, user_id=user_id, config_id=config_id)
    except Exception as error:
        _handle_error(error)


@router.post("/users/{user_id}/training-configs/{config_id}/make-default", response_model=UserTrainingConfigAssignmentDTO)
def make_default_training_config(
    user_id: UUID,
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> UserTrainingConfigAssignmentDTO:
    try:
        return service.make_default_training_config(actor_user_id=current_session.user.id, user_id=user_id, config_id=config_id)
    except Exception as error:
        _handle_error(error)


@router.get("/organizations/{organization_id}/llm-provider-configs", response_model=list[LLMProviderConfigDTO])
def list_llm_provider_configs(
    organization_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[LLMProviderConfigDTO]:
    try:
        return service.list_llm_provider_configs(organization_id)
    except Exception as error:
        _handle_error(error)


@router.post("/organizations/{organization_id}/llm-provider-configs", response_model=LLMProviderConfigDTO, status_code=status.HTTP_201_CREATED)
def create_llm_provider_config(
    organization_id: UUID,
    request: LLMProviderConfigCreateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> LLMProviderConfigDTO:
    try:
        return service.create_llm_provider_config(
            actor_user_id=current_session.user.id,
            organization_id=organization_id,
            name=request.name,
            provider=request.provider,
            persona_api_key=request.persona_api_key or request.api_key,
            persona_folder_id=request.persona_folder_id or request.folder_id,
            persona_agent_id=request.persona_agent_id or request.agent_id,
            dialogue_api_key=request.dialogue_api_key,
            dialogue_folder_id=request.dialogue_folder_id,
            dialogue_agent_id=request.dialogue_agent_id,
            base_url=request.base_url,
            model_or_agent_label=request.model_or_agent_label,
        )
    except Exception as error:
        _handle_error(error)


@router.get("/llm-provider-configs/{config_id}", response_model=LLMProviderConfigDTO)
def get_llm_provider_config(
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> LLMProviderConfigDTO:
    try:
        return service.get_llm_provider_config(config_id)
    except Exception as error:
        _handle_error(error)


@router.patch("/llm-provider-configs/{config_id}", response_model=LLMProviderConfigDTO)
def update_llm_provider_config(
    config_id: UUID,
    request: LLMProviderConfigUpdateRequest,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> LLMProviderConfigDTO:
    try:
        return service.update_llm_provider_config(
            actor_user_id=current_session.user.id,
            config_id=config_id,
            **request.model_dump(exclude_unset=True),
        )
    except Exception as error:
        _handle_error(error)


@router.post("/llm-provider-configs/{config_id}/disable", response_model=LLMProviderConfigDTO)
def disable_llm_provider_config(
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> LLMProviderConfigDTO:
    try:
        return service.set_llm_provider_config_active(actor_user_id=current_session.user.id, config_id=config_id, is_active=False)
    except Exception as error:
        _handle_error(error)


@router.post("/llm-provider-configs/{config_id}/enable", response_model=LLMProviderConfigDTO)
def enable_llm_provider_config(
    config_id: UUID,
    service: InternalAdminService = Depends(get_internal_admin_service),
    current_session: CurrentSession = Depends(require_internal_admin_session),
) -> LLMProviderConfigDTO:
    try:
        return service.set_llm_provider_config_active(actor_user_id=current_session.user.id, config_id=config_id, is_active=True)
    except Exception as error:
        _handle_error(error)


@router.get("/audit-log", response_model=list[AuditLogDTO])
def list_audit_log(
    organization_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: InternalAdminService = Depends(get_internal_admin_service),
    _: CurrentSession = Depends(require_internal_admin_session),
) -> list[AuditLogDTO]:
    return service.list_audit_log(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
