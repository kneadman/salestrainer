from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.application.report_formatter import build_human_report, build_key_mistakes
from app.domain.models import ClientState, PersonaProfile, TrainingSessionState, TurnEvaluation
from tests.unit._persona_fixtures import valid_minimal_persona


def make_session() -> TrainingSessionState:
    now = datetime.now(tz=UTC)
    return TrainingSessionState(
        session_id=uuid4(),
        scenario_id="sales_audit_cold_outreach",
        status="finished",
        persona=valid_minimal_persona(
            id="generated_persona",
            display_name="Unknown B2B contact",
            role="managing_partner",
            industry="professional_services",
            company_size="20-50",
            behavior_model="analytical_and_cautious",
            communication_style="Спокойный, задаёт уточняющие вопросы.",
            current_business_context="Компания растёт, но контроль финансов и процессов размыт.",
            latent_pains=["Нет прозрачности по юнит-экономике", "Решения принимаются на ощущениях"],
            decision_criteria=["Понятный ROI", "Низкая нагрузка на команду", "Быстрый старт"],
            hidden_constraints=["Нет времени на долгий проект"],
        ),
        interest_score=52,
        stage="need_discovery",
        client_state=ClientState(
            tone="neutral",
            trust=38,
            irritation=10,
            urgency=24,
            price_sensitivity=40,
            open_objections=["Сейчас не до нового проекта"],
            known_pains=[],
            buying_signals=[],
            red_flags=[],
            discovered_role=None,
            discovered_authority_level=None,
            discovered_pains=[],
            discovered_decision_criteria=[],
            discovered_constraints=[],
            discovered_current_process=[],
        ),
        summary="Менеджер задал несколько общих вопросов, но не углубился в диагностику.",
        turns=[],
        turn_evaluations=[
            TurnEvaluation(
                turn_index=1,
                discovery_quality_score=2,
                role_identification_score=1,
                pain_identification_score=1,
                relevance_score=2,
                pressure_score=3,
                objection_handling_score=2,
                next_step_timing_score=2,
                conversation_control_score=3,
                notes=["Вопросы были слишком общими."],
            )
        ],
        recent_turns=[],
        turn_count=1,
        state_version=2,
        created_at=now,
        updated_at=now,
    )


def test_human_report_contains_structured_sections_and_labels() -> None:
    report = build_human_report(make_session())

    assert "Итог тренировки" in report
    assert "Кто был клиент" in report
    assert "Что менеджер выяснил" in report
    assert "Что осталось скрытым" in report
    assert "Оценка навыков" in report
    assert "Ключевые ошибки" in report
    assert "Рекомендации" in report
    assert "управляющий партнёр" in report
    assert "ЛПР" in report


def test_human_report_surfaces_expected_mistakes_and_hides_old_dump_labels() -> None:
    report = build_human_report(make_session())
    mistakes = build_key_mistakes(make_session())

    assert "Не была выяснена роль собеседника." in mistakes
    assert "Не были выявлены реальные боли клиента." in mistakes
    assert "Не была выяснена роль собеседника." in report
    assert "Не были выявлены реальные боли клиента." in report

    assert "Hidden role:" not in report
    assert "Authority level:" not in report
    assert "Discovery score:" not in report
    assert "What worked:" not in report
    assert "Early pitch risk:" not in report
