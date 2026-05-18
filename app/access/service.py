from __future__ import annotations

from uuid import UUID

from app.access.models import RuntimeTrainingConfig, TrainingSessionOwnership
from app.access.repository import AccessRepository


class AccessService:
    def __init__(self, repository: AccessRepository) -> None:
        self._repository = repository

    def get_default_training_config_for_user(self, user_id: UUID) -> RuntimeTrainingConfig:
        training_config = self._repository.get_default_training_config_for_user(user_id)
        if training_config is None:
            raise LookupError(f"Default training config for user '{user_id}' was not found.")
        return training_config

    def get_training_config_by_id(self, config_id: UUID) -> RuntimeTrainingConfig | None:
        config = self._repository.get_training_config_by_id(config_id)
        if config is None:
            return None
        return RuntimeTrainingConfig.model_validate(
            {
                "id": config.id,
                "client_account_id": config.client_account_id,
                "name": config.name,
                "persona_generation_context": config.persona_generation_context,
                "seed_config": config.seed_config,
                "is_active": config.is_active,
            }
        )

    def bind_session_to_user(
        self,
        session_id: UUID,
        user_id: UUID,
        client_account_id: UUID,
        training_config_id: UUID,
    ) -> None:
        self._repository.create_training_session_ownership(
            session_id=session_id,
            user_id=user_id,
            client_account_id=client_account_id,
            training_config_id=training_config_id,
        )

    def require_session_access(self, session_id: str | UUID, user_id: UUID) -> None:
        normalized_session_id = session_id if isinstance(session_id, UUID) else self._parse_session_id(session_id)
        if not self._repository.check_session_ownership(
            session_id=normalized_session_id,
            user_id=user_id,
        ):
            raise LookupError("Session not found.")

    def get_session_ownership(self, session_id: str | UUID) -> TrainingSessionOwnership:
        """Return ownership metadata or hide missing/invalid sessions behind LookupError."""
        normalized_session_id = session_id if isinstance(session_id, UUID) else self._parse_session_id(session_id)
        ownership = self._repository.get_session_ownership(normalized_session_id)
        if ownership is None:
            raise LookupError("Session not found.")
        return ownership

    def delete_session_ownership(self, session_id: str | UUID) -> None:
        """Remove session ownership during compensated API session creation."""
        normalized_session_id = session_id if isinstance(session_id, UUID) else self._parse_session_id(session_id)
        self._repository.delete_training_session_ownership(normalized_session_id)

    @staticmethod
    def _parse_session_id(session_id: str) -> UUID:
        try:
            return UUID(str(session_id))
        except (TypeError, ValueError) as error:
            raise LookupError("Session not found.") from error
