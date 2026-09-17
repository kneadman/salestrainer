from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import ClientTrainingConfig, PersonaPoolEntry, RuntimeTrainingConfig
from app.access.persona_pool_repository import PersonaPoolRepository
from app.application.persona_pool_service import PersonaPoolService, build_pool_context_hash
from app.domain.contract_versions import PERSONA_PROMPT_VERSION
from app.domain.errors import PersonaGenerationError
from app.domain.persona_generation import UniversalFakePersonaGenerator
from app.domain.token_counter import TokenCountedResult
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from tests.unit._persona_fixtures import valid_minimal_persona


def _create_session() -> Session:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def _persist_config(session: Session, *, prompt: str = "Generate a persona.") -> RuntimeTrainingConfig:
    from app.identity.repository import IdentityRepository

    identity = IdentityRepository(session)
    account = identity.create_client_account(name="Acme", slug=f"acme-{uuid4().hex[:8]}")
    record = ClientTrainingConfig(
        client_account_id=account.id,
        name="Config",
        persona_generation_context=prompt,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return RuntimeTrainingConfig(
        id=record.id,
        client_account_id=record.client_account_id,
        name=record.name,
        persona_generation_context=record.persona_generation_context,
        seed_config=record.seed_config,
        is_active=record.is_active,
    )


class _StubGenerator:
    """Generation service double that counts calls and can be made to fail."""

    def __init__(self, *, fail_after: int | None = None) -> None:
        self.calls = 0
        self._fail_after = fail_after

    def generate_for_training_config(self, *, training_config, scenario_id=None):  # type: ignore[no-untyped-def]
        del training_config, scenario_id
        self.calls += 1
        if self._fail_after is not None and self.calls > self._fail_after:
            raise PersonaGenerationError("generator exploded")
        persona = valid_minimal_persona(id=f"pooled_persona_{self.calls}")
        return TokenCountedResult(value=persona, input_tokens=10, output_tokens=20)


def _service(session: Session, generator, **overrides) -> PersonaPoolService:
    defaults = {"low_watermark": 1, "target_size": 3, "refill_batch_size": 5}
    defaults.update(overrides)
    return PersonaPoolService(session, generation_service=generator, **defaults)  # type: ignore[arg-type]


def test_pool_context_hash_is_stable_and_content_sensitive() -> None:
    session = _create_session()
    config = _persist_config(session, prompt="context A")
    other = _persist_config(session, prompt="context A")
    different = _persist_config(session, prompt="context B")

    # Same config content hash the same regardless of the row identity.
    assert build_pool_context_hash(config) == build_pool_context_hash(other)
    assert build_pool_context_hash(config) != build_pool_context_hash(different)
    assert len(build_pool_context_hash(config)) == 32


def test_pool_context_hash_changes_when_seed_config_changes() -> None:
    session = _create_session()
    config = _persist_config(session)

    with_seed = config.model_copy(update={"seed_config": {"pains": ["a"]}})

    assert build_pool_context_hash(config) != build_pool_context_hash(with_seed)


def test_claim_returns_none_when_pool_is_empty() -> None:
    session = _create_session()
    config = _persist_config(session)
    service = _service(session, _StubGenerator())

    assert service.claim(training_config=config, scenario_id="first_contact_discovery") is None


def test_refill_then_claim_returns_pooled_persona_without_generating() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator)

    results = service.refill(training_config=config, scenario_id="first_contact_discovery")

    assert len(results) == 3
    assert generator.calls == 3
    assert service.available_count(training_config=config, scenario_id="first_contact_discovery") == 3

    claimed = service.claim(training_config=config, scenario_id="first_contact_discovery")

    assert claimed is not None
    # Claiming must not trigger generation.
    assert generator.calls == 3
    assert service.available_count(training_config=config, scenario_id="first_contact_discovery") == 2


def test_claim_is_exclusive_across_repeated_calls() -> None:
    session = _create_session()
    config = _persist_config(session)
    service = _service(session, _StubGenerator())
    service.refill(training_config=config, scenario_id="first_contact_discovery")

    claimed_ids = [
        service.claim(training_config=config, scenario_id="first_contact_discovery").id  # type: ignore[union-attr]
        for _ in range(3)
    ]

    assert len(set(claimed_ids)) == 3
    assert service.claim(training_config=config, scenario_id="first_contact_discovery") is None


def test_refill_is_skipped_while_above_low_watermark() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator)
    service.refill(training_config=config, scenario_id="first_contact_discovery")

    assert service.refill(training_config=config, scenario_id="first_contact_discovery") == []
    assert generator.calls == 3


def test_refill_tops_up_after_reserve_drops_to_watermark() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator)
    service.refill(training_config=config, scenario_id="first_contact_discovery")

    # Drop to the low watermark (1) and refill back to target.
    service.claim(training_config=config, scenario_id="first_contact_discovery")
    service.claim(training_config=config, scenario_id="first_contact_discovery")
    assert service.available_count(training_config=config, scenario_id="first_contact_discovery") == 1

    service.refill(training_config=config, scenario_id="first_contact_discovery")

    assert service.available_count(training_config=config, scenario_id="first_contact_discovery") == 3


def test_pool_is_scenario_scoped() -> None:
    session = _create_session()
    config = _persist_config(session)
    service = _service(session, _StubGenerator())
    service.refill(training_config=config, scenario_id="first_contact_discovery")

    assert service.available_count(training_config=config, scenario_id="objection_handling") == 0
    assert service.claim(training_config=config, scenario_id="objection_handling") is None


def test_editing_config_context_invalidates_stale_reserve() -> None:
    session = _create_session()
    config = _persist_config(session, prompt="Generate persona for configuration A.")
    generator = _StubGenerator()
    service = _service(session, generator)
    service.refill(training_config=config, scenario_id="first_contact_discovery")

    updated = config.model_copy(update={"persona_generation_context": "Generate persona for configuration B."})

    # The stale reserve is invisible to the new revision...
    assert service.available_count(training_config=updated, scenario_id="first_contact_discovery") == 0
    assert service.claim(training_config=updated, scenario_id="first_contact_discovery") is None
    # ...and the refill drops it instead of accumulating garbage.
    service.refill(training_config=updated, scenario_id="first_contact_discovery")

    rows = session.query(PersonaPoolEntry).all()
    assert len(rows) == 3
    assert {row.context_hash for row in rows} == {service.context_hash_for(updated)}


def test_refill_stops_on_generation_error_without_raising() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator(fail_after=1)
    service = _service(session, generator)

    results = service.refill(training_config=config, scenario_id="first_contact_discovery")

    assert len(results) == 1
    assert service.available_count(training_config=config, scenario_id="first_contact_discovery") == 1


def test_disabled_pool_never_generates() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator, target_size=0, low_watermark=0)

    assert service.enabled is False
    assert service.refill(training_config=config, scenario_id="first_contact_discovery") == []
    assert service.claim(training_config=config, scenario_id="first_contact_discovery") is None
    assert generator.calls == 0


def test_claim_recovers_when_the_repository_raises() -> None:
    """A failed claim must return a miss and leave the session reusable."""
    session = _create_session()
    config = _persist_config(session)
    service = _service(session, _StubGenerator())

    class BrokenRepository:
        def claim_one(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("database is on fire")

    service._repository = BrokenRepository()  # type: ignore[assignment]

    assert service.claim(training_config=config, scenario_id="first_contact_discovery") is None
    # Session is still usable afterwards.
    service._repository = PersonaPoolRepository(session)  # type: ignore[assignment]
    assert service.available_count(training_config=config, scenario_id="first_contact_discovery") == 0


def test_refill_recovers_when_stale_cleanup_raises() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator)

    class BrokenRepository:
        def drop_stale_entries(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("database is on fire")

    service._repository = BrokenRepository()  # type: ignore[assignment]

    assert service.refill(training_config=config, scenario_id="first_contact_discovery") == []
    assert generator.calls == 0


def test_refill_recovers_when_persisting_raises() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator)

    class BrokenRepository:
        def drop_stale_entries(self, **kwargs):  # type: ignore[no-untyped-def]
            return 0

        def count_available(self, **kwargs):  # type: ignore[no-untyped-def]
            return 0

        def add_entry(self, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("cannot persist")

    service._repository = BrokenRepository()  # type: ignore[assignment]

    assert service.refill(training_config=config, scenario_id="first_contact_discovery") == []
    # Generation happened, persistence failed, and nothing was reported as added.
    assert generator.calls == 1


def test_pool_rejects_invalid_sizing_configuration() -> None:
    session = _create_session()
    generator = _StubGenerator()

    with pytest.raises(ValueError, match="target_size must be greater"):
        _service(session, generator, target_size=2, low_watermark=2)
    with pytest.raises(ValueError, match="low_watermark must not be negative"):
        _service(session, generator, target_size=2, low_watermark=-1)
    # target_size=0 is the supported "disabled" switch and must not raise.
    assert _service(session, generator, target_size=0, low_watermark=0).enabled is False


def test_invalid_pooled_persona_is_discarded_as_a_miss() -> None:
    session = _create_session()
    config = _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator)
    service.refill(training_config=config, scenario_id="first_contact_discovery")

    entry = session.query(PersonaPoolEntry).first()
    assert entry is not None
    entry.persona = {"not": "a persona"}
    session.commit()

    assert service.claim(training_config=config, scenario_id="first_contact_discovery") is None
    # The broken row was consumed, not returned forever.
    assert service.available_count(training_config=config, scenario_id="first_contact_discovery") == 2


def test_refill_all_active_configs_covers_every_scenario() -> None:
    session = _create_session()
    _persist_config(session)
    generator = _StubGenerator()
    service = _service(session, generator)

    results = service.refill_all_active_configs(
        scenario_ids=["first_contact_discovery", "objection_handling"]
    )

    assert len(results) == 6
    assert generator.calls == 6


def test_repository_counts_only_current_prompt_revision() -> None:
    session = _create_session()
    config = _persist_config(session)
    repository = PersonaPoolRepository(session)
    repository.add_entry(
        training_config_id=config.id,
        client_account_id=config.client_account_id,
        scenario_id="first_contact_discovery",
        context_hash="hash-a",
        persona=valid_minimal_persona().model_dump(mode="json"),
    )

    assert (
        repository.count_available(
            training_config_id=config.id,
            scenario_id="first_contact_discovery",
            context_hash="hash-a",
            prompt_version=PERSONA_PROMPT_VERSION,
        )
        == 1
    )
    assert (
        repository.count_available(
            training_config_id=config.id,
            scenario_id="first_contact_discovery",
            context_hash="hash-a",
            prompt_version="outdated-prompt",
        )
        == 0
    )


def test_local_fake_generator_backed_pool_end_to_end() -> None:
    """Real generation service + real repository, no LLM call involved."""
    from app.application.persona_generation_service import PersonaGenerationService

    session = _create_session()
    config = _persist_config(session, prompt="")
    settings = Settings(app_env="local", allow_fake_llm_fallback=True)
    generation_service = PersonaGenerationService(
        session,
        settings=settings,
        fallback_generator=UniversalFakePersonaGenerator(seed=7),
    )
    service = PersonaPoolService(
        session,
        generation_service=generation_service,
        low_watermark=1,
        target_size=2,
        refill_batch_size=2,
    )

    service.refill(training_config=config, scenario_id="first_contact_discovery")
    claimed = service.claim(training_config=config, scenario_id="first_contact_discovery")

    assert claimed is not None
    assert claimed.id.startswith("generated_first_contact_discovery_")
    assert claimed.authority_level == "final_decider"
