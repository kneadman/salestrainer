# Запрос на генерацию B2B-персоны

## Контекст тренировки

- **Продуктовая область**: {{product_area}}
- **Целевой сегмент**: {{target_segment}}
- **Тип тренировки**: {{training_type}}
- **Целевое действие**: {{target_action}}
- **Описание целевого действия**: {{target_action_description}}
- **Правильное название действия**: {{target_action_proper_name}}
- **Цель звонка**: {{call_goal}}

{% if call_goal_is_not %}### Что НЕ является целью звонка
{% for item in call_goal_is_not %}
- {{item}}
{% endfor %}
{% endif %}

{% if preconditions %}### Предусловия для целевого действия
{% for item in preconditions %}
- {{item}}
{% endfor %}
{% endif %}

{% if negative_behaviors %}### Нежелательные поведения менеджера
{% for item in negative_behaviors %}
- {{item}}
{% endfor %}
{% endif %}

## Продукт

- **Категория**: {{category}}
- **Ценностное предложение**: {{value_proposition}}
- **Что менеджер продает сейчас**: {{what_manager_sells_now}}
- **Полное название продукта**: {{full_product_name}}
- **Краткое название области**: {{product_area_short}}

## ЛПР и роли

- **Допустимые роли**: {{allowed_roles | join(', ') if allowed_roles else '—'}}
- **Уровень полномочий**: {{authority_level}}
- **Требования к роли**: {{role_requirements}}

---

[SEED] ТИПИЧНЫЕ ОТРАСЛИ И РАЗМЕРЫ КОМПАНИЙ:

{% if industries %}### Примеры отраслей
{% for item in industries %}
- {{item}}
{% endfor %}
{% endif %}

{% if company_sizes %}### Примеры размеров компаний
{% for item in company_sizes %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] ТРИГГЕРЫ АКТУАЛЬНОСТИ:
{% if triggers %}
{% for item in triggers %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] БОЛИ КЛИЕНТА:
{% if pains %}
{% for item in pains %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] ТИПИЧНЫЕ ВОЗРАЖЕНИЯ:
{% if objections %}
{% for item in objections %}
- {{item.text}} (тип: {{item.type}})
{% endfor %}
{% endif %}

---

[SEED] КРИТЕРИИ ПРИНЯТИЯ РЕШЕНИЯ:
{% if decision_criteria %}
{% for item in decision_criteria %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] СКРЫТЫЕ ОГРАНИЧЕНИЯ:
{% if hidden_constraints %}
{% for item in hidden_constraints %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] МОТИВАЦИЯ К ПОКУПКЕ:
{% if motivations %}
{% for item in motivations %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] ВНУТРЕННИЙ КОНФЛИКТ:

{% if conflict_side_a %}### Почему клиент НЕ хочет менять (сторона А)
{% for item in conflict_side_a %}
- {{item}}
{% endfor %}
{% endif %}

{% if conflict_side_b %}### Почему у клиента есть причина рассмотреть варианты (сторона Б)
{% for item in conflict_side_b %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] ТЕКУЩИЕ РЕШЕНИЯ И АЛЬТЕРНАТИВЫ:

{% if solution_types %}### Типы текущих решений
{% for item in solution_types %}
- {{item}}
{% endfor %}
{% endif %}

{% if alternative_solutions %}### Альтернативные решения (включая статус-кво)
{% for item in alternative_solutions %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] ИНФОРМАЦИОННЫЕ ПРОБЕЛЫ:
{% if information_gaps %}
{% for item in information_gaps %}
- {{item}}
{% endfor %}
{% endif %}

---

[SEED] ФАКТОРЫ ДОВЕРИЯ:
{% if trust_factors %}
{% for item in trust_factors %}
- {{item}}
{% endfor %}
{% endif %}

---

## Антипаттерны и кластеры для избегания

{% if anti_patterns %}### Антипаттерны
{% for item in anti_patterns %}
- {{item}}
{% endfor %}
{% endif %}

{% if avoid_clusters %}### Кластеры, которых следует избегать
{% for item in avoid_clusters %}
- {{item}}
{% endfor %}
{% endif %}

---

## Стартовые параметры

- **Начальная открытость**: от {{initial_openness_min}} до {{initial_openness_max}}
- **Стартовый интерес**: от {{starting_interest_min}} до {{starting_interest_max}}
- **Базовое доверие**: от {{trust_baseline_min}} до {{trust_baseline_max}}
- **Ценовая чувствительность**: от {{price_sensitivity_min}} до {{price_sensitivity_max}}
- **Срочность**: от {{urgency_min}} до {{urgency_max}}

---

## Технические требования

- Верни строго один JSON-объект `PersonaGenerationOutput`.
- Все описательные текстовые поля на русском языке.
- Не добавляй markdown, комментарии или текст вне JSON.
- Не включай запрещенные поля: internal_conflict, status_quo_alternative, current_accounting_model, legal_form, tax_system, accounting_software, accounting_software_mode, primary_docs_owner, product_line, segment, profile.
