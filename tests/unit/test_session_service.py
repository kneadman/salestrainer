import pytest

from app.application.session_service import TrainingSessionService
from app.domain.errors import SessionNotFoundError
from app.domain.persona_generation import PersonaGenerator
from app.infrastructure.session_repository import InMemorySessionRepository


def test_resume_session_returns_active_session() -> None:
    repository = InMemorySessionRepository()
    service = TrainingSessionService(repository)
    session = service.start_session("sales_audit_cold_outreach", "owner")

    resumed = service.resume_session(str(session.session_id))

    assert resumed.session_id == session.session_id
    assert resumed.status == "active"


def test_resume_session_rejects_missing_session() -> None:
    repository = InMemorySessionRepository()
    service = TrainingSessionService(repository)

    with pytest.raises(SessionNotFoundError, match="not found"):
        service.resume_session("missing-session-id")


def test_start_session_without_persona_uses_generated_profile() -> None:
    repository = InMemorySessionRepository()
    service = TrainingSessionService(
        repository,
        persona_generator=PersonaGenerator(seed=7),
    )

    session = service.start_session()

    assert session.scenario_id == "generic_b2b_first_contact"
    assert session.persona.id.startswith("generated_")
    assert session.public_brief


def test_generated_persona_is_deterministic_with_fixed_seed() -> None:
    first = TrainingSessionService(
        InMemorySessionRepository(),
        persona_generator=PersonaGenerator(seed=11),
    ).start_session()
    second = TrainingSessionService(
        InMemorySessionRepository(),
        persona_generator=PersonaGenerator(seed=11),
    ).start_session()

    assert first.persona.role == second.persona.role
    assert first.persona.latent_pains == second.persona.latent_pains


def test_generated_personas_without_seed_can_vary() -> None:
    service = TrainingSessionService(InMemorySessionRepository())
    roles = {service.start_session().persona.role for _ in range(10)}
    assert len(roles) > 1
