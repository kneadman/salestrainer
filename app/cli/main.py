from __future__ import annotations

import logging
from typing import Callable

from app.application.report_service import ReportService
from app.application.session_service import TrainingSessionService
from app.application.turn_service import TurnService
from app.cli.renderer import (
    render_debug_block,
    render_help,
    render_history,
    render_scenarios,
    render_state,
)
from app.domain.errors import SalesTrainerError
from app.infrastructure.config import get_settings
from app.infrastructure.llm_client import build_llm_client
from app.infrastructure.logging import setup_logging
from app.infrastructure.redis_client import build_repository
from app.infrastructure.summary_compressor import build_summary_compressor

logger = logging.getLogger(__name__)


def parse_command_with_arg(raw: str) -> tuple[str, str]:
    command, _, argument = raw.partition(" ")
    return command, argument.strip()


def start_flow(
    session_service: TrainingSessionService,
    output_fn: Callable[[str], None],
) -> str:
    session = session_service.start_session()
    output_fn("Session created.")
    output_fn(f"Situation: {session.public_brief}")
    output_fn(f"Starting interest: {session.interest_score}/100.")
    output_fn(render_state(session))
    output_fn("Type your message or use /help.")
    return str(session.session_id)


def resume_flow(
    session_service: TrainingSessionService,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
    session_id: str | None = None,
) -> str:
    target_session_id = session_id or input_fn("Session ID: ").strip()
    session = session_service.resume_session(target_session_id)
    output_fn("Session resumed.")
    output_fn(render_state(session))
    output_fn("Continue the dialogue or use /help.")
    return str(session.session_id)


def run_cli(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    repository = build_repository(settings)
    session_service = TrainingSessionService(
        repository,
        default_scenario_id=settings.default_training_scenario_id,
    )
    turn_service = TurnService(
        repository,
        build_llm_client(settings),
        recent_turn_limit=settings.recent_turn_limit,
        debug_mode=settings.debug_cli,
        summary_compressor=build_summary_compressor(settings),
    )
    report_service = ReportService(repository)

    output_fn("Sales Trainer MVP")
    output_fn(render_help())
    output_fn("Use /start to create a session or /resume <session_id> to continue one.")
    current_session_id: str | None = None

    while True:
        try:
            raw = input_fn("You: ").strip()
        except EOFError:
            logger.info("cli_eof_exit")
            break
        if not raw:
            continue
        command, argument = parse_command_with_arg(raw)
        if command == "/exit":
            break
        if command == "/help":
            output_fn(render_help())
            continue
        if command == "/start":
            current_session_id = start_flow(session_service, output_fn)
            continue
        if command == "/resume":
            try:
                current_session_id = resume_flow(session_service, input_fn, output_fn, argument or None)
            except SalesTrainerError as error:
                output_fn(f"Error: {error}")
                logger.warning("cli_resume_error error=%s", error)
            continue
        if command == "/scenarios":
            output_fn(render_scenarios())
            continue
        if current_session_id is None:
            if command.startswith("/"):
                output_fn("Unknown command. Use /help.")
                continue
            output_fn("No active session. Use /start or /resume <session_id>.")
            continue
        if command == "/state":
            session = session_service.get_session(current_session_id)
            if session is not None:
                output_fn(render_state(session))
            continue
        if command == "/history":
            session = session_service.get_session(current_session_id)
            if session is not None:
                output_fn(render_history(session))
            continue
        if command == "/finish":
            try:
                output_fn(report_service.finish_session(current_session_id))
                current_session_id = None
            except SalesTrainerError as error:
                output_fn(f"Error: {error}")
                logger.warning("cli_finish_error error=%s", error)
            continue
        if command.startswith("/"):
            output_fn("Unknown command. Use /help.")
            continue
        try:
            result = turn_service.process_message(current_session_id, raw)
        except SalesTrainerError as error:
            output_fn(f"Error: {error}")
            logger.warning("cli_turn_error error=%s", error)
            continue
        output_fn(f"Client: {result.client_answer}")
        output_fn(
            f"Interest: {result.interest_before} -> {result.interest_after} ({result.interest_delta:+d})"
        )
        output_fn(f"Stage: {result.stage_after}")
        if settings.debug_cli:
            output_fn(render_debug_block("LLM payload", result.llm_payload))
            output_fn(render_debug_block("LLM response", result.llm_response))


def main() -> None:
    run_cli()


if __name__ == "__main__":
    main()
