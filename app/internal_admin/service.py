from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.access.models import AuditLog, ClientTrainingConfig, LLMProviderConfig, UserTrainingConfig
from app.client_portal.service import ClientPortalService
from app.history.projections import session_summary_dto
from app.history.repository import HistoryRepository, SessionListFilters
from app.identity.models import ClientAccount, User
from app.identity.roles import CLIENT_ROLES, normalize_role
from app.identity.security import hash_password, PasswordValidationError, validate_permanent_password
from app.infrastructure.config import Settings
from app.infrastructure.secrets import encrypt_secret, preview_encrypted_secret
from app.internal_admin.schemas import (
    AdminUserAnalyticsDetailDTO,
    AuditLogDTO,
    ClientAccountBriefDTO,
    LLMProviderConfigDTO,
    OrganizationDTO,
    TrainingConfigDTO,
    UserDTO,
    UserTrainingConfigAssignmentDTO,
)


class InternalAdminError(Exception):
    pass


class NotFoundError(InternalAdminError):
    pass


class ConflictError(InternalAdminError):
    pass


class ValidationError(InternalAdminError):
    pass


class InternalAdminService:
    def __init__(self, session: Session, *, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def list_organizations(self) -> list[OrganizationDTO]:
        accounts = list(self._session.scalars(select(ClientAccount).order_by(ClientAccount.created_at.desc())))
        return [self._organization_dto(account) for account in accounts]

    def create_organization(self, *, actor_user_id: UUID, name: str, slug: str) -> OrganizationDTO:
        account = ClientAccount(name=name, slug=slug, is_active=True)
        self._session.add(account)
        self._flush_or_conflict("Organization slug already exists.")
        self._audit(
            actor_user_id=actor_user_id,
            action="organization_created",
            entity_type="organization",
            entity_id=account.id,
            payload=self._organization_payload(account, {"name": account.name, "slug": account.slug}),
        )
        self._commit_or_conflict("Organization slug already exists.")
        self._session.refresh(account)
        return self._organization_dto(account)

    def get_organization(self, organization_id: UUID) -> OrganizationDTO:
        return self._organization_dto(self._get_account(organization_id))

    def update_organization(
        self,
        *,
        actor_user_id: UUID,
        organization_id: UUID,
        name: str | None = None,
        slug: str | None = None,
    ) -> OrganizationDTO:
        account = self._get_account(organization_id)
        if name is not None:
            account.name = name
        if slug is not None:
            account.slug = slug
        self._audit(
            actor_user_id=actor_user_id,
            action="organization_updated",
            entity_type="organization",
            entity_id=account.id,
            payload=self._organization_payload(account, {"name": account.name, "slug": account.slug}),
        )
        self._commit_or_conflict("Organization slug already exists.")
        self._session.refresh(account)
        return self._organization_dto(account)

    def set_organization_active(self, *, actor_user_id: UUID, organization_id: UUID, is_active: bool) -> OrganizationDTO:
        account = self._get_account(organization_id)
        account.is_active = is_active
        self._audit(
            actor_user_id=actor_user_id,
            action="organization_enabled" if is_active else "organization_disabled",
            entity_type="organization",
            entity_id=account.id,
            payload=self._organization_payload(account, {"slug": account.slug, "is_active": account.is_active}),
        )
        self._session.commit()
        self._session.refresh(account)
        return self._organization_dto(account)

    def list_users(self, organization_id: UUID) -> list[UserDTO]:
        self._get_account(organization_id)
        statement = (
            select(User)
            .options(joinedload(User.client_account))
            .where(User.client_account_id == organization_id)
            .order_by(User.created_at.desc())
        )
        return [self._user_dto(user) for user in self._session.scalars(statement)]

    def get_user_analytics_detail(self, *, organization_id: UUID, user_id: UUID) -> AdminUserAnalyticsDetailDTO:
        """Return one organization user's profile, analytics, and recent public-safe history for internal admin."""
        self._get_account(organization_id)
        user = self._get_user(user_id)
        if user.client_account_id != organization_id:
            raise NotFoundError("User not found.")
        analytics = ClientPortalService(
            self._session,
            inactive_ttl_seconds=self._settings.session_ttl_seconds,
        ).get_user_analytics_for_admin(user_id=user.id)
        history_rows = HistoryRepository(self._session).list_sessions_for_user(
            user_id=user.id,
            filters=SessionListFilters(),
            limit=25,
            offset=0,
        )
        return AdminUserAnalyticsDetailDTO(
            user=self._user_dto(user),
            analytics=analytics,
            history=[session_summary_dto(record, user_email=email) for record, email in history_rows],
        )

    def create_user(
        self,
        *,
        actor_user_id: UUID,
        organization_id: UUID,
        email: str,
        password: str,
        role: object,
    ) -> UserDTO:
        self._get_account(organization_id)
        normalized_role = normalize_role(str(role))
        if normalized_role not in CLIENT_ROLES:
            raise ValidationError("Only client_lead or client_manager can be created for an organization.")
        try:
            validate_permanent_password(password)
        except PasswordValidationError as error:
            raise ValidationError(str(error)) from error
        user = User(
            client_account_id=organization_id,
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=normalized_role.value,
            must_change_password=True,
            is_active=True,
        )
        self._session.add(user)
        self._flush_or_conflict("User email already exists.")
        self._audit(
            actor_user_id=actor_user_id,
            action="user_created",
            entity_type="user",
            entity_id=user.id,
            payload=self._client_payload(user.client_account_id, {"email": user.email, "role": user.role}),
        )
        self._commit_or_conflict("User email already exists.")
        return self.get_user(user.id)

    def get_user(self, user_id: UUID) -> UserDTO:
        return self._user_dto(self._get_user(user_id))

    def update_user(
        self,
        *,
        actor_user_id: UUID,
        user_id: UUID,
        email: str | None = None,
        role: object | None = None,
    ) -> UserDTO:
        user = self._get_user(user_id)
        if email is not None:
            user.email = email.strip().lower()
        if role is not None:
            normalized_role = normalize_role(str(role))
            if normalized_role not in CLIENT_ROLES:
                raise ValidationError("Only client_lead or client_manager can be assigned through this endpoint.")
            user.role = normalized_role.value
        self._audit(
            actor_user_id=actor_user_id,
            action="user_updated",
            entity_type="user",
            entity_id=user.id,
            payload=self._client_payload(user.client_account_id, {"email": user.email, "role": user.role}),
        )
        self._commit_or_conflict("User email already exists.")
        return self.get_user(user.id)

    def reset_user_password(self, *, actor_user_id: UUID, user_id: UUID, password: str) -> UserDTO:
        user = self._get_user(user_id)
        try:
            validate_permanent_password(password)
        except PasswordValidationError as error:
            raise ValidationError(str(error)) from error
        user.password_hash = hash_password(password)
        user.must_change_password = True
        self._audit(
            actor_user_id=actor_user_id,
            action="password_reset",
            entity_type="user",
            entity_id=user.id,
            payload=self._client_payload(user.client_account_id, {"email": user.email}),
        )
        self._session.commit()
        return self.get_user(user.id)

    def set_user_active(self, *, actor_user_id: UUID, user_id: UUID, is_active: bool) -> UserDTO:
        user = self._get_user(user_id)
        user.is_active = is_active
        self._audit(
            actor_user_id=actor_user_id,
            action="user_enabled" if is_active else "user_disabled",
            entity_type="user",
            entity_id=user.id,
            payload=self._client_payload(user.client_account_id, {"email": user.email, "is_active": user.is_active}),
        )
        self._session.commit()
        return self.get_user(user.id)

    def list_training_configs(self, organization_id: UUID) -> list[TrainingConfigDTO]:
        self._get_account(organization_id)
        statement = (
            select(ClientTrainingConfig)
            .where(ClientTrainingConfig.client_account_id == organization_id)
            .order_by(ClientTrainingConfig.created_at.desc())
        )
        return [self._training_config_dto(config) for config in self._session.scalars(statement)]

    def create_training_config(
        self,
        *,
        actor_user_id: UUID,
        organization_id: UUID,
        name: str,
        persona_generation_context: str = "",
    ) -> TrainingConfigDTO:
        self._get_account(organization_id)
        config = ClientTrainingConfig(
            client_account_id=organization_id,
            name=name,
            persona_generation_context=persona_generation_context,
            is_active=True,
        )
        self._session.add(config)
        self._session.flush()
        self._audit(
            actor_user_id=actor_user_id,
            action="training_config_created",
            entity_type="client_training_config",
            entity_id=config.id,
            payload=self._client_payload(config.client_account_id, {"name": config.name}),
        )
        self._session.commit()
        self._session.refresh(config)
        return self._training_config_dto(config)

    def get_training_config(self, config_id: UUID) -> TrainingConfigDTO:
        return self._training_config_dto(self._get_training_config(config_id))

    def update_training_config(self, *, actor_user_id: UUID, config_id: UUID, **updates: object) -> TrainingConfigDTO:
        config = self._get_training_config(config_id)
        for field in ("name", "persona_generation_context"):
            if field in updates:
                setattr(config, field, updates[field])
        self._audit(
            actor_user_id=actor_user_id,
            action="training_config_updated",
            entity_type="client_training_config",
            entity_id=config.id,
            payload=self._client_payload(config.client_account_id, {"name": config.name}),
        )
        self._session.commit()
        self._session.refresh(config)
        return self._training_config_dto(config)

    def set_training_config_active(self, *, actor_user_id: UUID, config_id: UUID, is_active: bool) -> TrainingConfigDTO:
        config = self._get_training_config(config_id)
        config.is_active = is_active
        self._audit(
            actor_user_id=actor_user_id,
            action="training_config_enabled" if is_active else "training_config_disabled",
            entity_type="client_training_config",
            entity_id=config.id,
            payload=self._client_payload(config.client_account_id, {"name": config.name, "is_active": config.is_active}),
        )
        self._session.commit()
        self._session.refresh(config)
        return self._training_config_dto(config)

    def list_user_training_configs(self, user_id: UUID) -> list[UserTrainingConfigAssignmentDTO]:
        self._get_user(user_id)
        statement = (
            select(UserTrainingConfig, ClientTrainingConfig)
            .join(ClientTrainingConfig, ClientTrainingConfig.id == UserTrainingConfig.training_config_id)
            .where(UserTrainingConfig.user_id == user_id)
        )
        return [
            UserTrainingConfigAssignmentDTO(
                user_id=assignment.user_id,
                training_config_id=assignment.training_config_id,
                is_default=assignment.is_default,
                training_config=self._training_config_dto(config),
            )
            for assignment, config in self._session.execute(statement)
        ]

    def assign_training_config(self, *, actor_user_id: UUID, user_id: UUID, config_id: UUID) -> UserTrainingConfigAssignmentDTO:
        user = self._get_user(user_id)
        config = self._get_training_config(config_id)
        if config.client_account_id != user.client_account_id:
            raise ValidationError("Cannot assign a training config from another organization.")
        assignment = self._get_or_create_assignment(user_id=user.id, config_id=config.id)
        self._audit(
            actor_user_id=actor_user_id,
            action="training_config_assigned",
            entity_type="client_training_config",
            entity_id=config.id,
            payload=self._client_payload(user.client_account_id, {"user_id": str(user.id)}),
        )
        self._session.commit()
        self._session.refresh(assignment)
        return UserTrainingConfigAssignmentDTO(
            user_id=user.id,
            training_config_id=config.id,
            is_default=assignment.is_default,
            training_config=self._training_config_dto(config),
        )

    def unassign_training_config(self, *, actor_user_id: UUID, user_id: UUID, config_id: UUID) -> dict[str, str]:
        user = self._get_user(user_id)
        config = self._get_training_config(config_id)
        assignment = self._session.get(UserTrainingConfig, {"user_id": user.id, "training_config_id": config.id})
        if assignment is not None:
            self._session.delete(assignment)
        self._audit(
            actor_user_id=actor_user_id,
            action="training_config_unassigned",
            entity_type="client_training_config",
            entity_id=config.id,
            payload=self._client_payload(user.client_account_id, {"user_id": str(user.id)}),
        )
        self._session.commit()
        return {"status": "ok"}

    def make_default_training_config(
        self,
        *,
        actor_user_id: UUID,
        user_id: UUID,
        config_id: UUID,
    ) -> UserTrainingConfigAssignmentDTO:
        user = self._get_user(user_id)
        config = self._get_training_config(config_id)
        if config.client_account_id != user.client_account_id:
            raise ValidationError("Cannot assign a training config from another organization.")
        if not config.is_active:
            raise ValidationError("Disabled training config cannot be made default.")
        self._session.execute(
            update(UserTrainingConfig).where(UserTrainingConfig.user_id == user.id).values(is_default=False)
        )
        assignment = self._get_or_create_assignment(user_id=user.id, config_id=config.id)
        assignment.is_default = True
        self._audit(
            actor_user_id=actor_user_id,
            action="default_training_config_changed",
            entity_type="client_training_config",
            entity_id=config.id,
            payload=self._client_payload(user.client_account_id, {"user_id": str(user.id)}),
        )
        self._session.commit()
        self._session.refresh(assignment)
        return UserTrainingConfigAssignmentDTO(
            user_id=user.id,
            training_config_id=config.id,
            is_default=assignment.is_default,
            training_config=self._training_config_dto(config),
        )

    def list_llm_provider_configs(self, organization_id: UUID) -> list[LLMProviderConfigDTO]:
        self._get_account(organization_id)
        statement = (
            select(LLMProviderConfig)
            .where(LLMProviderConfig.client_account_id == organization_id)
            .order_by(LLMProviderConfig.created_at.desc())
        )
        return [self._llm_provider_config_dto(config) for config in self._session.scalars(statement)]

    def create_llm_provider_config(
        self,
        *,
        actor_user_id: UUID,
        organization_id: UUID,
        name: str,
        provider: str,
        persona_api_key: str | None,
        persona_folder_id: str | None,
        persona_agent_id: str | None,
        dialogue_api_key: str | None,
        dialogue_folder_id: str | None,
        dialogue_agent_id: str | None,
        base_url: str | None,
        model_or_agent_label: str | None,
    ) -> LLMProviderConfigDTO:
        self._get_account(organization_id)
        config = LLMProviderConfig(
            client_account_id=organization_id,
            name=name,
            provider=str(provider),
            encrypted_api_key=encrypt_secret(persona_api_key, self._settings) if persona_api_key else None,
            folder_id=persona_folder_id,
            agent_id=persona_agent_id,
            base_url=base_url,
            model_or_agent_label=model_or_agent_label,
            persona_api_key_encrypted=encrypt_secret(persona_api_key, self._settings) if persona_api_key else None,
            persona_folder_id=persona_folder_id,
            persona_agent_id=persona_agent_id,
            dialogue_api_key_encrypted=encrypt_secret(dialogue_api_key, self._settings) if dialogue_api_key else None,
            dialogue_folder_id=dialogue_folder_id,
            dialogue_agent_id=dialogue_agent_id,
            is_active=True,
        )
        self._session.add(config)
        self._session.flush()
        self._audit(
            actor_user_id=actor_user_id,
            action="llm_provider_config_created",
            entity_type="llm_provider_config",
            entity_id=config.id,
            payload=self._client_payload(config.client_account_id, {"name": config.name, "provider": config.provider}),
        )
        self._session.commit()
        self._session.refresh(config)
        return self._llm_provider_config_dto(config)

    def get_llm_provider_config(self, config_id: UUID) -> LLMProviderConfigDTO:
        return self._llm_provider_config_dto(self._get_llm_provider_config(config_id))

    def update_llm_provider_config(self, *, actor_user_id: UUID, config_id: UUID, **updates: object) -> LLMProviderConfigDTO:
        config = self._get_llm_provider_config(config_id)
        persona_api_key = updates.pop("persona_api_key", None)
        dialogue_api_key = updates.pop("dialogue_api_key", None)
        legacy_api_key = updates.pop("api_key", None)
        if persona_api_key is None:
            persona_api_key = legacy_api_key
        if persona_api_key is not None:
            config.persona_api_key_encrypted = encrypt_secret(str(persona_api_key), self._settings)
            config.encrypted_api_key = config.persona_api_key_encrypted
        if dialogue_api_key is not None:
            config.dialogue_api_key_encrypted = encrypt_secret(str(dialogue_api_key), self._settings)
        field_map = {
            "folder_id": "folder_id",
            "agent_id": "agent_id",
            "base_url": "base_url",
            "model_or_agent_label": "model_or_agent_label",
            "persona_folder_id": "persona_folder_id",
            "persona_agent_id": "persona_agent_id",
            "dialogue_folder_id": "dialogue_folder_id",
            "dialogue_agent_id": "dialogue_agent_id",
        }
        if "folder_id" in updates and "persona_folder_id" not in updates:
            updates["persona_folder_id"] = updates["folder_id"]
        if "agent_id" in updates and "persona_agent_id" not in updates:
            updates["persona_agent_id"] = updates["agent_id"]
        for field in ("name", "provider", *field_map):
            if field in updates:
                setattr(config, field, str(updates[field]) if field == "provider" else updates[field])
        self._audit(
            actor_user_id=actor_user_id,
            action="llm_provider_config_updated",
            entity_type="llm_provider_config",
            entity_id=config.id,
            payload=self._client_payload(config.client_account_id, {"name": config.name, "provider": config.provider}),
        )
        self._session.commit()
        self._session.refresh(config)
        return self._llm_provider_config_dto(config)

    def set_llm_provider_config_active(self, *, actor_user_id: UUID, config_id: UUID, is_active: bool) -> LLMProviderConfigDTO:
        config = self._get_llm_provider_config(config_id)
        config.is_active = is_active
        self._audit(
            actor_user_id=actor_user_id,
            action="llm_provider_config_enabled" if is_active else "llm_provider_config_disabled",
            entity_type="llm_provider_config",
            entity_id=config.id,
            payload=self._client_payload(
                config.client_account_id,
                {"name": config.name, "provider": config.provider, "is_active": config.is_active},
            ),
        )
        self._session.commit()
        self._session.refresh(config)
        return self._llm_provider_config_dto(config)

    def list_audit_log(
        self,
        *,
        organization_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLogDTO]:
        statement = select(AuditLog)
        if organization_id is not None:
            organization_key = str(organization_id)
            statement = statement.where(
                or_(
                    and_(AuditLog.entity_type == "organization", AuditLog.entity_id == organization_id),
                    AuditLog.payload["client_account_id"].as_string() == organization_key,
                    AuditLog.payload["organization_id"].as_string() == organization_key,
                )
            )
        if actor_user_id is not None:
            statement = statement.where(AuditLog.actor_user_id == actor_user_id)
        if action is not None:
            statement = statement.where(AuditLog.action == action)
        if entity_type is not None:
            statement = statement.where(AuditLog.entity_type == entity_type)
        statement = statement.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
        return [self._audit_log_dto(record) for record in self._session.scalars(statement)]

    def _get_account(self, organization_id: UUID) -> ClientAccount:
        account = self._session.get(ClientAccount, organization_id)
        if account is None:
            raise NotFoundError("Organization not found.")
        return account

    def _get_user(self, user_id: UUID) -> User:
        statement = select(User).options(joinedload(User.client_account)).where(User.id == user_id)
        user = self._session.scalar(statement)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    def _get_training_config(self, config_id: UUID) -> ClientTrainingConfig:
        config = self._session.get(ClientTrainingConfig, config_id)
        if config is None:
            raise NotFoundError("Training config not found.")
        return config

    def _get_llm_provider_config(self, config_id: UUID) -> LLMProviderConfig:
        config = self._session.get(LLMProviderConfig, config_id)
        if config is None:
            raise NotFoundError("LLM provider config not found.")
        return config

    def _get_or_create_assignment(self, *, user_id: UUID, config_id: UUID) -> UserTrainingConfig:
        assignment = self._session.get(UserTrainingConfig, {"user_id": user_id, "training_config_id": config_id})
        if assignment is None:
            assignment = UserTrainingConfig(user_id=user_id, training_config_id=config_id, is_default=False)
            self._session.add(assignment)
            self._session.flush()
        return assignment

    def _flush_or_conflict(self, message: str) -> None:
        try:
            self._session.flush()
        except IntegrityError as error:
            self._session.rollback()
            raise ConflictError(message) from error

    def _commit_or_conflict(self, message: str) -> None:
        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise ConflictError(message) from error

    def _audit(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        payload: dict[str, object],
    ) -> None:
        self._session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
            )
        )

    def _organization_payload(self, account: ClientAccount, payload: dict[str, object]) -> dict[str, object]:
        return self._client_payload(account.id, payload)

    def _client_payload(self, client_account_id: UUID, payload: dict[str, object]) -> dict[str, object]:
        return {
            "client_account_id": str(client_account_id),
            "organization_id": str(client_account_id),
            **payload,
        }

    def _organization_dto(self, account: ClientAccount) -> OrganizationDTO:
        users_count = self._session.scalar(
            select(func.count()).select_from(User).where(User.client_account_id == account.id)
        )
        active_users_count = self._session.scalar(
            select(func.count()).select_from(User).where(User.client_account_id == account.id, User.is_active.is_(True))
        )
        configs_count = self._session.scalar(
            select(func.count()).select_from(ClientTrainingConfig).where(ClientTrainingConfig.client_account_id == account.id)
        )
        return OrganizationDTO(
            id=account.id,
            name=account.name,
            slug=account.slug,
            is_active=account.is_active,
            created_at=account.created_at,
            updated_at=account.updated_at,
            users_count=int(users_count or 0),
            active_users_count=int(active_users_count or 0),
            training_configs_count=int(configs_count or 0),
        )

    def _user_dto(self, user: User) -> UserDTO:
        account = user.client_account
        return UserDTO(
            id=user.id,
            client_account_id=user.client_account_id,
            email=user.email,
            role=normalize_role(user.role).value,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            created_at=user.created_at,
            updated_at=user.updated_at,
            client_account=ClientAccountBriefDTO(id=account.id, name=account.name, slug=account.slug) if account else None,
        )

    def _training_config_dto(self, config: ClientTrainingConfig) -> TrainingConfigDTO:
        return TrainingConfigDTO(
            id=config.id,
            client_account_id=config.client_account_id,
            name=config.name,
            is_active=config.is_active,
            persona_generation_context=config.persona_generation_context,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    def _llm_provider_config_dto(self, config: LLMProviderConfig) -> LLMProviderConfigDTO:
        legacy_preview = preview_encrypted_secret(config.encrypted_api_key, self._settings)
        persona_preview = preview_encrypted_secret(config.persona_api_key_encrypted or config.encrypted_api_key, self._settings)
        dialogue_preview = preview_encrypted_secret(config.dialogue_api_key_encrypted, self._settings)
        return LLMProviderConfigDTO(
            id=config.id,
            client_account_id=config.client_account_id,
            name=config.name,
            provider=config.provider,
            is_active=config.is_active,
            has_api_key=config.encrypted_api_key is not None,
            api_key_preview=legacy_preview,
            has_persona_api_key=(config.persona_api_key_encrypted or config.encrypted_api_key) is not None,
            persona_api_key_preview=persona_preview,
            persona_folder_id=config.persona_folder_id or config.folder_id,
            persona_agent_id=config.persona_agent_id or config.agent_id,
            has_dialogue_api_key=config.dialogue_api_key_encrypted is not None,
            dialogue_api_key_preview=dialogue_preview,
            dialogue_folder_id=config.dialogue_folder_id,
            dialogue_agent_id=config.dialogue_agent_id,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )

    def _audit_log_dto(self, record: AuditLog) -> AuditLogDTO:
        return AuditLogDTO(
            id=record.id,
            actor_user_id=record.actor_user_id,
            action=record.action,
            entity_type=record.entity_type,
            entity_id=record.entity_id,
            payload=record.payload,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            created_at=record.created_at,
        )
