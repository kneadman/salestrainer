from __future__ import annotations

from app.domain.persona_generation import PersonaGenerator


def test_persona_generator_always_returns_final_decider() -> None:
    generator = PersonaGenerator(seed=1)

    for _ in range(50):
        persona = generator.generate()
        assert persona.authority_level == "final_decider"


def test_persona_generator_can_create_accounting_outsourcing_persona() -> None:
    persona = PersonaGenerator(seed=2).generate("accounting_outsourcing")

    assert persona.product_line == "accounting_outsourcing"
    assert persona.current_accounting_model != ""
    assert persona.target_action in {
        "book_express_audit",
        "get_accounting_data_export",
        "schedule_audit_result_meeting",
        "send_personal_offer_after_audit",
    }


def test_persona_generator_can_create_outsourced_cfo_persona() -> None:
    persona = PersonaGenerator(seed=3).generate("outsourced_cfo")

    assert persona.product_line == "outsourced_cfo"
    assert persona.target_action in {
        "book_financial_diagnostic",
        "collect_financial_reports",
        "schedule_financial_model_meeting",
        "present_management_reporting_offer",
    }


def test_generated_persona_has_required_domain_fields() -> None:
    persona = PersonaGenerator(seed=4).generate()

    assert persona.role
    assert persona.product_line
    assert persona.behavior_model
    assert persona.current_business_context
    assert persona.latent_pains
    assert persona.typical_objections
    assert persona.buying_motivation
    assert persona.decision_criteria
    assert persona.hidden_constraints
    assert persona.communication_style


def test_persona_generator_is_reproducible_with_seed() -> None:
    first = PersonaGenerator(seed=9).generate()
    second = PersonaGenerator(seed=9).generate()

    assert first.model_dump() == second.model_dump()


def test_generated_personas_keep_required_lists_non_empty() -> None:
    generator = PersonaGenerator(seed=5)

    for _ in range(100):
        persona = generator.generate()
        assert persona.latent_pains
        assert persona.typical_objections
        assert persona.buying_motivation
        assert persona.decision_criteria
        assert persona.hidden_constraints
        assert persona.business_facts
        assert persona.proof_sensitivity
        assert persona.call_scoring_criteria


def test_current_accounting_model_is_set_for_accounting_outsourcing() -> None:
    persona = PersonaGenerator(seed=6).generate("accounting_outsourcing")
    assert persona.current_accounting_model in {
        "outsourced_accounting",
        "private_accountant",
        "inhouse_accountant",
        "owner_does_accounting",
        "unknown",
    }


def test_authority_level_does_not_depend_on_role() -> None:
    generator = PersonaGenerator(seed=7)
    seen_roles: set[str] = set()

    for _ in range(100):
        persona = generator.generate()
        seen_roles.add(persona.role)
        assert persona.authority_level == "final_decider"

    assert len(seen_roles) > 1
