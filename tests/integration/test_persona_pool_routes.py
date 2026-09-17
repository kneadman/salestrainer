from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import PersonaPoolEntry, RuntimeTrainingConfig
from app.access.persona_pool_repository import PersonaPoolRepository
from app.access.repository import AccessRepository
from app.api.dependencies import get_persona_generation_service, get_persona_pool_service
from app.api.main import create_app
from app.application.persona_pool_service import PersonaPoolService, build_pool_context_hash
from app.domain.token_counter import TokenCountedResult
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, get_db_session, import_model_modules
from app.infrastructure.fake_llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository
from tests.integration.test_api_routes import _login, _seed_authenticated_user
from tests.unit._persona_fixtures import valid_minimal_persona


def _create_db_session() -> Session:
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


class _CountingGenerator:
    """Persona generation double that returns a distinguishable persona per call."""

    def __init__(self) -> None:
        self.calls = 0

    def generate_for_training_config(self, *, training_config, scenario_id=None):  # type: ignore[no-untyped-def]
        del training_config, scenario_id
        self.calls += 1
        persona = valid_minimal_persona(id=f"generated_on_demand_{self.calls}")
        return TokenCountedResult(value=persona, input_tokens=11, output_tokens=22)


def _runtime_config(db_session: Session, training_config, *, prompt: str) -> RuntimeTrainingConfig:
    """Persist a generation context and return the runtime view of the config."""
    AccessRepository(db_session).update_training_config(
        training_config_id=training_config.id,
        persona_generation_context=prompt,
    )
    record = AccessRepository(db_session).get_training_config_by_id(training_config.id)
    assert record is not None
    return RuntimeTrainingConfig.model_validate(
        {
            "id": record.id,
            "client_account_id": record.client_account_id,
            "name": record.name,
            "persona_generation_context": record.persona_generation_context,
            "seed_config": record.seed_config,
            "is_active": record.is_active,
        }
    )


def _seed_pool(
    db_session: Session,
    training_config: RuntimeTrainingConfig,
    *,
    count: int,
    scenario_id: str = "first_contact_discovery",
) -> None:
    """Insert ready personas for the exact config revision the request will use."""
    repository = PersonaPoolRepository(db_session)
    for index in range(count):
        repository.add_entry(
            training_config_id=training_config.id,
            client_account_id=training_config.client_account_id,
            scenario_id=scenario_id,
            context_hash=build_pool_context_hash(training_config),
            persona=valid_minimal_persona(id=f"pooled_persona_{index}").model_dump(mode="json"),
        )


def _build_client(db_session: Session, repository, *, generation_service) -> TestClient:
    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0),
        repository=repository,
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session():
        yield db_session

    def override_pool_service() -> PersonaPoolService:
        settings = Settings(auth_cookie_secure=False)
        return PersonaPoolService(
            db_session,
            generation_service=generation_service,
            low_watermark=settings.persona_pool_low_watermark,
            target_size=settings.persona_pool_target_size,
            refill_batch_size=settings.persona_pool_refill_batch_size,
        )

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_persona_generation_service] = lambda: generation_service
    app.dependency_overrides[get_persona_pool_service] = override_pool_service
    return TestClient(app, raise_server_exceptions=False)


def test_create_session_serves_pooled_persona_without_calling_the_llm() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _, training_config = _seed_authenticated_user(db_session)
    runtime_config = _runtime_config(db_session, training_config, prompt="Pooled context.")
    _seed_pool(db_session, runtime_config, count=2)
    generator = _CountingGenerator()
    client = _build_client(db_session, repository, generation_service=generator)
    _login(client)

    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    saved_session = repository.get(response.json()["session"]["session_id"])
    assert saved_session is not None
    # The pooled persona was served and no LLM call happened on the request path.
    assert saved_session.persona.id == "pooled_persona_0"
    assert generator.calls == 0
    assert db_session.query(PersonaPoolEntry).count() == 1
    db_session.close()


def test_create_session_generates_on_demand_when_pool_is_empty() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _, training_config = _seed_authenticated_user(db_session)
    _runtime_config(db_session, training_config, prompt="Pooled context.")
    generator = _CountingGenerator()
    client = _build_client(db_session, repository, generation_service=generator)
    _login(client)

    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    saved_session = repository.get(response.json()["session"]["session_id"])
    assert saved_session is not None
    assert saved_session.persona.id == "generated_on_demand_1"
    assert generator.calls == 1
    db_session.close()


def test_create_session_falls_back_to_generation_when_pooled_persona_is_corrupt() -> None:
    """A broken reserve row must degrade to a fresh generation, never a 500."""
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _, training_config = _seed_authenticated_user(db_session)
    runtime_config = _runtime_config(db_session, training_config, prompt="Pooled context.")
    _seed_pool(db_session, runtime_config, count=1)
    entry = db_session.query(PersonaPoolEntry).first()
    assert entry is not None
    entry.persona = {"broken": True}
    db_session.commit()

    generator = _CountingGenerator()
    client = _build_client(db_session, repository, generation_service=generator)
    _login(client)

    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    saved_session = repository.get(response.json()["session"]["session_id"])
    assert saved_session is not None
    assert saved_session.persona.id == "generated_on_demand_1"
    assert generator.calls == 1
    db_session.close()


def test_pooled_persona_is_scenario_scoped_on_the_request_path() -> None:
    """A persona pooled for another scenario must not be served."""
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _, training_config = _seed_authenticated_user(db_session)
    runtime_config = _runtime_config(db_session, training_config, prompt="Pooled context.")
    _seed_pool(db_session, runtime_config, count=1)

    generator = _CountingGenerator()
    client = _build_client(db_session, repository, generation_service=generator)
    _login(client)

    response = client.post("/api/sessions", json={"scenario_id": "objection_handling"})

    assert response.status_code == 201
    saved_session = repository.get(response.json()["session"]["session_id"])
    assert saved_session is not None
    assert saved_session.persona.id == "generated_on_demand_1"
    assert generator.calls == 1
    db_session.close()


def test_session_start_records_no_persona_token_usage_for_pooled_persona() -> None:
    """Pooled personas were paid for by the refill, so the request must not bill them again."""
    from app.history.models import TokenUsageRecord

    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _, training_config = _seed_authenticated_user(db_session)
    runtime_config = _runtime_config(db_session, training_config, prompt="Pooled context.")
    _seed_pool(db_session, runtime_config, count=1)
    generator = _CountingGenerator()
    client = _build_client(db_session, repository, generation_service=generator)
    _login(client)

    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    usage = db_session.query(TokenUsageRecord).filter(TokenUsageRecord.event_type == "persona_generation").all()
    assert usage == []
    db_session.close()
