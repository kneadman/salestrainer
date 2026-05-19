import json

import pytest

from app.domain.errors import LLMProviderConfigurationError
from app.domain.judgement_models import JudgeSessionInput, JudgeSessionOutput
from app.domain.models import ClientState, PersonaProfile, Scenario, TurnEvaluation
from tests.unit._persona_fixtures import valid_minimal_persona
from app.infrastructure.config import Settings
from app.infrastructure.judge_client import (
    FakeJudgeClient,
    JudgeOutputValidationError,
    StructuredJudgeClient,
    build_judge_client,
    parse_judge_session_output,
    validate_judge_output,
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
        persona=valid_minimal_persona(
            id="persona-1",
            display_name="Owner",
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


def _valid_output_dict(
    *,
    bento_evidence: list[int] | None = None,
    skill_evidence: list[int] | None = None,
    finding_evidence: list[int] | None = None,
) -> dict[str, object]:
    """Build one minimal valid structured judge output payload for parser tests."""
    return {
        "schema_version": 1,
        "overall_score": 80,
        "overall_grade": "good",
        "outcome": "Итог сессии хороший.",
        "executive_summary": "Менеджер провёл содержательный разговор и довёл его до понятного этапа.",
        "bento_blocks": [
            {
                "id": "summary",
                "title": "Итог",
                "type": "summary",
                "severity": "neutral",
                "short_text": "Краткий итог.",
                "detail": "Подробный итог завершённой тренировки.",
                "evidence_turn_indexes": bento_evidence if bento_evidence is not None else [1],
            }
        ],
        "skill_scores": [
            {
                "id": "discovery_quality",
                "title": "Discovery quality",
                "score": 80,
                "severity": "green",
                "explanation": "Навык проявлен на хорошем уровне.",
                "evidence_turn_indexes": skill_evidence if skill_evidence is not None else [1],
            }
        ],
        "key_strengths": [
            {
                "title": "Сильная диагностика",
                "description": "Менеджер задавал вопросы по контексту клиента.",
                "evidence_turn_indexes": finding_evidence if finding_evidence is not None else [1],
                "impact": "medium",
            }
        ],
        "key_weaknesses": [],
        "missed_opportunities": [],
        "recommendations": [
            {
                "title": "Уточнить следующий шаг",
                "description": "Добавить больше конкретики перед предложением следующего шага.",
                "example_phrase": "Что для вас было бы следующим логичным шагом после этой диагностики?",
                "priority": "medium",
            }
        ],
        "final_verdict": "Хорошая сессия с понятной зоной для следующего улучшения.",
        "risk_flags": [],
    }


def test_fake_judge_client_returns_judge_session_output() -> None:
    """Fake judge client should return the strict domain output model."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert isinstance(result.value, JudgeSessionOutput)


def test_fake_judge_client_keeps_overall_score_in_range() -> None:
    """Overall fake score should stay within the normalized 0..100 range."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert 0 <= result.value.overall_score <= 100


def test_fake_judge_client_maps_grade_from_score() -> None:
    """Overall grade should match the configured score bands."""
    result = FakeJudgeClient().judge_session(_build_payload(heuristic=False))

    assert result.value.overall_score == 38
    assert result.value.overall_grade == "weak"


def test_fake_judge_client_returns_non_empty_bento_blocks() -> None:
    """Fake judge client should always emit the minimum bento block set."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert result.value.bento_blocks


def test_fake_judge_client_returns_skill_scores_when_heuristics_exist() -> None:
    """Skill scores should be derived from heuristic evaluations when present."""
    result = FakeJudgeClient().judge_session(_build_payload())

    assert result.value.skill_scores


def test_fake_judge_client_uses_one_based_evidence_indexes() -> None:
    """Evidence indexes should remain one-based and point only to existing turns."""
    result = FakeJudgeClient().judge_session(_build_payload())

    existing_indexes = {1, 2}
    for block in result.value.bento_blocks:
        assert all(index >= 1 for index in block.evidence_turn_indexes)
        assert set(block.evidence_turn_indexes).issubset(existing_indexes)


def test_fake_judge_client_uses_russian_user_facing_text() -> None:
    """Fake judge text should stay Russian for the default Russian runtime contract."""
    result = FakeJudgeClient().judge_session(_build_payload())

    combined_text = " ".join(
        [
            result.value.outcome,
            result.value.executive_summary,
            result.value.final_verdict,
            *[block.title for block in result.value.bento_blocks],
            *[block.short_text for block in result.value.bento_blocks],
            *[block.detail for block in result.value.bento_blocks],
        ]
    ).lower()

    assert result.value.bento_blocks[0].title == "Итог сессии"
    assert "Сессия завершилась" in result.value.outcome
    assert "Итоговая оценка" in result.value.final_verdict
    assert "fake judge" not in combined_text
    assert "fake" not in combined_text
    assert "заглуш" not in combined_text
    assert "детерминирован" not in combined_text


def test_parse_judge_session_output_accepts_direct_output_dict() -> None:
    """Parser should accept a direct JudgeSessionOutput-like dictionary."""
    result = parse_judge_session_output(
        _valid_output_dict()
    )

    assert isinstance(result, JudgeSessionOutput)
    assert result.overall_score == 80


def test_parse_judge_session_output_accepts_output_text_json() -> None:
    """Parser should extract JSON from provider output_text envelopes."""
    result = parse_judge_session_output(
        {
            "output_text": json.dumps(
                {
                    **_valid_output_dict(),
                    "overall_score": 61,
                    "overall_grade": "normal",
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
            **_valid_output_dict(),
            "overall_score": 70,
            "overall_grade": "normal",
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
            **_valid_output_dict(),
            "overall_score": 88,
            "overall_grade": "strong",
        },
    )

    result = client.judge_session(_build_payload())

    assert isinstance(result.value, JudgeSessionOutput)
    assert result.value.overall_grade == "strong"


def test_structured_judge_client_retries_with_retry_instruction() -> None:
    """Structured client should add retry_instruction after the first invalid response."""
    captured_requests: list[dict[str, object]] = []
    responses = iter(
        [
            {"output_text": "not json"},
            {
                "output_text": json.dumps(
                    {
                        **_valid_output_dict(),
                        "overall_score": 63,
                        "overall_grade": "normal",
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
    assert result.value.overall_score == 63
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

    assert isinstance(result.value, JudgeSessionOutput)
    assert 0 <= result.value.overall_score <= 100


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


def test_build_judge_client_allows_fake_fallback_for_incomplete_yandex_in_local_when_flag_is_true() -> None:
    client = build_judge_client(
        Settings(
            app_env="local",
            llm_backend="yandex_compatible",
            allow_fake_llm_fallback=True,
            yandex_api_key="",
            yandex_judge_folder_id="judge-folder",
            yandex_judge_agent_id="judge-agent",
        )
    )

    assert isinstance(client, FakeJudgeClient)


def test_validate_judge_output_accepts_valid_indexes() -> None:
    """Post-validation should accept evidence indexes that point to existing 1-based turns."""
    payload = _build_payload()
    output = JudgeSessionOutput.model_validate(_valid_output_dict())

    validated = validate_judge_output(output, payload)

    assert validated == output


def test_validate_judge_output_rejects_invalid_bento_evidence_index() -> None:
    """Bento evidence indexes should be rejected when they point outside the input turns."""
    payload = _build_payload()
    output = JudgeSessionOutput.model_validate(_valid_output_dict(bento_evidence=[99]))

    with pytest.raises(JudgeOutputValidationError):
        validate_judge_output(output, payload)


def test_validate_judge_output_rejects_invalid_skill_evidence_index() -> None:
    """Skill evidence indexes should be rejected when they point outside the input turns."""
    payload = _build_payload()
    output = JudgeSessionOutput.model_validate(_valid_output_dict(skill_evidence=[99]))

    with pytest.raises(JudgeOutputValidationError):
        validate_judge_output(output, payload)


def test_validate_judge_output_rejects_invalid_finding_evidence_index() -> None:
    """Finding evidence indexes should be rejected when they point outside the input turns."""
    payload = _build_payload()
    output = JudgeSessionOutput.model_validate(_valid_output_dict(finding_evidence=[99]))

    with pytest.raises(JudgeOutputValidationError):
        validate_judge_output(output, payload)


def test_structured_judge_client_retries_on_invalid_evidence_indexes() -> None:
    """Structured client should retry when provider output contains invalid evidence indexes."""
    responses = iter(
        [
            {"output_text": json.dumps(_valid_output_dict(bento_evidence=[99]))},
            {"output_text": json.dumps({**_valid_output_dict(), "overall_score": 66, "overall_grade": "normal"})},
        ]
    )

    client = StructuredJudgeClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret-key-value",
        folder_id="folder-1",
        agent_id="agent-1",
        max_retries=1,
        transport=lambda _: next(responses),
    )

    result = client.judge_session(_build_payload())

    assert result.value.overall_score == 66


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
                app_env="production",
                allow_fake_llm_fallback=False,
                yandex_api_key="secret-key-value",
                yandex_folder_id="",
                yandex_agent_id="",
                yandex_judge_folder_id="judge-folder",
                yandex_judge_agent_id="",
            )
        )


def test_build_judge_client_raises_for_unknown_backend_in_production_even_when_flag_is_true() -> None:
    with pytest.raises(LLMProviderConfigurationError):
        build_judge_client(
            Settings(
                app_env="production",
                llm_backend="unknown-provider",
                allow_fake_llm_fallback=True,
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
