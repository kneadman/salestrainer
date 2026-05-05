from __future__ import annotations

from app.domain.persona_generation import UniversalFakePersonaGenerator
from app.domain.scenarios import get_scenario


def test_universal_fake_persona_generator_always_returns_final_decider() -> None:
    generator = UniversalFakePersonaGenerator(seed=1)

    for _ in range(50):
        persona = generator.generate()
        assert persona.authority_level == "final_decider"


def test_universal_fake_persona_generator_uses_selected_training_format() -> None:
    persona = UniversalFakePersonaGenerator(seed=2).generate(
        scenario=get_scenario("price_and_value"),
        persona_policy={"target_action": "book_value_review"},
    )

    assert persona.id.startswith("generated_price_and_value_")
    assert persona.target_action == "book_value_review"
    assert "price" in persona.behavior_model or persona.price_sensitivity >= 60


def test_generated_persona_has_required_domain_fields_without_product_line() -> None:
    persona = UniversalFakePersonaGenerator(seed=4).generate()

    assert persona.role
    assert "product_line" not in persona.model_dump()
    assert persona.behavior_model
    assert persona.current_business_context
    assert persona.latent_pains
    assert persona.typical_objections
    assert persona.buying_motivation
    assert persona.decision_criteria
    assert persona.hidden_constraints
    assert persona.communication_style


def test_universal_fake_persona_generator_is_reproducible_with_seed() -> None:
    first = UniversalFakePersonaGenerator(seed=9).generate()
    second = UniversalFakePersonaGenerator(seed=9).generate()

    assert first.model_dump() == second.model_dump()


def test_generated_personas_keep_required_lists_non_empty() -> None:
    generator = UniversalFakePersonaGenerator(seed=5)

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


def test_authority_level_does_not_depend_on_role() -> None:
    generator = UniversalFakePersonaGenerator(seed=7)
    seen_roles: set[str] = set()

    for _ in range(100):
        persona = generator.generate()
        seen_roles.add(persona.role)
        assert persona.authority_level == "final_decider"

    assert len(seen_roles) > 1


def test_universal_fake_persona_generator_respects_allowed_roles_and_target_action_policy() -> None:
    persona = UniversalFakePersonaGenerator(seed=8).generate(
        scenario=get_scenario("qualification_and_authority"),
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "confirm_decision_process",
        },
    )

    assert persona.role == "owner"
    assert persona.target_action == "confirm_decision_process"
    assert persona.authority_level == "final_decider"
