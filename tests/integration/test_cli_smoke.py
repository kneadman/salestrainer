from __future__ import annotations

from collections import deque

from app.cli.main import run_cli
from app.infrastructure.config import Settings


def test_cli_smoke_flow(monkeypatch) -> None:
    inputs = deque(
        [
            "/start",
            "1",
            "1",
            "/scenarios",
            "We start with a diagnostic of conversion losses. How do you track drop-off now?",
            "/state",
            "/history",
            "/finish",
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

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings())
    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Sales Trainer MVP" in joined
    assert "Use /start to create a session or /resume <session_id> to continue one." in joined
    assert "Available scenarios:" in joined
    assert "Session created." in joined
    assert "Client:" in joined
    assert "Recent turns:" in joined
    assert "Final interest:" in joined


def test_cli_finish_handles_missing_session_without_traceback(monkeypatch) -> None:
    inputs = deque(["/start", "1", "1", "/finish", "/exit"])
    outputs: list[str] = []

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        if not inputs:
            raise EOFError
        return inputs.popleft()

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings())

    def fake_build_repository(settings):
        class BrokenRepository:
            def get(self, session_id: str):
                return None

            def create(self, session):
                return None

            def save(self, session):
                return None

            def delete(self, session_id: str):
                return None

        return BrokenRepository()

    monkeypatch.setattr("app.cli.main.build_repository", fake_build_repository)

    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Error:" in joined
    assert "not found" in joined
