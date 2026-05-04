from __future__ import annotations

import json

import pytest

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
            "id": "generated_accounting_owner_tax_risk",
            "display_name": "Unknown B2B contact",
            "role": "owner",
            "industry": "services",
            "company_size": "30-100",
            "authority_level": "final_decider",
            "behavior_model": "skeptical_but_rational",
            "product_line": "accounting_outsourcing",
            "target_action": "book_express_audit",
            "cares_about": ["control", "tax risk"],
            "typical_objections": ["We already have an accountant."],
            "current_business_context": "The company is growing and accounting quality is unclear.",
            "latent_pains": ["Tax errors are risky."],
            "buying_motivation": ["Reduce operational risk."],
            "decision_criteria": ["data security", "similar cases"],
            "hidden_constraints": ["Bad contractor experience."],
            "business_facts": ["15 employees"],
            "proof_sensitivity": ["cases", "process"],
            "call_scoring_criteria": ["role discovery"],
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

    assert output.persona.id == "generated_accounting_owner_tax_risk"
    assert output.persona.role == "owner"
    assert output.policy_coverage == ["role", "pain"]


def test_parse_persona_generation_response_from_provider_output_text() -> None:
    raw = {"output_text": f"```json\n{json.dumps(_persona_payload())}\n```"}

    output = parse_persona_generation_response(raw)

    assert output.persona.product_line == "accounting_outsourcing"
    assert output.persona.starting_interest == 22


def _generation_input(allowed_roles: list[str] | None = None) -> PersonaGenerationInput:
    """Build generation input used by business-rule validation tests."""
    return PersonaGenerationInput(
        product_line="accounting_outsourcing",
        scenario=get_scenario("generic_b2b_first_contact"),
        training_config_name="Demo",
        allowed_roles=allowed_roles,
    )


def test_generated_persona_business_rules_reject_non_decider() -> None:
    payload = _persona_payload()
    payload["persona"]["authority_level"] = "gatekeeper"  # type: ignore[index]
    output = parse_persona_generation_response(payload)

    with pytest.raises(PersonaGenerationBusinessValidationError):
        validate_generated_persona(output, _generation_input())


def test_generated_persona_business_rules_reject_role_outside_allowed_roles() -> None:
    output = parse_persona_generation_response(_persona_payload())

    with pytest.raises(PersonaGenerationBusinessValidationError):
        validate_generated_persona(output, _generation_input(allowed_roles=["cfo"]))


@pytest.mark.parametrize("field", ["latent_pains", "typical_objections", "decision_criteria"])
def test_generated_persona_business_rules_reject_empty_required_lists(field: str) -> None:
    payload = _persona_payload()
    payload["persona"][field] = []  # type: ignore[index]
    output = parse_persona_generation_response(payload)

    with pytest.raises(PersonaGenerationBusinessValidationError):
        validate_generated_persona(output, _generation_input(allowed_roles=["owner"]))


def test_generated_persona_business_rules_accept_valid_persona() -> None:
    output = parse_persona_generation_response(_persona_payload())

    persona = validate_generated_persona(output, _generation_input(allowed_roles=["owner"]))

    assert persona.role == "owner"


def test_structured_persona_generator_falls_back_after_invalid_business_output() -> None:
    class Fallback:
        def generate_persona(self, payload: PersonaGenerationInput):
            """Return a valid local persona after provider business validation fails."""
            return parse_persona_generation_response(_persona_payload())

    invalid_payload = _persona_payload()
    invalid_payload["persona"]["authority_level"] = "gatekeeper"  # type: ignore[index]
    client = StructuredPersonaGeneratorClient(
        provider="yandex_compatible",
        base_url="https://example.test/v1",
        api_key="secret",
        max_retries=0,
        fallback_client=Fallback(),
        transport=lambda _: {"output_text": json.dumps(invalid_payload)},
    )

    output = client.generate_persona(_generation_input(allowed_roles=["owner"]))

    assert output.persona.authority_level == "final_decider"


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
