from __future__ import annotations

from uuid import UUID

from app.access.models import RuntimeTrainingConfig
from app.access.repository import AccessRepository


class AccessService:
    def __init__(self, repository: AccessRepository) -> None:
        self._repository = repository

    def get_default_training_config_for_user(self, user_id: UUID) -> RuntimeTrainingConfig:
        training_config = self._repository.get_default_training_config_for_user(user_id)
        if training_config is None:
            raise LookupError(f"Default training config for user '{user_id}' was not found.")
        return training_config

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
