from __future__ import annotations

from app.domain.errors import UnknownScenarioError
from app.domain.models import Scenario


SCENARIOS: dict[str, Scenario] = {
    "first_contact_discovery": Scenario(
        id="first_contact_discovery",
        name="Первичный контакт и разведка",
        training_format="first_contact_discovery",
        default_starting_interest=25,
        default_stage="first_contact",
        manager_goal="Понять контекст клиента и открыть содержательный диалог.",
        success_condition="Менеджер проясняет ситуацию клиента и получает разрешение на следующий осмысленный шаг.",
        failure_condition="Разговор скатывается в ранний питч без понимания контекста.",
        evaluation_focus=["discovery", "relevance", "next_step_timing"],
        client_behavior_hint="Клиент мало знает о вас и сначала экономит внимание.",
    ),
    "qualification_and_authority": Scenario(
        id="qualification_and_authority",
        name="Квалификация и полномочия",
        training_format="qualification_and_authority",
        default_starting_interest=22,
        default_stage="qualification",
        manager_goal="Понять, кто влияет на решение и как устроен процесс согласования.",
        success_condition="Менеджер уточняет роль собеседника и карту принятия решения без давления.",
        failure_condition="Менеджер давит на встречу, не разобравшись в полномочиях.",
        evaluation_focus=["role_identification", "authority_discovery", "pressure_control"],
        client_behavior_hint="Клиент осторожно раскрывает полномочия и процесс принятия решений.",
    ),
    "needs_diagnosis": Scenario(
        id="needs_diagnosis",
        name="Диагностика потребностей",
        training_format="needs_diagnosis",
        default_starting_interest=30,
        default_stage="needs_analysis",
        manager_goal="Добраться до корневых болей, ограничений и критериев выбора.",
        success_condition="Менеджер раскрывает реальные проблемы и критерии решения.",
        failure_condition="Разговор остаётся на уровне симптомов и общих фраз.",
        evaluation_focus=["pain_discovery", "constraint_discovery", "decision_criteria"],
        client_behavior_hint="Клиент раскрывает детали только в ответ на точные вопросы.",
    ),
    "objection_handling": Scenario(
        id="objection_handling",
        name="Работа с возражениями",
        training_format="objection_handling",
        default_starting_interest=24,
        default_stage="objection_handling",
        manager_goal="Разобрать возражение, не споря и не давя.",
        success_condition="Менеджер снимает напряжение и переводит разговор в конструктив.",
        failure_condition="Менеджер спорит, давит или игнорирует реальную причину возражения.",
        evaluation_focus=["objection_handling", "empathy", "relevance"],
        client_behavior_hint="Клиент проверяет, слышат ли его, и быстро замечает шаблонные ответы.",
    ),
    "price_and_value": Scenario(
        id="price_and_value",
        name="Цена и ценность",
        training_format="price_and_value",
        default_starting_interest=26,
        default_stage="value_discussion",
        manager_goal="Связать ценность решения с контекстом клиента до обсуждения цены.",
        success_condition="Менеджер переводит разговор от цены к экономике и рискам решения.",
        failure_condition="Менеджер уходит в скидки или защищает цену без контекста.",
        evaluation_focus=["value_linking", "economic_reasoning", "objection_handling"],
        client_behavior_hint="Клиент чувствителен к цене и требует конкретики по ценности.",
    ),
    "bad_experience_recovery": Scenario(
        id="bad_experience_recovery",
        name="Восстановление доверия после плохого опыта",
        training_format="bad_experience_recovery",
        default_starting_interest=18,
        default_stage="trust_recovery",
        manager_goal="Признать риск клиента и аккуратно восстановить доверие.",
        success_condition="Менеджер снижает защиту клиента и договаривается о безопасном следующем шаге.",
        failure_condition="Менеджер обещает слишком много или обесценивает прошлый опыт клиента.",
        evaluation_focus=["trust_building", "empathy", "credibility"],
        client_behavior_hint="Клиент изначально насторожен и проверяет вас на зрелость.",
    ),
    "next_step_booking": Scenario(
        id="next_step_booking",
        name="Назначение следующего шага",
        training_format="next_step_booking",
        default_starting_interest=40,
        default_stage="next_step",
        manager_goal="Перевести хороший разговор в конкретное действие.",
        success_condition="Менеджер договаривается о понятном и уместном следующем шаге.",
        failure_condition="Следующий шаг остаётся размытым или навязанным.",
        evaluation_focus=["next_step_timing", "clarity", "conversation_control"],
        client_behavior_hint="Клиент в целом открыт, но защищает календарь и внимание.",
    ),
    "follow_up_after_pause": Scenario(
        id="follow_up_after_pause",
        name="Возврат после паузы",
        training_format="follow_up_after_pause",
        default_starting_interest=20,
        default_stage="follow_up",
        manager_goal="Вернуть разговор в контекст и понять, что изменилось за время паузы.",
        success_condition="Менеджер восстанавливает контекст и находит реалистичный путь продолжения.",
        failure_condition="Менеджер повторяет старый питч, не признавая паузу и смену приоритетов.",
        evaluation_focus=["context_recovery", "relevance", "next_step_timing"],
        client_behavior_hint="Клиент остыл и сначала проверяет уместность продолжения.",
    ),
}

DEPRECATED_SCENARIO_ALIASES = {
    "generic_b2b_first_contact": "first_contact_discovery",
    "sales_audit_cold_outreach": "first_contact_discovery",
    "accounting_outsource_cold_outreach": "first_contact_discovery",
}


def normalize_scenario_id(scenario_id: str) -> str:
    """Map deprecated scenario ids to current universal training formats."""
    return DEPRECATED_SCENARIO_ALIASES.get(scenario_id, scenario_id)


def list_scenarios() -> list[Scenario]:
    """Return only current universal training formats for API and UI selection."""
    return list(SCENARIOS.values())


def get_scenario(scenario_id: str) -> Scenario:
    """Load a training format by id while keeping deprecated ids readable in old data."""
    normalized_id = normalize_scenario_id(scenario_id)
    try:
        return SCENARIOS[normalized_id]
    except KeyError as error:
        raise UnknownScenarioError(f"Unknown scenario_id '{scenario_id}'.") from error
