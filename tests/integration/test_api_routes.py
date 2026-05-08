from __future__ import annotations

from collections.abc import Generator
from io import BytesIO
import tempfile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import LandingLead, TrainingSessionOwnership
from app.access.repository import AccessRepository
from app.api.dependencies import get_persona_generation_service
from app.api.main import create_app
from app.domain.models import PersonaProfile
from app.history.models import TrainingTurnRecord, UsageEventRecord
from app.identity.dependencies import get_db_session
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository
from app.infrastructure.stt_client import FakeSTTClient, STTResult


def _create_db_session() -> Session:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def _create_client(
    db_session: Session | None = None,
    *,
    repository: InMemorySessionRepository | None = None,
    settings: Settings | None = None,
    stt_client: FakeSTTClient | None = None,
) -> TestClient:
    app = create_app(
        settings=settings or Settings(auth_cookie_secure=False, login_rate_limit_attempts=0),
        repository=repository or InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
        stt_client=stt_client,
    )

    if db_session is not None:
        def override_get_db_session() -> Generator[Session, None, None]:
            yield db_session

        app.dependency_overrides[get_db_session] = override_get_db_session

    return TestClient(app)


def _seed_authenticated_user(
    db_session: Session,
    *,
    email: str = "manager@example.com",
    password: str = "password",
    role: str = "client_user",
    client_account_name: str = "Acme",
    client_account_slug: str = "acme",
    default_scenario_id: str = "first_contact_discovery",
    persona_policy: dict[str, object] | None = None,
    ui_config: dict[str, object] | None = None,
) -> tuple[object, object]:
    identity_repository = IdentityRepository(db_session)
    access_repository = AccessRepository(db_session)
    client_account = identity_repository.create_client_account(
        name=client_account_name,
        slug=client_account_slug,
    )
    user = identity_repository.create_user(
        client_account_id=client_account.id,
        email=email,
        password_hash=hash_password(password),
        role=role,
        must_change_password=False,
    )
    training_config = access_repository.create_training_config(
        client_account_id=client_account.id,
        name="Default config",
        default_scenario_id=default_scenario_id,
        persona_policy=persona_policy or {},
        ui_config=ui_config or {},
    )
    access_repository.assign_training_config_to_user(
        user_id=user.id,
        training_config_id=training_config.id,
        is_default=True,
    )
    return user, training_config


def _login(client: TestClient, *, email: str = "manager@example.com", password: str = "password") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    csrf_response = client.get("/auth/csrf")
    assert csrf_response.status_code == 200
    client.headers.update({"X-CSRF-Token": csrf_response.json()["csrf_token"]})


def _create_session_for_logged_in_user(client: TestClient) -> str:
    response = client.post("/api/sessions", json={})
    assert response.status_code == 201
    return response.json()["session"]["session_id"]


def _valid_lead_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Иван",
        "email": "ivan@example.com",
        "phone": "+79990000000",
        "company": "ООО Ромашка",
        "role": "Руководитель",
        "sales_team_size": "5-10",
        "consent_personal_data": True,
        "consent_marketing": False,
        "comment": "Хочу демо",
        "query_params": {},
        "page": "landing",
        "form_id": "demo",
    }
    payload.update(overrides)
    return payload


def _speech_settings(**overrides: object) -> Settings:
    temp_dir = tempfile.mkdtemp(prefix="salestrainer-stt-tests-")
    return Settings(
        auth_cookie_secure=False,
        login_rate_limit_attempts=0,
        stt_enabled=True,
        stt_backend="fake",
        stt_temp_dir=temp_dir,
        **overrides,
    )


class StubSTTClient(FakeSTTClient):
    def transcribe(self, audio_path, *, language: str) -> STTResult:
        return STTResult(text="  привет   клиенту \n\nкак дела  ", duration_ms=3450)


def test_api_session_flow() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session, role="internal_admin")
    client = _create_client(db_session, repository=repository)
    _login(client)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert "X-Request-ID" in health.headers

    scenarios = client.get("/api/scenarios")
    assert scenarios.status_code == 200
    assert len(scenarios.json()) >= 1

    personas = client.get("/api/personas")
    assert personas.status_code == 200
    assert len(personas.json()) >= 1

    create_response = client.post("/api/sessions", json={})
    assert create_response.status_code == 201
    session_payload = create_response.json()["session"]
    session_id = session_payload["session_id"]
    assert session_payload["status"] == "active"
    assert session_payload["persona_name"] == "Unknown B2B contact"
    assert session_payload["scenario_id"] == "first_contact_discovery"
    assert "public_brief" in session_payload

    resume_response = client.post(f"/api/sessions/{session_id}/resume")
    assert resume_response.status_code == 200

    detail_response = client.get(f"/api/sessions/{session_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["session"]["session_id"] == session_id
    assert detail_response.json()["turns"] == []

    turn_response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "How do you track conversion losses now?"},
    )
    assert turn_response.status_code == 200
    turn_payload = turn_response.json()
    assert turn_payload["client_answer"]
    assert turn_payload["turn_index"] == 1
    assert len(turn_payload["turns"]) == 1

    unfinished_report = client.get(f"/api/sessions/{session_id}/report")
    assert unfinished_report.status_code == 409

    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200
    assert finish_response.json()["session"]["status"] == "finished"
    assert "# Итог тренировки" in finish_response.json()["report"]

    report_response = client.get(f"/api/sessions/{session_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["session"]["status"] == "finished"

    db_session.close()


def test_api_create_session_requires_auth() -> None:
    client = _create_client()

    response = client.post("/api/sessions", json={})

    assert response.status_code == 401


def test_api_speech_transcribe_requires_auth() -> None:
    client = _create_client(settings=_speech_settings())

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.wav", BytesIO(b"fake-audio"), "audio/wav")},
    )

    assert response.status_code == 401


def test_api_speech_transcribe_rejects_authenticated_request_without_csrf() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, settings=_speech_settings())
    response = client.post("/auth/login", json={"email": "manager@example.com", "password": "password"})
    assert response.status_code == 200

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.wav", BytesIO(b"fake-audio"), "audio/wav")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Missing or invalid CSRF token."
    db_session.close()


def test_api_speech_transcribe_accepts_small_audio_and_normalizes_text() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(
        db_session,
        repository=repository,
        settings=_speech_settings(),
        stt_client=StubSTTClient(),
    )
    _login(client)
    session_id = _create_session_for_logged_in_user(client)

    response = client.post(
        "/api/speech/transcribe",
        data={"session_id": session_id},
        files={"audio": ("voice.wav", BytesIO(b"fake-audio"), "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Привет клиенту\n\nкак дела",
        "raw_text": "привет   клиенту \n\nкак дела",
        "normalized": True,
        "duration_ms": 3450,
    }
    db_session.close()


def test_api_speech_transcribe_rejects_oversized_upload() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(
        db_session,
        settings=_speech_settings(stt_max_upload_bytes=100_000),
    )
    _login(client)

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.wav", BytesIO(b"x" * 100_001), "audio/wav")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    db_session.close()


def test_api_speech_transcribe_rejects_unsupported_content_type() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, settings=_speech_settings())
    _login(client)

    response = client.post(
        "/api/speech/transcribe",
        files={"audio": ("voice.txt", BytesIO(b"not-audio"), "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    db_session.close()


def test_api_speech_transcribe_does_not_create_turns_or_mutate_session_state() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(
        db_session,
        repository=repository,
        settings=_speech_settings(),
        stt_client=StubSTTClient(),
    )
    _login(client)
    session_id = _create_session_for_logged_in_user(client)
    session_before = repository.get(session_id)
    assert session_before is not None
    session_before_json = session_before.model_dump_json()
    turns_before = db_session.query(TrainingTurnRecord).count()
    usage_events_before = db_session.query(UsageEventRecord).count()

    response = client.post(
        "/api/speech/transcribe",
        data={"session_id": session_id},
        files={"audio": ("voice.wav", BytesIO(b"fake-audio"), "audio/wav")},
    )

    session_after = repository.get(session_id)
    assert response.status_code == 200
    assert session_after is not None
    assert session_after.model_dump_json() == session_before_json
    assert db_session.query(TrainingTurnRecord).count() == turns_before
    assert db_session.query(UsageEventRecord).count() == usage_events_before
    db_session.close()


def test_api_mutating_endpoint_rejects_authenticated_request_without_csrf() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    response = client.post("/auth/login", json={"email": "manager@example.com", "password": "password"})
    assert response.status_code == 200

    response = client.post("/api/sessions", json={})

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Missing or invalid CSRF token."
    db_session.close()


def test_anonymous_cannot_get_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    owner_client = _create_client(db_session, repository=repository)
    _seed_authenticated_user(db_session)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    anonymous_client = _create_client(db_session, repository=repository)
    response = anonymous_client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 401

    db_session.close()


def test_anonymous_cannot_send_message() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    anonymous_client = _create_client(db_session, repository=repository)
    response = anonymous_client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "Hello"},
    )

    assert response.status_code == 401

    db_session.close()


def test_anonymous_cannot_finish_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    anonymous_client = _create_client(db_session, repository=repository)
    response = anonymous_client.post(f"/api/sessions/{session_id}/finish")

    assert response.status_code == 401

    db_session.close()


def test_user_cannot_read_another_users_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_user_cannot_send_message_to_another_users_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "Can we continue?"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_user_cannot_finish_another_users_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.post(f"/api/sessions/{session_id}/finish")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_user_cannot_get_another_users_report() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)
    finish_response = owner_client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.get(f"/api/sessions/{session_id}/report")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_owner_user_can_access_own_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, repository=repository)
    _login(client)
    session_id = _create_session_for_logged_in_user(client)

    response = client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 200
    assert response.json()["session"]["session_id"] == session_id

    db_session.close()


def test_owner_user_can_send_message_to_own_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, repository=repository)
    _login(client)
    session_id = _create_session_for_logged_in_user(client)

    response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "How do you handle this now?"},
    )

    assert response.status_code == 200
    assert response.json()["turn_index"] == 1


def test_api_create_session_uses_settings_default_scenario_and_creates_ownership() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    user, training_config = _seed_authenticated_user(
        db_session,
        default_scenario_id="qualification_and_authority",
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "confirm_decision_process",
        },
    )
    client = _create_client(db_session, repository=repository)
    _login(client)

    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    session_id = response.json()["session"]["session_id"]
    saved_session = repository.get(session_id)
    assert saved_session is not None
    assert saved_session.scenario_id == "first_contact_discovery"
    assert saved_session.persona.authority_level == "final_decider"
    ownership = db_session.scalar(select(TrainingSessionOwnership).where(TrainingSessionOwnership.session_id == saved_session.session_id))
    assert ownership is not None
    assert ownership.user_id == user.id
    assert ownership.client_account_id == training_config.client_account_id
    assert ownership.training_config_id == training_config.id

    db_session.close()


def test_api_create_session_uses_persona_generation_service_for_client_config() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _, training_config = _seed_authenticated_user(
        db_session,
        default_scenario_id="needs_diagnosis",
        persona_policy={"allowed_roles": ["cfo"], "target_action": "book_diagnostic_call"},
    )
    access_repository = AccessRepository(db_session)
    access_repository.update_training_config(
        training_config_id=training_config.id,
        persona_generation_context="Buyer for a cosmetics retail business with low repeat sales and poor diagnostics.",
        persona_policy={"allowed_roles": ["cfo"], "target_action": "book_diagnostic_call"},
    )
    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0),
        repository=repository,
        llm_client=FakeLLMClient(),
    )

    captured: dict[str, object] = {}

    class StubPersonaGenerationService:
        def generate_for_training_config(self, *, training_config, scenario_id):
            """Return a known generated persona so the API wiring is observable."""
            captured["persona_generation_context"] = training_config.persona_generation_context
            captured["llm_provider_config_id"] = training_config.llm_provider_config_id
            captured["scenario_id"] = scenario_id
            return PersonaProfile(
                id="llm_generated_cfo_cash_gap",
                display_name="Unknown B2B contact",
                role="cfo",
                industry="distribution",
                company_size="30-100",
                authority_level="final_decider",
                behavior_model="analytical_and_cautious",
                target_action="book_diagnostic_call",
                current_business_context="Company is growing but cash planning is unclear.",
                latent_pains=["Cash gaps are hard to forecast."],
                typical_objections=["We already track this in spreadsheets."],
                buying_motivation=["Improve financial transparency."],
                decision_criteria=["clear methodology", "similar cases"],
                hidden_constraints=["Bad experience with consultants."],
                business_facts=["Several legal entities."],
                proof_sensitivity=["cases"],
                call_scoring_criteria=["discovery"],
                communication_style="short and analytical",
                initial_openness=30,
                starting_interest=31,
                price_sensitivity=55,
                urgency=60,
                trust_baseline=28,
            )

    def override_get_db_session() -> Generator[Session, None, None]:
        """Share the in-memory database with the tested FastAPI app."""
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_persona_generation_service] = lambda: StubPersonaGenerationService()
    client = TestClient(app, raise_server_exceptions=False)
    _login(client)

    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    session_id = response.json()["session"]["session_id"]
    saved_session = repository.get(session_id)
    assert saved_session is not None
    assert saved_session.persona.id == "llm_generated_cfo_cash_gap"
    assert saved_session.persona.role == "cfo"
    assert saved_session.interest_score == 31
    assert captured["persona_generation_context"] == "Buyer for a cosmetics retail business with low repeat sales and poor diagnostics."
    assert captured["llm_provider_config_id"] is None
    assert captured["scenario_id"] is None
    assert "llm_generated_cfo_cash_gap" not in response.text

    db_session.close()


def test_api_leads_persist_whitelisted_query_params_and_honeypot() -> None:
    db_session = _create_db_session()
    client = _create_client(db_session)

    response = client.post(
        "/api/leads",
        json={
            "name": "Иван",
            "email": "ivan@example.com",
            "phone": "+79990000000",
            "company": "ООО Ромашка",
            "role": "Руководитель",
            "sales_team_size": "5-10",
            "consent_personal_data": True,
            "consent_marketing": False,
            "comment": "Хочу демо",
            "query_params": {"utm_source": "direct", "unknown": "drop"},
            "page": "landing",
            "form_id": "demo",
            "website": "bot-filled",
        },
    )
    lead = db_session.scalar(select(LandingLead))

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert lead is not None
    assert lead.email == "ivan@example.com"
    assert lead.query_params == {"utm_source": "direct"}
    assert lead.is_spam is True

    db_session.close()


def test_api_leads_accepts_valid_payload_and_creates_row() -> None:
    db_session = _create_db_session()
    client = _create_client(db_session)

    response = client.post("/api/leads", json=_valid_lead_payload())
    lead = db_session.scalar(select(LandingLead))

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert lead is not None
    assert lead.email == "ivan@example.com"
    assert lead.consent_personal_data is True
    assert lead.is_spam is False

    db_session.close()


def test_api_leads_rejects_invalid_email() -> None:
    db_session = _create_db_session()
    client = _create_client(db_session)

    response = client.post("/api/leads", json=_valid_lead_payload(email="not-an-email"))

    assert response.status_code == 422
    assert db_session.scalar(select(LandingLead)) is None

    db_session.close()


def test_api_leads_rejects_missing_or_false_personal_data_consent() -> None:
    db_session = _create_db_session()
    client = _create_client(db_session)

    missing_payload = _valid_lead_payload()
    missing_payload.pop("consent_personal_data")
    missing_response = client.post("/api/leads", json=missing_payload)
    false_response = client.post("/api/leads", json=_valid_lead_payload(consent_personal_data=False))

    assert missing_response.status_code == 422
    assert false_response.status_code == 422
    assert db_session.scalar(select(LandingLead)) is None

    db_session.close()


def test_api_leads_keeps_whitelisted_query_params_and_truncates_values() -> None:
    db_session = _create_db_session()
    client = _create_client(db_session)
    long_value = "x" * 350

    response = client.post(
        "/api/leads",
        json=_valid_lead_payload(
            query_params={
                "utm_source": long_value,
                "utm_medium": "cpc",
                "utm_campaign": "spring",
                "utm_content": "hero",
                "utm_term": "sales trainer",
                "ref": "partner",
                "unknown": "drop",
            }
        ),
    )
    lead = db_session.scalar(select(LandingLead))

    assert response.status_code == 202
    assert lead is not None
    assert lead.query_params == {
        "utm_source": long_value[:300],
        "utm_medium": "cpc",
        "utm_campaign": "spring",
        "utm_content": "hero",
        "utm_term": "sales trainer",
        "ref": "partner",
    }

    db_session.close()


def test_api_create_session_compensates_runtime_and_ownership_when_history_fails() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0),
        repository=repository,
        llm_client=FakeLLMClient(),
    )

    class FailingHistoryService:
        def record_session_started(self, **_: object) -> None:
            """Simulate a persistent history outage after runtime creation."""
            raise RuntimeError("history down")

    def override_get_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    from app.history.dependencies import get_history_service

    app.dependency_overrides[get_history_service] = lambda: FailingHistoryService()
    client = TestClient(app, raise_server_exceptions=False)
    _login(client)

    response = client.post("/api/sessions", json={})
    ownership_count = db_session.scalar(select(TrainingSessionOwnership))

    assert response.status_code == 500
    assert repository._store == {}
    assert ownership_count is None

    db_session.close()


def test_api_personas_forbidden_for_client_user() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/personas")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"

    db_session.close()


def test_api_personas_allowed_for_internal_admin() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session, role="internal_admin")
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/personas")

    assert response.status_code == 200
    assert len(response.json()) >= 1

    db_session.close()


def test_api_scenarios_for_client_user_returns_settings_default_scenario() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(
        db_session,
        default_scenario_id="qualification_and_authority",
    )
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    assert [scenario["scenario_id"] for scenario in response.json()] == ["first_contact_discovery"]

    db_session.close()


def test_api_scenarios_for_client_user_ignores_ui_allowed_scenarios() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(
        db_session,
        default_scenario_id="qualification_and_authority",
        ui_config={
            "allowed_scenarios": [
                "qualification_and_authority",
                "objection_handling",
            ]
        },
    )
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    assert [scenario["scenario_id"] for scenario in response.json()] == ["first_contact_discovery"]

    db_session.close()


def test_api_create_session_rejects_request_persona_id_in_client_auth_mode() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(
        db_session,
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "book_intro_call",
        },
    )
    client = _create_client(db_session, repository=repository)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"persona_id": "purchase_manager"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "persona_id is not allowed for client sessions."

    db_session.close()


def test_api_create_session_allows_request_persona_id_for_internal_admin() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(
        db_session,
        role="internal_admin",
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "book_intro_call",
        },
    )
    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0),
        repository=repository,
        llm_client=FakeLLMClient(),
    )

    class FailingPersonaGenerationService:
        def generate_for_training_config(self, **_: object) -> PersonaProfile:
            """Fail the test if debug preset sessions call persona generation."""
            raise AssertionError("persona generation must not run for internal admin persona_id sessions")

    def override_get_db_session() -> Generator[Session, None, None]:
        """Share the in-memory database with the tested FastAPI app."""
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_persona_generation_service] = lambda: FailingPersonaGenerationService()
    client = TestClient(app)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"scenario_id": "objection_handling", "persona_id": "purchase_manager"},
    )

    assert response.status_code == 201
    session_id = response.json()["session"]["session_id"]
    saved_session = repository.get(session_id)
    assert saved_session is not None
    assert saved_session.persona.id == "purchase_manager"
    assert saved_session.scenario_id == "objection_handling"

    db_session.close()


def test_api_internal_admin_persona_id_without_default_config_returns_clear_error() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    identity_repository = IdentityRepository(db_session)
    client_account = identity_repository.create_client_account(name="Platform", slug="platform-debug")
    identity_repository.create_user(
        client_account_id=client_account.id,
        email="admin@example.com",
        password_hash=hash_password("password"),
        role="internal_admin",
        must_change_password=False,
    )
    client = _create_client(db_session, repository=repository)
    _login(client, email="admin@example.com")

    response = client.post("/api/sessions", json={"persona_id": "owner"})

    assert response.status_code == 404
    assert (
        response.json()["error"]["message"]
        == "Default training config is required for internal admin debug sessions."
    )
    assert repository._store == {}

    db_session.close()


def test_api_returns_404_for_missing_session() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/sessions/missing-session")
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Session not found.",
            "request_id": response.headers["X-Request-ID"],
            "details": [],
        }
    }

    db_session.close()


def test_api_returns_openapi_friendly_validation_error_shape() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"persona_id": 123},
    )
    assert response.status_code == 422
    payload = response.json()
    assert "X-Request-ID" in response.headers
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed."
    assert payload["error"]["request_id"] == response.headers["X-Request-ID"]
    assert payload["error"]["details"]

    db_session.close()


def test_api_preserves_incoming_request_id() -> None:
    client = _create_client()

    response = client.get("/api/health", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"


def test_api_create_session_returns_controlled_404_for_unknown_scenario() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"scenario_id": "missing-scenario"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "Unknown scenario_id 'missing-scenario'." == payload["error"]["message"]

    db_session.close()


def test_api_finished_session_returns_conflict_for_message_and_resume() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    create_response = client.post("/api/sessions", json={})
    session_id = create_response.json()["session"]["session_id"]

    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200

    message_response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "Can we continue?"},
    )
    assert message_response.status_code == 409
    assert message_response.json()["error"]["code"] == "conflict"

    resume_response = client.post(f"/api/sessions/{session_id}/resume")
    assert resume_response.status_code == 409
    assert resume_response.json()["error"]["code"] == "conflict"

    db_session.close()


def test_api_session_detail_returns_full_turn_history_beyond_recent_turn_limit() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    app = create_app(
        settings=Settings(auth_cookie_secure=False, login_rate_limit_attempts=0, recent_turn_limit=2),
        repository=repository,
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app)
    _login(client)

    create_response = client.post("/api/sessions", json={})
    session_id = create_response.json()["session"]["session_id"]

    for message in [
        "How do you track conversion losses now?",
        "What does your funnel look like by stage?",
        "Where do deals drop most often?",
    ]:
        response = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"manager_message": message},
        )
        assert response.status_code == 200

    saved_session = repository.get(session_id)
    assert saved_session is not None
    assert len(saved_session.recent_turns) == 2
    assert len(saved_session.turns) == 3

    detail_response = client.get(f"/api/sessions/{session_id}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["turns"]) == 3

    db_session.close()


def test_api_report_reveals_hidden_profile_only_after_finish() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, repository=repository)
    _login(client)

    create_response = client.post("/api/sessions", json={})
    session_id = create_response.json()["session"]["session_id"]
    detail_before = client.get(f"/api/sessions/{session_id}")
    assert "# Кто был клиент" not in detail_before.text

    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200
    assert "# Кто был клиент" in finish_response.json()["report"]

    db_session.close()
