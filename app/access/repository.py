from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.access.models import (
    AuditLog,
    ClientTrainingConfig,
    LLMProviderConfig,
    RuntimeTrainingConfig,
    TrainingSessionOwnership,
    UserTrainingConfig,
)


class AccessRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_training_config(
        self,
        *,
        client_account_id: UUID,
        name: str,
        default_scenario_id: str,
        persona_generation_context: str = "",
        persona_policy: dict[str, object] | None = None,
        ui_config: dict[str, object] | None = None,
        limits: dict[str, object] | None = None,
        llm_provider_config_id: UUID | None = None,
        is_active: bool = True,
        training_config_id: UUID | None = None,
    ) -> ClientTrainingConfig:
        training_config_kwargs = dict(
            client_account_id=client_account_id,
            name=name,
            default_scenario_id=default_scenario_id,
            persona_generation_context=persona_generation_context,
            persona_policy=persona_policy or {},
            ui_config=ui_config or {},
            limits=limits or {},
            is_active=is_active,
            llm_provider_config_id=llm_provider_config_id,
        )
        if training_config_id is not None:
            training_config_kwargs["id"] = training_config_id
        training_config = ClientTrainingConfig(**training_config_kwargs)
        self._session.add(training_config)
        self._session.commit()
        self._session.refresh(training_config)
        return training_config

    def assign_training_config_to_user(
        self,
        *,
        user_id: UUID,
        training_config_id: UUID,
        is_default: bool = False,
    ) -> UserTrainingConfig:
        if is_default:
            self._session.execute(
                update(UserTrainingConfig)
                .where(UserTrainingConfig.user_id == user_id)
                .values(is_default=False)
            )

        assignment = self._session.get(
            UserTrainingConfig,
            {"user_id": user_id, "training_config_id": training_config_id},
        )
        if assignment is None:
            assignment = UserTrainingConfig(
                user_id=user_id,
                training_config_id=training_config_id,
                is_default=is_default,
            )
            self._session.add(assignment)
        else:
            assignment.is_default = is_default

        self._session.commit()
        self._session.refresh(assignment)
        return assignment

    def get_default_training_config_for_user(self, user_id: UUID) -> RuntimeTrainingConfig | None:
        statement = (
            select(ClientTrainingConfig)
            .join(UserTrainingConfig, UserTrainingConfig.training_config_id == ClientTrainingConfig.id)
            .where(
                UserTrainingConfig.user_id == user_id,
                UserTrainingConfig.is_default.is_(True),
            )
        )
        training_config = self._session.scalar(statement)
        if training_config is None:
            return None

        return RuntimeTrainingConfig.model_validate(
            {
                "id": training_config.id,
                "client_account_id": training_config.client_account_id,
                "name": training_config.name,
                "default_scenario_id": training_config.default_scenario_id,
                "persona_generation_context": training_config.persona_generation_context,
                "persona_policy": training_config.persona_policy,
                "ui_config": training_config.ui_config,
                "limits": training_config.limits,
                "llm_provider_config_id": training_config.llm_provider_config_id,
            }
        )

    def list_training_configs_for_client_by_name(
        self,
        *,
        client_account_id: UUID,
        name: str,
    ) -> list[ClientTrainingConfig]:
        statement = select(ClientTrainingConfig).where(
            ClientTrainingConfig.client_account_id == client_account_id,
            ClientTrainingConfig.name == name,
        )
        return list(self._session.scalars(statement))

    def update_training_config(
        self,
        *,
        training_config_id: UUID,
        name: str | None = None,
        default_scenario_id: str | None = None,
        persona_generation_context: str | None = None,
        persona_policy: dict[str, object] | None = None,
        ui_config: dict[str, object] | None = None,
        limits: dict[str, object] | None = None,
        llm_provider_config_id: UUID | None = None,
    ) -> ClientTrainingConfig | None:
        training_config = self._session.get(ClientTrainingConfig, training_config_id)
        if training_config is None:
            return None

        if name is not None:
            training_config.name = name
        if default_scenario_id is not None:
            training_config.default_scenario_id = default_scenario_id
        if persona_generation_context is not None:
            training_config.persona_generation_context = persona_generation_context
        if persona_policy is not None:
            training_config.persona_policy = persona_policy
        if ui_config is not None:
            training_config.ui_config = ui_config
        if limits is not None:
            training_config.limits = limits
        if llm_provider_config_id is not None:
            training_config.llm_provider_config_id = llm_provider_config_id

        self._session.commit()
        self._session.refresh(training_config)
        return training_config

    def get_training_config_by_id(self, training_config_id: UUID) -> ClientTrainingConfig | None:
        return self._session.get(ClientTrainingConfig, training_config_id)

    def get_llm_provider_config_by_id(self, config_id: UUID) -> LLMProviderConfig | None:
        return self._session.get(LLMProviderConfig, config_id)

    def create_training_session_ownership(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        client_account_id: UUID,
        training_config_id: UUID,
    ) -> TrainingSessionOwnership:
        ownership = TrainingSessionOwnership(
            session_id=session_id,
            user_id=user_id,
            client_account_id=client_account_id,
            training_config_id=training_config_id,
        )
        self._session.add(ownership)
        self._session.commit()
        self._session.refresh(ownership)
        return ownership

    def check_session_ownership(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        client_account_id: UUID | None = None,
    ) -> bool:
        statement = select(TrainingSessionOwnership).where(
            TrainingSessionOwnership.session_id == session_id,
            TrainingSessionOwnership.user_id == user_id,
        )
        if client_account_id is not None:
            statement = statement.where(TrainingSessionOwnership.client_account_id == client_account_id)

        return self._session.scalar(statement) is not None

    def get_session_ownership(self, session_id: UUID) -> TrainingSessionOwnership | None:
        """Load ownership metadata needed by API-side history writes."""
        return self._session.get(TrainingSessionOwnership, session_id)

    def delete_training_session_ownership(self, session_id: UUID) -> None:
        """Delete ownership metadata when runtime session creation is compensated."""
        ownership = self._session.get(TrainingSessionOwnership, session_id)
        if ownership is not None:
            self._session.delete(ownership)
            self._session.commit()

    def create_audit_log_record(
        self,
        *,
        action: str,
        entity_type: str,
        actor_user_id: UUID | None = None,
        entity_id: UUID | None = None,
        payload: dict[str, object] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        audit_log_id: UUID | None = None,
    ) -> AuditLog:
        audit_record_kwargs = dict(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        if audit_log_id is not None:
            audit_record_kwargs["id"] = audit_log_id
        audit_record = AuditLog(**audit_record_kwargs)
        self._session.add(audit_record)
        self._session.commit()
        self._session.refresh(audit_record)
        return audit_record
