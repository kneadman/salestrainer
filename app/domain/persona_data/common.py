from __future__ import annotations

CALL_SCORING_CRITERIA = [
    "manager_took_initiative",
    "manager_collected_required_context",
    "manager_identified_current_solution",
    "manager_understood_current_process",
    "manager_identified_pain",
    "manager_uncovered_information_gap",
    "manager_identified_decision_criteria",
    "manager_identified_constraints",
    "manager_did_not_pitch_too_early",
    "manager_handled_objections",
    "manager_explained_next_step",
    "manager_requested_target_action",
    "manager_fixed_specific_followup_time",
    "manager_collected_contact_channel",
    "manager_avoided_script_robot_style",
]

ROLES = [
    "owner",
    "founder",
    "ceo",
    "general_director",
    "managing_partner",
    "commercial_director",
    "cfo",
    "chief_accountant",
    "operations_director",
    "sales_director",
    "purchase_manager",
]

COMPANY_SIZES = ["1-10", "10-30", "30-100", "100-250", "250-500"]

BEHAVIOR_MODELS = [
    "skeptical_but_rational",
    "dominant_and_direct",
    "price_sensitive",
    "analytical_and_cautious",
    "distrustful_due_to_bad_experience",
    "busy_and_short",
    "friendly_but_defensive",
    "formal_and_distant",
    "interested_but_overloaded",
    "process_oriented",
    "friendly_but_distrustful",
]

COMMUNICATION_STYLES = [
    "Коротко, по делу, без воды.",
    "Скептично, но рационально.",
    "Жестко проверяет компетентность собеседника.",
    "Осторожно, с фокусом на рисках.",
    "Интересуется, но боится лишней нагрузки.",
    "Сначала отмахивается, потом включается при конкретике.",
    "Формально, с дистанцией, без эмоционального включения.",
    "Дружелюбно, но постоянно проверяет практическую пользу.",
]

DECISION_CRITERIA = [
    "понятный эффект",
    "минимум риска",
    "быстрая диагностика",
    "практическая польза",
    "понятная окупаемость",
    "низкая нагрузка на команду",
    "понятный процесс внедрения",
    "доверие к исполнителю",
    "прозрачность ответственности",
    "применимость к специфике бизнеса",
]

HIDDEN_CONSTRAINTS = [
    "Собственник боится потерять контроль над процессом.",
    "Есть негативный опыт с подрядчиками.",
    "Команда может сопротивляться изменениям.",
    "Нет времени на долгую диагностику.",
    "Бюджет ограничен, но проблема уже раздражает.",
    "Нельзя допустить остановку текущих процессов.",
    "Решение нужно объяснить партнеру или руководству.",
    "Клиент не уверен, что сможет быстро предоставить данные.",
    "Клиент боится, что аудит вскроет неприятные ошибки.",
]

OBJECTION_GROUPS = {
    "price": [
        "Сколько стоит?",
        "Из чего складывается стоимость?",
        "Почему так дорого?",
        "Давайте сначала цену.",
    ],
    "trust": [
        "Я вам не доверяю.",
        "Нам то же самое обещали.",
        "Как я пойму, что вы не ошибетесь?",
        "А кто будет отвечать за результат?",
    ],
    "data_security": [
        "Я боюсь давать вам данные.",
        "Зачем удаленный доступ?",
        "Что вы будете смотреть?",
        "А если данные утекут?",
    ],
    "current_vendor_loyalty": [
        "Я доволен текущим подрядчиком.",
        "У нас уже есть проверенный партнёр.",
        "Не хочу портить отношения с текущим поставщиком.",
        "Нам ничего не нужно менять.",
    ],
    "remote_work": [
        "Где вы находитесь?",
        "Как это удалённое сопровождение?",
        "А если нужно срочно?",
        "Как передавать доступы?",
    ],
    "stalling": [
        "Отправьте КП.",
        "Я подумаю.",
        "Сейчас неудобно разговаривать.",
        "Давайте позже.",
        "Мне надо посоветоваться.",
    ],
}

PROOF_POINTS = {
    "process_stability": [
        "регламентная работа с процессами",
        "снижение зависимости от одного человека",
        "контроль сроков и качества",
    ],
    "financial_visibility": [
        "управленческая отчётность",
        "P&L",
        "ДДС",
        "платёжный календарь",
    ],
    "cash_flow_control": [
        "прогнозирование денежных потоков",
        "снижение кассовых разрывов",
        "планирование платежей",
    ],
    "margin_analysis": [
        "анализ маржинальности направлений",
        "поиск убыточных продуктов/клиентов/каналов",
        "понимание реальной прибыли",
    ],
    "relevant_cases": [
        "похожий кейс из отрасли клиента",
        "измеримый результат за известный срок",
        "контакты для обратной связи",
    ],
}
