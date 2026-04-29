from __future__ import annotations

from typing import Protocol

from app.domain.interest import interest_band
from app.domain.models import TrainingSessionState, Turn


class SummaryCompressor(Protocol):
    def compress(
        self,
        *,
        existing_summary: str,
        overflow_turns: list[Turn],
        session: TrainingSessionState,
        latest_internal_notes: str,
    ) -> str:
        ...


class FakeSummaryCompressor:
    def compress(
        self,
        *,
        existing_summary: str,
        overflow_turns: list[Turn],
        session: TrainingSessionState,
        latest_internal_notes: str,
    ) -> str:
        chunks: list[str] = []
        base_summary = existing_summary.strip()
        if base_summary:
            chunks.append(base_summary)
        for turn in overflow_turns:
            chunks.append(
                f"T{turn.index}: manager='{turn.manager_message[:80]}' "
                f"client='{turn.client_answer[:80]}' "
                f"interest={turn.interest_before}->{turn.interest_after} "
                f"stage={turn.stage_before}->{turn.stage_after}"
            )
        notes = latest_internal_notes.strip()
        if notes:
            chunks.append(f"Notes: {notes[:160]}")
        chunks.append(
            f"Current state: interest={session.interest_score}/100 ({interest_band(session.interest_score)}), "
            f"stage={session.stage}, "
            f"objections={', '.join(session.client_state.open_objections) or 'none'}, "
            f"signals={', '.join(session.client_state.buying_signals) or 'none'}"
        )
        return " | ".join(chunks)[-1000:]
