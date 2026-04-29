from __future__ import annotations

from collections import deque

from app.application.session_service import TrainingSessionService
from app.cli.main import run_cli
from app.infrastructure.config import Settings
from app.infrastructure.session_repository import InMemorySessionRepository


def test_cli_resume_existing_session(monkeypatch) -> None:
    repository = InMemorySessionRepository()
    session_service = TrainingSessionService(repository)
    session = session_service.start_session("sales_audit_cold_outreach", "owner")
    inputs = deque(
        [
            f"/resume {session.session_id}",
            "/state",
            "/exit",
        ]
    )
    outputs: list[str] = []

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        if not inputs:
            raise EOFError
        return inputs.popleft()

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings(llm_backend="fake"))
    monkeypatch.setattr("app.cli.main.build_repository", lambda settings: repository)
    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Session resumed." in joined
    assert str(session.session_id) in joined


def test_cli_resume_missing_session_shows_error(monkeypatch) -> None:
    inputs = deque(["/resume missing-session", "/exit"])
    outputs: list[str] = []

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        if not inputs:
            raise EOFError
        return inputs.popleft()

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings(llm_backend="fake"))
    monkeypatch.setattr("app.cli.main.build_repository", lambda settings: InMemorySessionRepository())
    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Error:" in joined
    assert "not found" in joined
