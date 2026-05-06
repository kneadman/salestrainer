import json

import pytest

from app.domain.errors import LLMProviderConfigurationError
from app.domain.judgement_models import JudgeSessionInput, JudgeSessionOutput
from app.domain.models import ClientState, PersonaProfile, Scenario, TurnEvaluation
from app.infrastructure.config import Settings
from app.infrastructure.judge_client import (
    FakeJudgeClient,
    StructuredJudgeClient,
    build_judge_client,
    parse_judge_session_output,
)


def _build_payload(*, heuristic: bool = True) -> JudgeSessionInput:
    """Create a compact judge input payload for fake client tests."""
    evaluations = []
    if heuristic:
        evaluations = [
            TurnEvaluation(
                turn_index=1,
                discovery_quality_score=4,
                role_identification_score=3,
                pain_identification_score=4,
                relevance_score=4,
                pressure_score=5,
                objection_handling_score=3,
                next_step_timing_score=4,
                conversation_control_score=4,
                notes=["Solid first turn."],
            )
        ]
    return JudgeSessionInput(
        scenario=Scenario(
            id="first_contact_discovery",
            name="Discovery",
            training_format="first_contact_discovery",
            default_starting_interest=25,
            default_stage="first_contact",
            manager_goal="Discover context.",
            success_condition="Earn a relevant next step.",
            failure_condition="Pitch too early.",
        ),
        persona=PersonaProfile(
            id="persona-1",
            display_name="Owner",
            role="owner",
            industry="b2b",
            company_size="30-100",
            authority_level="final_decider",
            behavior_model="skeptical_but_rational",
        ),
        final_client_state=ClientState(
            tone="interested",
            trust=45,
            irritation=10,
            urgency=25,
            price_sensitivity=50,
        ),
        conversation_summary="Manager discovered pain and moved the discussion forward.",
        turns=[
            {
                "turn_index": 1,
                "manager_message": "How does reporting work today?",
                "client_answer": "Mostly manually.",
                "interest_before": 25,
                "interest_delta": 5,
                "interest_after": 30,
                "stage_before": "first_contact",
                "stage_after": "qualification",
            },
            {
                "turn_index": 2,
                "manager_message": "Where does it slow you down most?",
                "client_answer": "At month end.",
                "interest_before": 30,
                "interest_delta": 8,
                "interest_after": 38,
                "stage_before": "qualification",
                "stage_after": "needs_analysis",
            },
        ],
        heuristic_evaluations=evaluations,
        final_interest_score=38,
        final_stage="needs_analysis",
        turn_count=2,
    )


def test_fake_judge_client_returns_judge_session_output() -> None:
    """Fake judge client should return the strict domain output model."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert isinstance(result, JudgeSessionOutput)


def test_fake_judge_client_keeps_overall_score_in_range() -> None:
    """Overall fake score should stay within the normalized 0..100 range."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert 0 <= result.overall_score <= 100


def test_fake_judge_client_maps_grade_from_score() -> None:
    """Overall grade should match the configured score bands."""
    result = FakeJudgeClient().judge_session(_build_payload(heuristic=False))

    assert result.overall_score == 38
    assert result.overall_grade == "weak"


def test_fake_judge_client_returns_non_empty_bento_blocks() -> None:
    """Fake judge client should always emit the minimum bento block set."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert result.bento_blocks


def test_fake_judge_client_returns_skill_scores_when_heuristics_exist() -> None:
    """Skill scores should be derived from heuristic evaluations when present."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert result.skill_scores


def test_fake_judge_client_uses_one_based_evidence_indexes() -> None:
    """Evidence indexes should remain one-based and point only to existing turns."""
    result = FakeJudgeClient().judge_session(_build_payload())

    existing_indexes = {1, 2}
    for block in result.bento_blocks:
        assert all(index >= 1 for index in block.evidence_turn_indexes)
        assert set(block.evidence_turn_indexes).issubset(existing_indexes)


def test_parse_judge_session_output_accepts_direct_output_dict() -> None:
    """Parser should accept a direct JudgeSessionOutput-like dictionary."""
    result = parse_judge_session_output(
        {
            "schema_version": 1,
            "overall_score": 80,
            "overall_grade": "good",
            "outcome": "Outcome",
            "executive_summary": "Summary",
            "bento_blocks": [],
            "skill_scores": [],
            "final_verdict": "Verdict",
        }
    )

    assert isinstance(result, JudgeSessionOutput)
    assert result.overall_score == 80


def test_parse_judge_session_output_accepts_output_text_json() -> None:
    """Parser should extract JSON from provider output_text envelopes."""
    result = parse_judge_session_output(
        {
            "output_text": json.dumps(
                {
                    "schema_version": 1,
                    "overall_score": 61,
                    "overall_grade": "normal",
                    "outcome": "Outcome",
                    "executive_summary": "Summary",
                    "bento_blocks": [],
                    "skill_scores": [],
                    "final_verdict": "Verdict",
                }
            )
        }
    )

    assert result.overall_grade == "normal"


def test_structured_judge_client_builds_request_with_json_schema_name() -> None:
    """Structured client should request strict JSON schema output with the expected name."""
    captured_requests: list[dict[str, object]] = []

    def transport(request_payload):
        captured_requests.append(request_payload)
        return {
            "schema_version": 1,
            "overall_score": 70,
            "overall_grade": "normal",
            "outcome": "Outcome",
            "executive_summary": "Summary",
            "bento_blocks": [],
            "skill_scores": [],
            "final_verdict": "Verdict",
        }

    client = StructuredJudgeClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret-key-value",
        folder_id="folder-1",
        agent_id="agent-1",
        transport=transport,
    )

    client.judge_session(_build_payload())

    assert captured_requests
    assert captured_requests[0]["text"]["format"]["name"] == "judge_session_output"
    assert captured_requests[0]["text"]["format"]["strict"] is True


def test_structured_judge_client_returns_output_on_successful_transport() -> None:
    """Structured client should validate and return JudgeSessionOutput on success."""
    client = StructuredJudgeClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret-key-value",
        folder_id="folder-1",
        agent_id="agent-1",
        transport=lambda _: {
            "schema_version": 1,
            "overall_score": 88,
            "overall_grade": "strong",
            "outcome": "Outcome",
            "executive_summary": "Summary",
            "bento_blocks": [],
            "skill_scores": [],
            "final_verdict": "Verdict",
        },
    )

    result = client.judge_session(_build_payload())

    assert isinstance(result, JudgeSessionOutput)
    assert result.overall_grade == "strong"


def test_structured_judge_client_retries_with_retry_instruction() -> None:
    """Structured client should add retry_instruction after the first invalid response."""
    captured_requests: list[dict[str, object]] = []
    responses = iter(
        [
            {"output_text": "not json"},
            {
                "output_text": json.dumps(
                    {
                        "schema_version": 1,
                        "overall_score": 63,
                        "overall_grade": "normal",
                        "outcome": "Outcome",
                        "executive_summary": "Summary",
                        "bento_blocks": [],
                        "skill_scores": [],
                        "final_verdict": "Verdict",
                    }
                )
            },
        ]
    )

    def transport(request_payload):
        captured_requests.append(request_payload)
        return next(responses)

    client = StructuredJudgeClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret-key-value",
        folder_id="folder-1",
        agent_id="agent-1",
        max_retries=1,
        transport=transport,
    )

    result = client.judge_session(_build_payload())

    second_input = json.loads(captured_requests[1]["input"])
    assert result.overall_score == 63
    assert "retry_instruction" in second_input


def test_structured_judge_client_falls_back_to_fake_after_invalid_provider_output() -> None:
    """Structured client should use fallback client after provider retries are exhausted."""
    client = StructuredJudgeClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret-key-value",
        folder_id="folder-1",
        agent_id="agent-1",
        max_retries=0,
        fallback_client=FakeJudgeClient(),
        transport=lambda _: {"output_text": "not json"},
    )

    result = client.judge_session(_build_payload())

    assert isinstance(result, JudgeSessionOutput)
    assert 0 <= result.overall_score <= 100


def test_build_judge_client_uses_judge_specific_folder_and_agent_ids() -> None:
    """Judge factory should prefer dedicated judge routing values when present."""
    client = build_judge_client(
        Settings(
            llm_backend="yandex_compatible",
            app_env="prod",
            allow_fake_llm_fallback=False,
            yandex_api_key="secret-key-value",
            yandex_judge_folder_id="judge-folder",
            yandex_judge_agent_id="judge-agent",
        )
    )

    assert isinstance(client, StructuredJudgeClient)
    assert client._folder_id == "judge-folder"
    assert client._agent_id == "judge-agent"


def test_build_judge_client_falls_back_to_legacy_folder_and_agent_ids() -> None:
    """Judge factory should reuse legacy Yandex routing values when judge-specific ones are empty."""
    client = build_judge_client(
        Settings(
            llm_backend="yandex_compatible",
            app_env="prod",
            allow_fake_llm_fallback=False,
            yandex_api_key="secret-key-value",
            yandex_folder_id="legacy-folder",
            yandex_agent_id="legacy-agent",
        )
    )

    assert isinstance(client, StructuredJudgeClient)
    assert client._folder_id == "legacy-folder"
    assert client._agent_id == "legacy-agent"


def test_build_judge_client_raises_for_incomplete_yandex_config_when_fallback_disabled() -> None:
    """Judge factory should fail closed in non-local mode when Yandex config is incomplete."""
    with pytest.raises(LLMProviderConfigurationError):
        build_judge_client(
            Settings(
                llm_backend="yandex_compatible",
                app_env="prod",
                allow_fake_llm_fallback=False,
                yandex_api_key="secret-key-value",
                yandex_folder_id="",
                yandex_agent_id="",
                yandex_judge_folder_id="judge-folder",
                yandex_judge_agent_id="",
            )
        )


def test_structured_judge_client_metadata_masks_api_key() -> None:
    """Safe request metadata must never expose the raw API key."""
    client = StructuredJudgeClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret-key-value",
        folder_id="folder-1",
        agent_id="agent-1",
        transport=lambda _: {},
    )

    metadata = client._safe_request_metadata(
        attempt=1,
        request_payload={"input": "{}", "text": {"format": {"name": "judge_session_output"}}},
    )

    assert metadata["api_key"] != "secret-key-value"
    assert "secret-key-value" not in json.dumps(metadata)
