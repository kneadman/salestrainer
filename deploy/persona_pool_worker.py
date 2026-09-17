#!/usr/bin/env python3
"""Background worker that keeps the pre-generated persona reserve topped up.

Runs as a long-lived container next to the backend. Every
``PERSONA_POOL_REFILL_INTERVAL_SECONDS`` it walks active training configs and
refills the reserve through the same ``PersonaPoolService`` the admin CLI uses
(``python -m app.admin.cli warm-persona-pool``), so the manual and background
paths cannot drift.

Sizing notes: one persona generation is a full structured LLM call, so the
worker is intentionally slow and serial. It only starts a refill when the
reserve dropped to the low watermark, so a healthy system does nothing.
"""
from __future__ import annotations

import logging
import time

from app.application.persona_generation_service import PersonaGenerationService
from app.application.persona_pool_service import PersonaPoolService
from app.infrastructure.config import get_settings
from app.infrastructure.db import get_session_factory, import_model_modules

logger = logging.getLogger("persona_pool_worker")


def run_refill_once() -> int:
    """Refill the reserve for every active config and scenario; return rows added.

    ``import_model_modules`` is required here: the worker runs as a standalone
    process, and without it the ORM metadata lacks tables owned by modules nobody
    imported, which surfaces as a foreign-key resolution error.
    """
    import_model_modules()
    settings = get_settings()
    # Only the configured scenarios: the UI resolves every session to the default
    # scenario, so warming the rest would pay for personas nothing can claim.
    scenario_ids = settings.resolved_persona_pool_scenario_ids()
    with get_session_factory()() as session:
        generation_service = PersonaGenerationService(session, settings=settings)
        pool_service = PersonaPoolService(
            session,
            generation_service=generation_service,
            low_watermark=settings.persona_pool_low_watermark,
            target_size=settings.persona_pool_target_size,
            refill_batch_size=settings.persona_pool_refill_batch_size,
        )
        return len(pool_service.refill_all_active_configs(scenario_ids=scenario_ids))


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    interval = settings.persona_pool_refill_interval_seconds
    enabled = settings.persona_pool_enabled and settings.persona_pool_target_size > 0
    logger.info(
        "persona_pool_worker_started enabled=%s target=%s low_watermark=%s interval_seconds=%s",
        enabled,
        settings.persona_pool_target_size,
        settings.persona_pool_low_watermark,
        interval,
    )
    if not enabled:
        logger.warning("persona_pool_worker_disabled pool is switched off; worker stays idle")
    while True:
        if enabled:
            try:
                added = run_refill_once()
                if added:
                    logger.info("persona_pool_worker_cycle added=%s", added)
            except Exception:
                # A failed cycle must not kill the worker; the next one retries.
                logger.warning("persona_pool_worker_cycle_failed", exc_info=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()
