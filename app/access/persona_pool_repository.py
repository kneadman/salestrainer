from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.access.models import ClientTrainingConfig, PersonaPoolEntry
from app.domain.contract_versions import PERSONA_SCHEMA_VERSION


def default_persona_pool_prompt_version() -> str:
    """Return the pool's default prompt revision.

    Imported lazily: ``app.prompts.versions`` reads prompt files from disk, and
    the access layer must stay importable in contexts where those files are not
    the ones under test.
    """
    from app.prompts.versions import prompt_revisions

    return prompt_revisions()["persona"]


class PersonaPoolRepository:
    """Persistence for the pre-generated persona reserve.

    The pool is a plain "claim the oldest ready row" queue. Claiming deletes the
    row inside the same transaction that reads it, so two concurrent session
    starts can never receive the same persona.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_available(
        self,
        *,
        training_config_id: UUID,
        scenario_id: str,
        context_hash: str,
        prompt_version: str,
    ) -> int:
        """Count unclaimed personas matching the current config revision."""
        statement = select(func.count()).select_from(PersonaPoolEntry).where(
            PersonaPoolEntry.training_config_id == training_config_id,
            PersonaPoolEntry.scenario_id == scenario_id,
            PersonaPoolEntry.context_hash == context_hash,
            PersonaPoolEntry.persona_prompt_version == prompt_version,
        )
        return int(self._session.scalar(statement) or 0)

    def claim_one(
        self,
        *,
        training_config_id: UUID,
        scenario_id: str,
        context_hash: str,
        prompt_version: str,
    ) -> PersonaPoolEntry | None:
        """Remove and return the oldest matching persona, or ``None`` when empty.

        Rows are locked with ``FOR UPDATE SKIP LOCKED`` where the dialect supports
        it, so concurrent requests never pick the same entry.
        """
        statement = (
            select(PersonaPoolEntry)
            .where(
                PersonaPoolEntry.training_config_id == training_config_id,
                PersonaPoolEntry.scenario_id == scenario_id,
                PersonaPoolEntry.context_hash == context_hash,
                PersonaPoolEntry.persona_prompt_version == prompt_version,
            )
            .order_by(PersonaPoolEntry.created_at)
            .limit(1)
        )
        if self._session.bind is not None and self._session.bind.dialect.name == "postgresql":
            statement = statement.with_for_update(skip_locked=True)
        entry = self._session.scalar(statement)
        if entry is None:
            return None
        self._session.delete(entry)
        self._session.commit()
        return entry

    def add_entry(
        self,
        *,
        training_config_id: UUID,
        client_account_id: UUID,
        scenario_id: str,
        context_hash: str,
        persona: dict,
        persona_prompt_version: str | None = None,
        persona_schema_version: str = PERSONA_SCHEMA_VERSION,
    ) -> PersonaPoolEntry:
        """Persist one ready persona for later claim."""
        entry = PersonaPoolEntry(
            training_config_id=training_config_id,
            client_account_id=client_account_id,
            scenario_id=scenario_id,
            context_hash=context_hash,
            persona=persona,
            persona_schema_version=persona_schema_version,
            persona_prompt_version=persona_prompt_version or default_persona_pool_prompt_version(),
        )
        self._session.add(entry)
        self._session.commit()
        self._session.refresh(entry)
        return entry

    def list_configs_with_pool_settings(self) -> list[ClientTrainingConfig]:
        """Return active training configs that are eligible for pool refills."""
        statement = select(ClientTrainingConfig).where(ClientTrainingConfig.is_active.is_(True))
        return list(self._session.scalars(statement))

    def drop_stale_entries(
        self,
        *,
        training_config_id: UUID,
        scenario_id: str,
        context_hash: str,
        prompt_version: str,
    ) -> int:
        """Delete reserve rows generated from an outdated config or prompt revision."""
        statement = delete(PersonaPoolEntry).where(
            PersonaPoolEntry.training_config_id == training_config_id,
            PersonaPoolEntry.scenario_id == scenario_id,
            (PersonaPoolEntry.context_hash != context_hash)
            | (PersonaPoolEntry.persona_prompt_version != prompt_version),
        )
        result = self._session.execute(statement)
        self._session.commit()
        return int(result.rowcount or 0)
