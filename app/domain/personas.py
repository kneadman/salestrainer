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
        product_line="outsourced_cfo",
        target_action="book_financial_diagnostic",
        cares_about=["money", "risk", "control", "payback", "time"],
        typical_objections=[
            "We already have things under control.",
            "I do not see why this is necessary.",
            "How much does it cost?",
            "How quickly will this produce a result?",
        ],
        current_business_context="Owner wants more control over how revenue is lost in the process.",
        latent_pains=["Conversion is leaking between stages.", "Managers work inconsistently."],
        buying_motivation=["Find the main loss points.", "Recover control over the sales process."],
        decision_criteria=["Clear ROI", "Low disruption", "Practical next step"],
        hidden_constraints=["Team cannot be taken out of work for long."],
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
        product_line="accounting_outsourcing",
        target_action="book_express_audit",
        cares_about=["price", "terms", "vendor comparison", "risk reduction"],
        typical_objections=[
            "Send a proposal.",
            "We are not reviewing this now.",
            "We already have a contractor.",
            "You need to go through our process.",
        ],
        current_business_context="Purchase manager filters inbound offers and protects internal process time.",
        latent_pains=["Current vendors are hard to compare objectively."],
        buying_motivation=["Reduce supplier risk."],
        decision_criteria=["Process fit", "Risk", "Price"],
        hidden_constraints=["Needs a concise case before escalation."],
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
        product_line="outsourced_cfo",
        target_action="book_financial_diagnostic",
        cares_about=["revenue plan", "conversion", "manager workload", "crm", "lead quality"],
        typical_objections=[
            "The issue is not the managers, it is the leads.",
            "I do not need outside control.",
            "This will distract the team.",
            "How will you measure quality?",
        ],
        current_business_context="Sales director is under pressure on plan execution and inconsistent funnel performance.",
        latent_pains=["Funnel bottlenecks are unclear.", "Coaching quality is inconsistent."],
        buying_motivation=["Raise conversion without adding headcount."],
        decision_criteria=["Practicality", "Fast diagnostic value", "Clear metrics"],
        hidden_constraints=["Needs owner support for implementation."],
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
