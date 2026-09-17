"""Persona pool: keep ready-made personas so session start is instant.

Generating a persona is one full structured LLM call. On a reasoning model that
costs seconds to tens of seconds, and every "start training" click paid it
inline. This module keeps a small reserve per training config and hands one out
on demand, refilling the reserve out of band.

Design notes
------------

* The reserve is keyed by ``(training_config_id, scenario_id, context_hash,
  persona_prompt_version)`` where ``context_hash`` covers everything that feeds
  generation: the free-text context, the structured seed config, and the seed
  template revision. Editing a training config or shipping a new prompt
  therefore invalidates the old reserve instead of serving a persona that no
  longer matches the configured business context.
* Claiming is a delete inside one transaction, so two concurrent session starts
  cannot receive the same persona.
* A refill failure is never fatal for the request that triggered it: the caller
  already has either a pooled persona or a freshly generated one.
"""

from __future__ import annotations

import hashlib
import json
import logging

from sqlalchemy.orm import Session

from app.access.models import RuntimeTrainingConfig
from app.access.persona_pool_repository import PersonaPoolRepository
from app.application.persona_generation_service import PersonaGenerationService
from app.domain.errors import PersonaGenerationError
from app.domain.models import PersonaProfile
from app.domain.token_counter import TokenCountedResult
from app.prompts.versions import prompt_revisions

logger = logging.getLogger(__name__)


def pool_prompt_version() -> str:
    """Return the persona-prompt revision used as part of the pool key.

    The durable history column keeps the stable ``PERSONA_PROMPT_VERSION`` label
    for backwards compatibility, but the reserve must be keyed by the *content*
    revision: otherwise editing ``persona_generator.md`` would leave sessions
    served personas produced by the previous prompt.
    """
    return prompt_revisions()["persona"]


def build_pool_context_hash(training_config: RuntimeTrainingConfig) -> str:
    """Hash everything that affects persona generation into a short pool key.

    Hashing the *inputs* rather than the rendered prompt keeps the pool
    independent from ``PersonaGenerationService`` and still invalidates the
    reserve when the seed config, the free-text context, or the seed template
    revision changes.
    """
    payload = json.dumps(
        {
            "persona_generation_context": training_config.persona_generation_context,
            "seed_config": training_config.seed_config,
            "seed_template": prompt_revisions()["persona_seed"],
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


class PersonaPoolService:
    """Claim personas from the reserve and top it up in the background."""

    def __init__(
        self,
        db_session: Session,
        *,
        generation_service: PersonaGenerationService,
        low_watermark: int,
        target_size: int,
        refill_batch_size: int,
    ) -> None:
        """Keep the session, the generator, and the reserve sizing policy."""
        if low_watermark < 0:
            raise ValueError("low_watermark must not be negative.")
        # ``target_size=0`` is the documented "pool disabled" switch; otherwise the
        # watermark has to leave headroom for a refill to actually add something.
        if target_size > 0 and target_size <= low_watermark:
            raise ValueError("target_size must be greater than low_watermark.")
        self._session = db_session
        self._repository = PersonaPoolRepository(db_session)
        self._generation_service = generation_service
        self._low_watermark = low_watermark
        self._target_size = target_size
        self._refill_batch_size = max(1, refill_batch_size)

    @property
    def enabled(self) -> bool:
        """Report whether the reserve can hold anything at all."""
        return self._target_size > 0

    def context_hash_for(self, training_config: RuntimeTrainingConfig) -> str:
        """Compute the pool key for one training config without generating anything."""
        return build_pool_context_hash(training_config)

    def claim(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str,
    ) -> PersonaProfile | None:
        """Pop one ready persona, or return ``None`` when the reserve is empty.

        A persona that no longer validates (schema drift, model change) is
        discarded and treated as a miss rather than surfaced as an error.
        """
        if not self.enabled:
            return None
        context_hash = self.context_hash_for(training_config)
        try:
            entry = self._repository.claim_one(
                training_config_id=training_config.id,
                scenario_id=scenario_id,
                context_hash=context_hash,
                prompt_version=pool_prompt_version(),
            )
        except Exception:
            # A failed statement leaves the session unusable until it is rolled
            # back. Swallow the error (the caller regenerates on demand) but never
            # hand a poisoned session back to the request.
            self._rollback()
            logger.warning(
                "persona_pool_claim_failed training_config_id=%s scenario_id=%s",
                training_config.id,
                scenario_id,
                exc_info=True,
            )
            return None
        if entry is None:
            return None
        try:
            persona = PersonaProfile.model_validate(entry.persona)
        except Exception:
            logger.warning(
                "persona_pool_entry_invalid training_config_id=%s scenario_id=%s pool_entry_id=%s",
                training_config.id,
                scenario_id,
                entry.id,
            )
            return None
        logger.info(
            "persona_pool_claim training_config_id=%s scenario_id=%s persona_id=%s",
            training_config.id,
            scenario_id,
            persona.id,
        )
        return persona

    def available_count(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str,
    ) -> int:
        """Return how many personas are ready for this exact config revision."""
        return self._repository.count_available(
            training_config_id=training_config.id,
            scenario_id=scenario_id,
            context_hash=self.context_hash_for(training_config),
            prompt_version=pool_prompt_version(),
        )

    def refill(
        self,
        *,
        training_config: RuntimeTrainingConfig,
        scenario_id: str,
    ) -> list[TokenCountedResult[PersonaProfile]]:
        """Top the reserve up to ``target_size`` when it dropped below the watermark.

        Returns the generation results so the caller can record token usage.
        Generation failures are logged and swallowed; the reserve simply stays
        below target and is retried on the next cycle.
        """
        if not self.enabled:
            return []
        try:
            self._repository.drop_stale_entries(
                training_config_id=training_config.id,
                scenario_id=scenario_id,
                context_hash=self.context_hash_for(training_config),
                prompt_version=pool_prompt_version(),
            )
            available = self.available_count(training_config=training_config, scenario_id=scenario_id)
        except Exception:
            self._rollback()
            logger.warning(
                "persona_pool_refill_lookup_failed training_config_id=%s scenario_id=%s",
                training_config.id,
                scenario_id,
                exc_info=True,
            )
            return []
        if available > self._low_watermark:
            return []
        missing = self._target_size - available
        results: list[TokenCountedResult[PersonaProfile]] = []
        for _ in range(min(missing, self._refill_batch_size)):
            try:
                result = self._generation_service.generate_for_training_config(
                    training_config=training_config,
                    scenario_id=scenario_id,
                )
            except PersonaGenerationError as error:
                logger.warning(
                    "persona_pool_refill_generation_failed training_config_id=%s scenario_id=%s error=%s",
                    training_config.id,
                    scenario_id,
                    error,
                )
                break
            try:
                self._repository.add_entry(
                    training_config_id=training_config.id,
                    client_account_id=training_config.client_account_id,
                    scenario_id=scenario_id,
                    context_hash=self.context_hash_for(training_config),
                    persona=result.value.model_dump(mode="json"),
                    # Explicit, not a hidden default: the write key must stay
                    # identical to the read key in claim()/available_count().
                    persona_prompt_version=pool_prompt_version(),
                )
            except Exception:
                self._rollback()
                logger.warning(
                    "persona_pool_refill_persist_failed training_config_id=%s scenario_id=%s",
                    training_config.id,
                    scenario_id,
                    exc_info=True,
                )
                break
            results.append(result)
        if results:
            logger.info(
                "persona_pool_refilled training_config_id=%s scenario_id=%s added=%s",
                training_config.id,
                scenario_id,
                len(results),
            )
        return results

    def refill_all_active_configs(self, *, scenario_ids: list[str]) -> list[TokenCountedResult[PersonaProfile]]:
        """Top up every active training config for each supplied scenario.

        Used by the background worker. One config failing must not stop the rest.
        """
        results: list[TokenCountedResult[PersonaProfile]] = []
        for record in self._repository.list_configs_with_pool_settings():
            training_config = RuntimeTrainingConfig.model_validate(
                {
                    "id": record.id,
                    "client_account_id": record.client_account_id,
                    "name": record.name,
                    "persona_generation_context": record.persona_generation_context,
                    "seed_config": record.seed_config,
                    "is_active": record.is_active,
                }
            )
            for scenario_id in scenario_ids:
                try:
                    results.extend(
                        self.refill(training_config=training_config, scenario_id=scenario_id)
                    )
                except Exception:
                    self._rollback()
                    logger.warning(
                        "persona_pool_refill_failed training_config_id=%s scenario_id=%s",
                        training_config.id,
                        scenario_id,
                        exc_info=True,
                    )
        return results

    def _rollback(self) -> None:
        """Return the session to a usable state after a failed statement."""
        try:
            self._session.rollback()
        except Exception:
            logger.warning("persona_pool_rollback_failed", exc_info=True)
