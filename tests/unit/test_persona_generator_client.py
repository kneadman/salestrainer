from __future__ import annotations

import json

from app.infrastructure.persona_generator_client import parse_persona_generation_response


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
