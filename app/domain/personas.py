from __future__ import annotations

from app.domain.errors import UnknownPersonaError
from app.domain.models import PersonaProfile


PERSONAS: dict[str, PersonaProfile] = {
    "owner": PersonaProfile(
        id="owner",
        display_name="Owner",
        role="owner",
        industry="b2b_services",
        company_size="30-100",
        authority_level="final_decider",
        behavior_model="skeptical_but_rational",
        target_action="book_financial_diagnostic",
        current_business_context="Owner wants more control over how revenue is lost in the process.",
        business_facts=[
            "Mid-size B2B services company.",
            "Owner is involved in daily operations.",
        ],
        cares_about=["money", "risk", "control", "payback", "time"],
        current_solution="Excel + ручной контроль ключевых показателей",
        alternative_solutions=[
            "статус-кво: продолжать как сейчас",
            "нанять операционного директора",
            "внедрить управленческий учёт",
        ],
        information_gaps=[
            "Думает, что внедрение займёт несколько месяцев и остановит продажи.",
            "Не знает, что можно начать с одного отчёта в неделю.",
        ],
        latent_pains=["Conversion is leaking between stages.", "Managers work inconsistently."],
        buying_motivation=["Find the main loss points.", "Recover control over the sales process."],
        decision_criteria=["Clear ROI", "Low disruption", "Practical next step"],
        hidden_constraints=["Team cannot be taken out of work for long."],
        typical_objections=[
            "We already have things under control.",
            "I do not see why this is necessary.",
            "How much does it cost?",
            "How quickly will this produce a result?",
        ],
        proof_sensitivity=["relevant cases", "clear numbers"],
        call_scoring_criteria=["discovery depth", "objection handling", "clarity of next step"],
        communication_style="Direct and skeptical.",
        initial_openness=20,
        starting_interest=25,
        price_sensitivity=60,
        urgency=30,
        trust_baseline=20,
    ),
    "purchase_manager": PersonaProfile(
        id="purchase_manager",
        display_name="Purchase Manager",
        role="purchase_manager",
        industry="b2b_services",
        company_size="100-500",
        authority_level="final_decider",
        behavior_model="process_oriented",
        target_action="book_express_audit",
        current_business_context="Purchase manager filters inbound offers and protects internal process time.",
        business_facts=[
            "Company has a formal vendor selection process.",
            "Multiple departments submit requirements.",
        ],
        cares_about=["price", "terms", "vendor comparison", "risk reduction"],
        current_solution="внутренний реестр подрядчиков + Excel-сравнение",
        alternative_solutions=[
            "статус-кво: оставить текущий реестр",
            "закупить корпоративную платформу для тендеров",
            "расширить штат закупок",
        ],
        information_gaps=[
            "Считает, что любое новое решение потребует обучения всей команды.",
            "Не уверен, что автоматика снизит время на согласование.",
        ],
        latent_pains=["Current vendors are hard to compare objectively.", "No standardized evaluation criteria."],
        buying_motivation=["Reduce supplier risk.", "Improve procurement transparency."],
        decision_criteria=["Process fit", "Risk", "Price"],
        hidden_constraints=["Needs a concise case before escalation."],
        typical_objections=[
            "Send a proposal.",
            "We are not reviewing this now.",
            "We already have a contractor.",
            "You need to go through our process.",
        ],
        proof_sensitivity=["similar cases", "implementation plan"],
        call_scoring_criteria=["process fit", "risk clarity", "next step clarity"],
        communication_style="Short and procedural.",
        initial_openness=15,
        starting_interest=20,
        price_sensitivity=65,
        urgency=20,
        trust_baseline=15,
    ),
    "sales_director": PersonaProfile(
        id="sales_director",
        display_name="Sales Director",
        role="sales_director",
        industry="b2b_services",
        company_size="30-100",
        authority_level="final_decider",
        behavior_model="dominant_and_direct",
        target_action="book_financial_diagnostic",
        current_business_context="Sales director is under pressure on plan execution and inconsistent funnel performance.",
        business_facts=[
            "Funnel conversion dropped 12 % last quarter.",
            "Team of 8 account executives.",
        ],
        cares_about=["revenue plan", "conversion", "manager workload", "crm", "lead quality"],
        current_solution="CRM + ручная отчётность в таблицах",
        alternative_solutions=[
            "статус-кво: продолжать вести отчётность вручную",
            "нанять аналитика в штат",
            "внедрить BI-платформу",
        ],
        information_gaps=[
            "Думает, что диагностика отнимет у команды 2–3 дня.",
            "Не знает, что аудит можно провести за полдня на существующих данных.",
        ],
        latent_pains=["Funnel bottlenecks are unclear.", "Coaching quality is inconsistent."],
        buying_motivation=["Raise conversion without adding headcount.", "Get predictable forecasting."],
        decision_criteria=["Practicality", "Fast diagnostic value", "Clear metrics"],
        hidden_constraints=["Needs owner support for implementation."],
        typical_objections=[
            "The issue is not the managers, it is the leads.",
            "I do not need outside control.",
            "This will distract the team.",
            "How will you measure quality?",
        ],
        proof_sensitivity=["cases from similar teams", "quick pilot"],
        call_scoring_criteria=["funnel clarity", "metric focus", "practical next step"],
        communication_style="Dominant and demanding.",
        initial_openness=25,
        starting_interest=28,
        price_sensitivity=45,
        urgency=45,
        trust_baseline=25,
    ),
}


def list_personas() -> list[PersonaProfile]:
    return list(PERSONAS.values())


def get_persona(persona_id: str) -> PersonaProfile:
    try:
        return PERSONAS[persona_id]
    except KeyError as error:
        raise UnknownPersonaError(f"Unknown persona_id '{persona_id}'.") from error
