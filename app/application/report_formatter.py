from __future__ import annotations

from app.domain.interest import interest_band
from app.domain.models import TrainingSessionState, TurnEvaluation

ROLE_LABELS = {
    "owner": "собственник",
    "founder": "основатель",
    "ceo": "CEO",
    "general_director": "генеральный директор",
    "managing_partner": "управляющий партнёр",
    "commercial_director": "коммерческий директор",
    "cfo": "финансовый директор",
    "chief_accountant": "главный бухгалтер",
    "operations_director": "операционный директор",
    "sales_director": "руководитель отдела продаж",
    "purchase_manager": "менеджер по закупкам",
}

AUTHORITY_LABELS = {
    "final_decider": "ЛПР, принимает финальное решение",
    "influencer": "влияет на решение",
    "gatekeeper": "фильтрует входящие предложения",
    "evaluator": "оценивает риски и экономику",
}

INTEREST_BAND_LABELS = {
    "cold": "холодный контакт",
    "skeptical": "скепсис",
    "neutral": "нейтральный интерес",
    "warm": "тёплый интерес",
    "hot": "готовность к следующему шагу",
}

STAGE_LABELS = {
    "first_contact": "первый контакт",
    "role_discovery": "выявление роли",
    "need_discovery": "выявление потребности",
    "value_clarification": "прояснение ценности",
    "objection_handling": "работа с возражениями",
    "trust_building": "формирование доверия",
    "next_step_negotiation": "согласование следующего шага",
    "finished_success": "успешное завершение",
    "finished_failed": "неуспешное завершение",
}

BEHAVIOR_LABELS = {
    "skeptical_but_rational": "скептичный, но рациональный",
    "dominant_and_direct": "прямой и доминирующий",
    "price_sensitive": "чувствительный к цене",
    "analytical_and_cautious": "аналитичный и осторожный",
    "distrustful_due_to_bad_experience": "недоверчивый из-за прошлого негативного опыта",
    "busy_and_short": "занятый, отвечает коротко",
    "friendly_but_defensive": "дружелюбный, но закрытый",
    "formal_and_distant": "формальный и дистанцированный",
    "interested_but_overloaded": "заинтересованный, но перегруженный",
    "process_oriented": "процессный",
    "friendly_but_distrustful": "вежливый, но недоверчивый",
}

SKILL_FIELDS = [
    ("Разведка потребности", "discovery_quality_score"),
    ("Выявление роли", "role_identification_score"),
    ("Выявление боли", "pain_identification_score"),
    ("Релевантность", "relevance_score"),
    ("Давление", "pressure_score"),
    ("Работа с возражениями", "objection_handling_score"),
    ("Тайминг следующего шага", "next_step_timing_score"),
    ("Контроль диалога", "conversation_control_score"),
]


def build_human_report(session: TrainingSessionState) -> str:
    hidden_pains = _missing_items(session.persona.latent_pains, session.client_state.discovered_pains)
    hidden_constraints = _missing_items(session.persona.hidden_constraints, session.client_state.discovered_constraints)
    hidden_criteria = _missing_items(
        session.persona.decision_criteria,
        session.client_state.discovered_decision_criteria,
    )
    mistakes = build_key_mistakes(session)
    recommendations = build_recommendations(session)
    skill_lines = _build_skill_lines(session.turn_evaluations)
    result = _build_result_label(session)
    summary = _build_summary(session, mistakes)

    sections = [
        "# Итог тренировки",
        "",
        f"- Результат: {result}",
        (
            f"- Финальный интерес: {session.interest_score}/100 "
            f"({INTEREST_BAND_LABELS.get(interest_band(session.interest_score), interest_band(session.interest_score))})"
        ),
        f"- Финальная стадия: {STAGE_LABELS.get(session.stage, session.stage)}",
        f"- Количество ходов: {session.turn_count}",
        f"- Краткий вывод: {summary}",
        "",
        "# Кто был клиент",
        "",
        f"- Роль: {ROLE_LABELS.get(session.persona.role, session.persona.role)}",
        f"- Полномочия: {AUTHORITY_LABELS.get(session.persona.authority_level, session.persona.authority_level)}",
        f"- Стиль общения: {_describe_communication_style(session)}",
        f"- Скрытый контекст: {_value_or_default(session.persona.current_business_context)}",
        "",
        "# Что менеджер выяснил",
        "",
        f"- Роль: {_value_or_default(_label_role(session.client_state.discovered_role))}",
        f"- Полномочия: {_value_or_default(_label_authority(session.client_state.discovered_authority_level))}",
        f"- Боли: {_join_or_default(session.client_state.discovered_pains)}",
        f"- Критерии решения: {_join_or_default(session.client_state.discovered_decision_criteria)}",
        f"- Ограничения: {_join_or_default(session.client_state.discovered_constraints)}",
        f"- Текущий процесс: {_join_or_default(session.client_state.discovered_current_process)}",
        f"- Сигналы интереса: {_join_or_default(session.client_state.buying_signals)}",
        "",
        "# Что осталось скрытым",
        "",
        f"- Скрытые боли, которые не были выявлены: {_join_or_default(hidden_pains)}",
        f"- Скрытые ограничения, которые не были выявлены: {_join_or_default(hidden_constraints)}",
        f"- Критерии решения, которые не были выявлены: {_join_or_default(hidden_criteria)}",
        "",
        "# Открытые возражения",
        "",
        *_render_bullet_list(session.client_state.open_objections, "Явных открытых возражений к финалу не осталось."),
        "",
        "# Оценка навыков",
        "",
        *skill_lines,
        "",
        "# Ключевые ошибки",
        "",
        *_render_bullet_list(mistakes, "Критических ошибок по базовым правилам не обнаружено."),
        "",
        "# Рекомендации",
        "",
        *_render_bullet_list(recommendations, "Продолжать в том же стиле: сначала диагностика, затем движение к следующему шагу."),
    ]
    return "\n".join(sections)


def build_key_mistakes(session: TrainingSessionState) -> list[str]:
    mistakes: list[str] = []
    state = session.client_state
    scores = _score_map(session.turn_evaluations)

    if state.discovered_role is None:
        mistakes.append("Не была выяснена роль собеседника.")
    if state.discovered_authority_level is None:
        mistakes.append("Не были проверены полномочия собеседника.")
    if not state.discovered_pains:
        mistakes.append("Не были выявлены реальные боли клиента.")
    if _missing_items(session.persona.latent_pains, state.discovered_pains):
        mistakes.append("Ключевые скрытые боли клиента остались нераскрытыми.")
    if not state.buying_signals:
        mistakes.append("В диалоге не появились явные сигналы интереса.")
    if scores["next_step_timing_score"] <= 2:
        mistakes.append("Следующий шаг был предложен слишком рано или без достаточной диагностики.")
    if scores["relevance_score"] <= 2:
        mistakes.append("Вопросы и сообщения были недостаточно связаны с контекстом клиента.")
    if scores["objection_handling_score"] <= 2:
        mistakes.append("Возражения клиента не были качественно отработаны.")
    return mistakes


def build_recommendations(session: TrainingSessionState) -> list[str]:
    recommendations: list[str] = []
    state = session.client_state
    scores = _score_map(session.turn_evaluations)

    if state.discovered_role is None:
        recommendations.append(
            "В начале диалога уточнить роль: «Подскажите, вы сами отвечаете за этот участок или подключаете коллег?»"
        )
    if state.discovered_authority_level is None:
        recommendations.append(
            "Проверить путь принятия решения: «Если увидите пользу, кто ещё должен участвовать в обсуждении?»"
        )
    if not state.discovered_pains:
        recommendations.append(
            "Не переходить к предложению до выявления боли: «Что сейчас вызывает больше всего вопросов в учёте, финансах или контроле?»"
        )
    if state.open_objections:
        recommendations.append(
            "Цепляться за возражения клиента и разворачивать их в диагностику: «Вы сказали, что нет доступа к бухгалтерии — как сейчас проверяете, что всё под контролем?»"
        )
    if scores["relevance_score"] <= 2:
        recommendations.append(
            "Не задавать слишком общие вопросы вроде «чем занимается компания», если клиент уже дал более важный контекст."
        )
    if scores["next_step_timing_score"] <= 2 and len(recommendations) < 5:
        recommendations.append(
            "Следующий шаг предлагать только после подтверждённой боли, критериев решения и понимания, кто участвует в выборе."
        )
    return recommendations[:5]


def interpret_score(score: int) -> str:
    if score <= 1:
        return "критически слабая зона"
    if score == 2:
        return "слабая зона"
    if score == 3:
        return "нормально, но нестабильно"
    if score == 4:
        return "хорошо"
    return "сильно"


def average_score(evaluations: list[TurnEvaluation], field_name: str) -> int:
    if not evaluations:
        return 0
    total = sum(int(getattr(item, field_name)) for item in evaluations)
    return round(total / len(evaluations))


def _build_skill_lines(evaluations: list[TurnEvaluation]) -> list[str]:
    return [
        f"- {label}: {average_score(evaluations, field_name)}/5 — {interpret_score(average_score(evaluations, field_name))}"
        for label, field_name in SKILL_FIELDS
    ]


def _build_result_label(session: TrainingSessionState) -> str:
    if session.stage == "finished_success":
        return "успешно довёл диалог до следующего шага"
    if session.stage == "finished_failed":
        return "диалог завершился без продвижения"
    if session.interest_score >= 70:
        return "хорошая динамика, клиент близок к следующему шагу"
    if session.interest_score >= 45:
        return "контакт прогрет частично, но ещё требует диагностики"
    return "контакт остался холодным или настороженным"


def _build_summary(session: TrainingSessionState, mistakes: list[str]) -> str:
    state = session.client_state
    if not mistakes and state.buying_signals:
        return "Менеджер удержал разговор в диагностике и вывел клиента к предметному интересу."
    if state.discovered_role and state.discovered_pains and session.interest_score >= 45:
        return "Базовая диагностика состоялась, но часть важных сигналов и условий осталась недораскрытой."
    return "Разговору не хватило глубины диагностики: роль, полномочия и реальные мотивы клиента раскрыты не полностью."


def _describe_communication_style(session: TrainingSessionState) -> str:
    behavior = BEHAVIOR_LABELS.get(session.persona.behavior_model, session.persona.behavior_model)
    communication = session.persona.communication_style.strip()
    if communication:
        return f"{communication} ({behavior})"
    return behavior


def _score_map(evaluations: list[TurnEvaluation]) -> dict[str, int]:
    return {field_name: average_score(evaluations, field_name) for _, field_name in SKILL_FIELDS}


def _render_bullet_list(items: list[str], empty_message: str) -> list[str]:
    if not items:
        return [f"- {empty_message}"]
    return [f"- {item}" for item in items]


def _missing_items(hidden: list[str], discovered: list[str]) -> list[str]:
    return [item for item in hidden if item not in discovered]


def _join_or_default(items: list[str]) -> str:
    return ", ".join(items) if items else "не выявлено"


def _value_or_default(value: str | None) -> str:
    if value is None:
        return "не выявлено"
    normalized = value.strip()
    return normalized or "не выявлено"


def _label_role(value: str | None) -> str | None:
    if value is None:
        return None
    return ROLE_LABELS.get(value, value)


def _label_authority(value: str | None) -> str | None:
    if value is None:
        return None
    return AUTHORITY_LABELS.get(value, value)
