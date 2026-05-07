from __future__ import annotations

from app.domain.judgement_models import JudgeSessionOutput, build_judge_input_from_session
from app.domain.models import TrainingSessionState
from app.infrastructure.judge_client import JudgeClient


class JudgementService:
    def __init__(self, judge_client: JudgeClient) -> None:
        """Keep the judge client that evaluates finished sessions."""
        self._judge_client = judge_client

    def judge_session(self, session: TrainingSessionState) -> JudgeSessionOutput:
        """Build the domain payload from session state and delegate judgement to the client."""
        input_payload = build_judge_input_from_session(session)
        return self._judge_client.judge_session(input_payload)
