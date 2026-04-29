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
        cares_about=["money", "risk", "control", "payback", "time"],
        typical_objections=[
            "We already have things under control.",
            "I do not see why this is necessary.",
            "How much does it cost?",
            "How quickly will this produce a result?",
        ],
    ),
    "purchase_manager": PersonaProfile(
        id="purchase_manager",
        display_name="Purchase Manager",
        role="purchase_manager",
        industry="b2b_services",
        company_size="100-500",
        authority_level="gatekeeper",
        behavior_model="process_oriented",
        cares_about=["price", "terms", "vendor comparison", "risk reduction"],
        typical_objections=[
            "Send a proposal.",
            "We are not reviewing this now.",
            "We already have a contractor.",
            "You need to go through our process.",
        ],
    ),
    "sales_director": PersonaProfile(
        id="sales_director",
        display_name="Sales Director",
        role="sales_director",
        industry="b2b_services",
        company_size="30-100",
        authority_level="influencer",
        behavior_model="dominant_and_direct",
        cares_about=["revenue plan", "conversion", "manager workload", "crm", "lead quality"],
        typical_objections=[
            "The issue is not the managers, it is the leads.",
            "I do not need outside control.",
            "This will distract the team.",
            "How will you measure quality?",
        ],
    ),
}


def list_personas() -> list[PersonaProfile]:
    return list(PERSONAS.values())


def get_persona(persona_id: str) -> PersonaProfile:
    try:
        return PERSONAS[persona_id]
    except KeyError as error:
        raise UnknownPersonaError(f"Unknown persona_id '{persona_id}'.") from error
