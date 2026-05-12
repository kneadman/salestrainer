from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.domain.models import PersonaGenerationInput
from app.domain.scenarios import get_scenario
from app.infrastructure.persona_generator_client import (
    PersonaGenerationBusinessValidationError,
    StructuredPersonaGeneratorClient,
    parse_persona_generation_response,
    validate_generated_persona,
)


def _persona_payload() -> dict[str, object]:
    """Build a minimal valid persona-generator output payload for parser tests."""
    return {
        "persona": {
            "id": "generated_beauty_owner_first_contact",
            "display_name": "Unknown B2B contact",
            "role": "owner",
            "industry": "beauty",
            "company_size": "30-100",
            "authority_level": "final_decider",
            "behavior_model": "skeptical_but_rational",
            "target_action": "book_intro_call",
            "current_business_context": "The company needs a better first conversation process.",
            "business_facts": ["A new sales process is being reviewed.", "Owner is directly involved."],
            "cares_about": ["control", "margin", "speed"],
            "current_solution": "Excel + manual outreach tracking",
            "alternative_solutions": [
                "статус-кво: продолжать как сейчас",
                "hire a sales ops person",
                "buy a lightweight CRM",
            ],
            "information_gaps": [
                "Thinks CRM implementation requires months.",
                "Does not know about plug-and-play options.",
            ],
            "latent_pains": ["Discovery is too shallow.", "Follow-up is inconsistent."],
            "buying_motivation": ["Reduce lost opportunities.", "Improve conversion."],
            "decision_criteria": ["credibility", "clarity", "quick setup"],
            "hidden_constraints": ["The owner protects calendar time."],
            "typical_objections": ["We already have a supplier.", "No time to change tools."],
            "proof_sensitivity": ["cases", "process"],
            "call_scoring_criteria": ["role discovery", "pain identification", "next step clarity"],
            "communication_style": "short answers, asks for specifics",
            "initial_openness": 25,
            "starting_interest": 22,
            "price_sensitivity": 60,
            "urgency": 45,
            "trust_baseline": 22,
        },
        "generation_notes": "Generated from policy.",
        "policy_coverage": ["role", "pain"],
        "risk_flags": [],
    }


def test_parse_persona_generation_response_from_direct_json_object() -> None:
    output = parse_persona_generation_response(_persona_payload())

    assert output.persona.id == "generated_beauty_owner_first_contact"
    assert output.persona.role == "owner"
    assert output.policy_coverage == ["role", "pain"]


def test_parse_persona_generation_response_from_provider_output_text() -> None:
    raw = {"output_text": f"```json\n{json.dumps(_persona_payload())}\n```"}

    output = parse_persona_generation_response(raw)

    assert output.persona.starting_interest == 22


def test_structured_persona_generator_builds_context_envelope() -> None:
    captured: dict[str, object] = {}

    client = StructuredPersonaGeneratorClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret",
        max_retries=0,
        transport=lambda request_payload: captured.update(request_payload) or {"output_text": json.dumps(_persona_payload())},
    )

    client.generate_persona(
        PersonaGenerationInput(
            scenario=get_scenario("first_contact_discovery"),
            training_config_name="Demo",
            persona_generation_context="Client business context.",
        )
    )

    input_payload = json.loads(captured["input"])
    assert input_payload["client_persona_context"] == "Client business context."
    assert "generation_payload" in input_payload


def _generation_input(allowed_roles: list[str] | None = None) -> PersonaGenerationInput:
    """Build generation input used by business-rule validation tests."""
    return PersonaGenerationInput(
        scenario=get_scenario("first_contact_discovery"),
        training_config_name="Demo",
        persona_generation_context="Client business context.",
        allowed_roles=allowed_roles,
    )


def test_generated_persona_business_rules_reject_non_decider() -> None:
    payload = _persona_payload()
    payload["persona"]["authority_level"] = "gatekeeper"  # type: ignore[index]

    # Pydantic now rejects invalid authority_level before business validation.
    with pytest.raises(ValidationError):
        parse_persona_generation_response(payload)


def test_generated_persona_business_rules_reject_role_outside_allowed_roles() -> None:
    output = parse_persona_generation_response(_persona_payload())

    with pytest.raises(PersonaGenerationBusinessValidationError):
        validate_generated_persona(output, _generation_input(allowed_roles=["cfo"]))


@pytest.mark.parametrize(
    "field",
    [
        "business_facts",
        "cares_about",
        "alternative_solutions",
        "information_gaps",
        "latent_pains",
        "typical_objections",
        "decision_criteria",
        "hidden_constraints",
        "proof_sensitivity",
        "call_scoring_criteria",
    ],
)
def test_generated_persona_business_rules_reject_empty_required_lists(field: str) -> None:
    payload = _persona_payload()
    payload["persona"][field] = []  # type: ignore[index]

    # Pydantic min-length validation catches these before business rules.
    with pytest.raises(ValidationError):
        parse_persona_generation_response(payload)


def test_generated_persona_business_rules_reject_missing_status_quo() -> None:
    payload = _persona_payload()
    payload["persona"]["alternative_solutions"] = [  # type: ignore[index]
        "hire a sales ops person",
        "buy a lightweight CRM",
    ]

    # Pydantic field_validator catches missing status quo before business rules.
    with pytest.raises(ValidationError):
        parse_persona_generation_response(payload)


def test_generated_persona_business_rules_accept_valid_persona() -> None:
    output = parse_persona_generation_response(_persona_payload())

    persona = validate_generated_persona(output, _generation_input(allowed_roles=["owner"]))

    assert persona.role == "owner"


def test_structured_persona_generator_raises_after_invalid_business_output_without_fallback() -> None:
    invalid_payload = _persona_payload()
    invalid_payload["persona"]["role"] = "cfo"  # type: ignore[index]
    client = StructuredPersonaGeneratorClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret",
        max_retries=0,
        transport=lambda _: {"output_text": json.dumps(invalid_payload)},
    )

    with pytest.raises(Exception, match="Persona generator request failed"):
        client.generate_persona(_generation_input(allowed_roles=["owner"]))
