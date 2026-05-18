from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.domain.models import LEGACY_PERSONA_FIELD_NAMES, PersonaProfile, PersonaGenerationOutput
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


def test_generated_persona_has_required_domain_fields() -> None:
    persona = UniversalFakePersonaGenerator(seed=4).generate()

    assert persona.role
    assert persona.behavior_model
    assert persona.current_business_context
    assert persona.latent_pains
    assert persona.typical_objections
    assert persona.buying_motivation
    assert persona.decision_criteria
    assert persona.hidden_constraints
    assert persona.communication_style
    assert persona.current_solution
    assert persona.alternative_solutions
    assert persona.information_gaps


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
        assert persona.alternative_solutions
        assert persona.information_gaps
        assert persona.cares_about


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


def test_fake_persona_generator_returns_v31_persona() -> None:
    generator = UniversalFakePersonaGenerator(seed=1)
    persona = generator.generate(scenario=get_scenario("first_contact_discovery"))
    persona_dump = persona.model_dump()

    assert persona.authority_level == "final_decider"
    assert persona.current_solution
    assert len(persona.alternative_solutions) >= 2
    assert len(persona.information_gaps) >= 2
    assert all(key not in persona_dump for key in LEGACY_PERSONA_FIELD_NAMES)


def test_persona_profile_accepts_v31_schema() -> None:
    persona = PersonaProfile.model_validate({
        "id": "saas_hr_medium_042",
        "display_name": "Елена Михайловна, HR-директор ООО «ТехноСтарт»",
        "role": "operations_director",
        "industry": "ИТ",
        "company_size": "50-200",
        "authority_level": "final_decider",
        "behavior_model": "interested_but_overloaded",
        "target_action": "demo",
        "current_business_context": (
            "IT-компания на 80 человек активно растёт и нанимает 15–20 специалистов в месяц. "
            "Сейчас подбор ведётся через HeadHunter, Excel и ручное планирование собеседований, "
            "из-за чего кандидаты теряются между этапами."
        ),
        "business_facts": [
            "80 сотрудников в IT-компании",
            "2 рекрутера ведут 15–20 вакансий в месяц",
        ],
        "cares_about": [
            "сократить time-to-hire",
            "не перегрузить рекрутеров внедрением",
            "не потерять сильных кандидатов",
        ],
        "current_solution": "HeadHunter + Excel-таблица + ручное планирование собеседований",
        "alternative_solutions": [
            "статус-кво: продолжать вести подбор в Excel",
            "нанять ещё одного рекрутера",
            "рассмотреть конкурирующий ATS",
        ],
        "information_gaps": [
            "Думает, что внедрение ATS займёт несколько месяцев",
            "Не знает, что можно начать с пилота на двух рекрутерах",
        ],
        "latent_pains": [
            "Стыдится, что в IT-компании подбор до сих пор ведётся через Excel",
            "Боится сопротивления рекрутеров",
        ],
        "buying_motivation": [
            "сократить time-to-hire и выполнить план найма",
            "получить прозрачную воронку вместо ручного контроля",
        ],
        "decision_criteria": [
            "внедрение без остановки текущего подбора",
            "интеграция с HeadHunter",
            "понятная цена на небольшой пилот",
        ],
        "hidden_constraints": [
            "Бюджет на HR-tech ограничен и требует объяснения CEO",
        ],
        "typical_objections": [
            "У нас и так работает, зачем ломать процесс?",
            "Внедрение займёт слишком много времени",
        ],
        "proof_sensitivity": [
            "похожий кейс из IT-компании",
            "демо на типовой вакансии",
        ],
        "call_scoring_criteria": [
            "выяснил ли менеджер текущий процесс подбора",
            "понял ли, где теряются кандидаты",
            "предложил ли безопасный пилот",
        ],
        "communication_style": (
            "Отвечает быстро и немного уставшим тоном. Не любит общие обещания."
        ),
        "initial_openness": 30,
        "starting_interest": 40,
        "price_sensitivity": 50,
        "urgency": 60,
        "trust_baseline": 25,
    })

    assert persona.authority_level == "final_decider"
    assert persona.current_solution
    assert len(persona.alternative_solutions) >= 2
    assert len(persona.information_gaps) >= 2
    assert "current_accounting_model" not in persona.model_dump()


def test_persona_profile_rejects_legacy_accounting_fields() -> None:
    payload = {
        "id": "test",
        "display_name": "Test",
        "role": "owner",
        "industry": "b2b",
        "company_size": "30-100",
        "authority_level": "final_decider",
        "behavior_model": "skeptical_but_rational",
        "target_action": "book_meeting",
        "current_business_context": "Context.",
        "business_facts": ["Fact 1", "Fact 2"],
        "cares_about": ["a", "b", "c"],
        "current_solution": "Excel",
        "alternative_solutions": ["статус-кво", "option b"],
        "information_gaps": ["gap 1", "gap 2"],
        "latent_pains": ["pain 1", "pain 2"],
        "buying_motivation": ["motivation 1", "motivation 2"],
        "decision_criteria": ["c1", "c2", "c3"],
        "hidden_constraints": ["constraint 1"],
        "typical_objections": ["objection 1", "objection 2"],
        "proof_sensitivity": ["proof 1", "proof 2"],
        "call_scoring_criteria": ["criteria 1", "criteria 2", "criteria 3"],
        "communication_style": "Style.",
        "initial_openness": 25,
        "starting_interest": 25,
        "price_sensitivity": 50,
        "urgency": 20,
        "trust_baseline": 20,
        "current_accounting_model": "director_self",
    }

    with pytest.raises(ValidationError):
        PersonaProfile.model_validate(payload)


def test_persona_profile_rejects_non_final_decider() -> None:
    payload = {
        "id": "test",
        "display_name": "Test",
        "role": "owner",
        "industry": "b2b",
        "company_size": "30-100",
        "authority_level": "influencer",
        "behavior_model": "skeptical_but_rational",
        "target_action": "book_meeting",
        "current_business_context": "Context.",
        "business_facts": ["Fact 1", "Fact 2"],
        "cares_about": ["a", "b", "c"],
        "current_solution": "Excel",
        "alternative_solutions": ["статус-кво", "option b"],
        "information_gaps": ["gap 1", "gap 2"],
        "latent_pains": ["pain 1", "pain 2"],
        "buying_motivation": ["motivation 1", "motivation 2"],
        "decision_criteria": ["c1", "c2", "c3"],
        "hidden_constraints": ["constraint 1"],
        "typical_objections": ["objection 1", "objection 2"],
        "proof_sensitivity": ["proof 1", "proof 2"],
        "call_scoring_criteria": ["criteria 1", "criteria 2", "criteria 3"],
        "communication_style": "Style.",
        "initial_openness": 25,
        "starting_interest": 25,
        "price_sensitivity": 50,
        "urgency": 20,
        "trust_baseline": 20,
    }

    with pytest.raises(ValidationError):
        PersonaProfile.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    [
        "business_facts",
        "cares_about",
        "alternative_solutions",
        "information_gaps",
        "latent_pains",
        "buying_motivation",
        "decision_criteria",
        "hidden_constraints",
        "typical_objections",
        "proof_sensitivity",
        "call_scoring_criteria",
    ],
)
def test_persona_profile_rejects_empty_lists(field_name: str) -> None:
    payload = {
        "id": "test",
        "display_name": "Test",
        "role": "owner",
        "industry": "b2b",
        "company_size": "30-100",
        "authority_level": "final_decider",
        "behavior_model": "skeptical_but_rational",
        "target_action": "book_meeting",
        "current_business_context": "Context.",
        "business_facts": ["Fact 1", "Fact 2"],
        "cares_about": ["a", "b", "c"],
        "current_solution": "Excel",
        "alternative_solutions": ["статус-кво", "option b"],
        "information_gaps": ["gap 1", "gap 2"],
        "latent_pains": ["pain 1", "pain 2"],
        "buying_motivation": ["motivation 1", "motivation 2"],
        "decision_criteria": ["c1", "c2", "c3"],
        "hidden_constraints": ["constraint 1"],
        "typical_objections": ["objection 1", "objection 2"],
        "proof_sensitivity": ["proof 1", "proof 2"],
        "call_scoring_criteria": ["criteria 1", "criteria 2", "criteria 3"],
        "communication_style": "Style.",
        "initial_openness": 25,
        "starting_interest": 25,
        "price_sensitivity": 50,
        "urgency": 20,
        "trust_baseline": 20,
    }
    payload[field_name] = []

    with pytest.raises(ValidationError):
        PersonaProfile.model_validate(payload)


def test_persona_profile_requires_status_quo_alternative() -> None:
    payload = {
        "id": "test",
        "display_name": "Test",
        "role": "owner",
        "industry": "b2b",
        "company_size": "30-100",
        "authority_level": "final_decider",
        "behavior_model": "skeptical_but_rational",
        "target_action": "book_meeting",
        "current_business_context": "Context.",
        "business_facts": ["Fact 1", "Fact 2"],
        "cares_about": ["a", "b", "c"],
        "current_solution": "Excel",
        "alternative_solutions": [
            "нанять ещё одного рекрутера",
            "купить конкурирующий ATS",
        ],
        "information_gaps": ["gap 1", "gap 2"],
        "latent_pains": ["pain 1", "pain 2"],
        "buying_motivation": ["motivation 1", "motivation 2"],
        "decision_criteria": ["c1", "c2", "c3"],
        "hidden_constraints": ["constraint 1"],
        "typical_objections": ["objection 1", "objection 2"],
        "proof_sensitivity": ["proof 1", "proof 2"],
        "call_scoring_criteria": ["criteria 1", "criteria 2", "criteria 3"],
        "communication_style": "Style.",
        "initial_openness": 25,
        "starting_interest": 25,
        "price_sensitivity": 50,
        "urgency": 20,
        "trust_baseline": 20,
    }

    with pytest.raises(ValidationError):
        PersonaProfile.model_validate(payload)


def test_persona_generation_output_json_schema_does_not_contain_legacy_fields() -> None:
    schema = PersonaGenerationOutput.model_json_schema()
    schema_as_text = json.dumps(schema, ensure_ascii=False)

    for legacy_field in [
        "current_accounting_model",
        "legal_form",
        "tax_system",
        "accounting_software",
        "accounting_software_mode",
        "primary_docs_owner",
    ]:
        assert legacy_field not in schema_as_text

    assert "current_solution" in schema_as_text
    assert "alternative_solutions" in schema_as_text
    assert "information_gaps" in schema_as_text
