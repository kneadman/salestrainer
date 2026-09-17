import re

from app.domain.models import PersonaGenerationOutput
from app.prompts.schemas import (
    build_strict_json_schema,
    llm_turn_response_schema,
    load_client_simulator_prompt,
    load_persona_generator_prompt,
    make_strict_json_schema,
)
from app.prompts.versions import prompt_revisions


def test_client_simulator_prompt_uses_universal_revealed_facts_contract() -> None:
    prompt = load_client_simulator_prompt()

    assert "accounting outsourcing" not in prompt
    assert "outsourced CFO services" not in prompt
    assert "revealed_facts" in prompt
    assert "`revealed_facts` НЕ является частью `state_patch`" in prompt
    assert "Запрещены технические коды" in prompt


def test_client_simulator_prompt_keeps_latest_master_rules() -> None:
    """The 2026-09 master revision must not be lost during future edits."""
    prompt = load_client_simulator_prompt()

    # Client does not guess why the manager is calling.
    assert "Клиент не знает повода звонка" in prompt
    # Final-check items 11-13 added in the master revision.
    assert "Ты не отвечаешь оппоненту его же языком" in prompt
    assert "Ты не отвечаешь банально" in prompt
    assert "Ты не рассказываешь больше, чем известно по контексту" in prompt


def test_persona_generator_prompt_keeps_master_isolation_and_cluster_rules() -> None:
    prompt = load_persona_generator_prompt()

    # Context isolation: examples from the instruction are not persona content.
    assert "ИЗОЛЯЦИЯ КОНТЕКСТА" in prompt
    assert "Он не является источником содержания" in prompt
    # The document-flow semantic cluster may appear at most once per persona.
    assert "КЛАСТЕРНЫЙ ЛИМИТ" in prompt
    # alternative_solutions[0] must be status quo, stated explicitly.
    assert "Первым элементом обязательно укажи статус-кво" in prompt
    # Placeholders keep the model from copying concrete example values.
    assert "[N] сотрудников" in prompt
    assert "[Статус-кво: текущее решение клиента, продолжение как есть]" in prompt


def test_persona_generator_prompt_does_not_leak_concrete_example_values() -> None:
    """No leftover hard-coded example persona from the pre-master revision."""
    prompt = load_persona_generator_prompt()

    assert "Оптовая торговля строительными материалами" not in prompt
    assert "оборот 82 млн руб" not in prompt


def test_prompt_revisions_are_content_derived_and_stable() -> None:
    revisions = prompt_revisions()

    assert set(revisions) == {"dialogue", "persona", "persona_seed", "judge", "summary"}
    # A revision is derived from the file content, so it must stay stable while
    # the file is unchanged and change whenever the text changes.
    assert revisions == prompt_revisions()
    for revision in revisions.values():
        assert re.fullmatch(r"[a-z_]+-[0-9a-f]{12}", revision), revision
    assert len(set(revisions.values())) == len(revisions)


def test_prompt_revision_changes_when_prompt_content_changes(tmp_path, monkeypatch) -> None:
    """Guards the 'editing a prompt changes its revision automatically' contract."""
    from app.prompts import versions

    prompt_file = tmp_path / "client_simulator.md"
    prompt_file.write_text("version one", encoding="utf-8")
    monkeypatch.setattr(versions, "DIALOGUE_PROMPT_FILE", prompt_file)
    versions.prompt_revisions.cache_clear()

    first = versions.prompt_revisions()["dialogue"]
    prompt_file.write_text("version two", encoding="utf-8")
    versions.prompt_revisions.cache_clear()
    second = versions.prompt_revisions()["dialogue"]

    assert first != second
    assert first.startswith("client_simulator-")


def test_llm_turn_response_schema_lists_every_property_as_required() -> None:
    """OpenAI-style strict validators reject schemas with optional properties.

    Pydantic omits defaulted fields from ``required``; without widening, every
    GPT-class model on the router answers with HTTP 400
    ``Invalid schema for response_format``.
    """
    schema = llm_turn_response_schema()

    assert schema["required"] == sorted(schema["properties"].keys())
    assert schema["additionalProperties"] is False
    state_patch = schema["$defs"]["StatePatch"]
    assert state_patch["required"] == sorted(state_patch["properties"].keys())
    assert state_patch["additionalProperties"] is False


def test_make_strict_json_schema_fixes_nested_objects_and_arrays() -> None:
    schema = make_strict_json_schema(
        {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"a": {"type": "string"}, "b": {"type": "integer"}},
                        "required": ["a"],
                    },
                }
            },
        }
    )

    assert schema["required"] == ["items"]
    assert schema["additionalProperties"] is False
    nested = schema["properties"]["items"]["items"]
    assert nested["required"] == ["a", "b"]
    assert nested["additionalProperties"] is False


def test_persona_and_dialogue_strict_schemas_accept_model_classes() -> None:
    persona_schema = make_strict_json_schema(PersonaGenerationOutput)

    assert persona_schema["required"] == sorted(persona_schema["properties"].keys())
    profile = persona_schema["$defs"]["PersonaProfile"]
    # ``authority_level`` has a default in the model and used to be the exact
    # field a strict validator complained about.
    assert "authority_level" in profile["required"]
    assert build_strict_json_schema(PersonaGenerationOutput)["required"] == persona_schema["required"]
