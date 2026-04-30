from __future__ import annotations

from collections import deque

from app.cli.main import run_cli
from app.infrastructure.config import Settings


def test_cli_smoke_flow(monkeypatch) -> None:
    inputs = deque(
        [
            "/start",
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

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings(llm_backend="fake"))
    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Sales Trainer MVP" in joined
    assert "Use /start to create a session or /resume <session_id> to continue one." in joined
    assert "Available scenarios:" in joined
    assert "Session created." in joined
    assert "Situation:" in joined
    assert "Client:" in joined
    assert "Recent turns:" in joined
    assert "Итог тренировки" in joined
    assert "Persona:" not in joined


def test_cli_help_outputs_commands(monkeypatch) -> None:
    inputs = deque(["/help", "/exit"])
    outputs: list[str] = []

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        if not inputs:
            raise EOFError
        return inputs.popleft()

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings(llm_backend="fake"))
    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Commands:" in joined
    assert "/start" in joined
    assert "/help" in joined


def test_cli_finish_handles_missing_session_without_traceback(monkeypatch) -> None:
    inputs = deque(["/start", "/finish", "/exit"])
    outputs: list[str] = []

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        if not inputs:
            raise EOFError
        return inputs.popleft()

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings(llm_backend="fake"))

    def fake_build_repository(settings):
        class BrokenRepository:
            def get(self, session_id: str):
                return None

            def create(self, session):
                return None

            def save(self, session, *, expected_version=None):
                return None

            def delete(self, session_id: str):
                return None

        return BrokenRepository()

    monkeypatch.setattr("app.cli.main.build_repository", fake_build_repository)

    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Error:" in joined
    assert "not found" in joined


def test_cli_unknown_slash_command_does_not_go_to_llm(monkeypatch) -> None:
    inputs = deque(["/start", "/unknown", "/exit"])
    outputs: list[str] = []

    class FailingLLMClient:
        def generate_client_turn(self, payload):
            raise AssertionError("Unknown slash command must not be sent to LLM.")

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        if not inputs:
            raise EOFError
        return inputs.popleft()

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("app.cli.main.get_settings", lambda: Settings(llm_backend="fake"))
    monkeypatch.setattr("app.cli.main.build_llm_client", lambda settings: FailingLLMClient())
    run_cli(input_fn=fake_input, output_fn=fake_output)

    joined = "\n".join(outputs)
    assert "Unknown command. Use /help." in joined


def test_cli_passes_persona_random_seed_to_persona_generator(monkeypatch) -> None:
    inputs = deque(["/exit"])
    outputs: list[str] = []
    captured_seeds: list[int | None] = []

    class RecordingPersonaGenerator:
        def __init__(self, seed=None) -> None:
            captured_seeds.append(seed)

    def fake_input(prompt: str) -> str:
        outputs.append(prompt)
        if not inputs:
            raise EOFError
        return inputs.popleft()

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr(
        "app.cli.main.get_settings",
        lambda: Settings(llm_backend="fake", persona_random_seed=123),
    )
    monkeypatch.setattr("app.cli.main.PersonaGenerator", RecordingPersonaGenerator)

    run_cli(input_fn=fake_input, output_fn=fake_output)

    assert captured_seeds == [123]
