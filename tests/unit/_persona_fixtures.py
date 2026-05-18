from __future__ import annotations

from app.domain.models import PersonaProfile


def valid_minimal_persona(**overrides: object) -> PersonaProfile:
    """Return a minimal but fully valid v3.1 persona for test fixtures."""
    defaults: dict[str, object] = {
        "id": "test_persona",
        "display_name": "Test Contact",
        "role": "owner",
        "industry": "b2b",
        "company_size": "30-100",
        "authority_level": "final_decider",
        "behavior_model": "skeptical_but_rational",
        "target_action": "book_meeting",
        "current_business_context": "Growing B2B company looking for process improvements.",
        "business_facts": ["10-50 employees", "Expanding sales team."],
        "cares_about": ["growth", "control", "ROI"],
        "current_solution": "Excel + manual process",
        "alternative_solutions": [
            "статус-кво: продолжать как сейчас",
            "buy a CRM",
        ],
        "information_gaps": [
            "Thinks implementation takes months.",
            "Does not know about pilot programs.",
        ],
        "latent_pains": ["Leads are slipping through.", "Reporting is manual."],
        "buying_motivation": ["Close more deals.", "Reduce manual work."],
        "decision_criteria": ["Ease of use", "Price", "Support"],
        "hidden_constraints": ["Limited budget this quarter."],
        "typical_objections": ["We already have a process.", "Too busy to change."],
        "proof_sensitivity": ["case studies", "free trial"],
        "call_scoring_criteria": ["discovery", "objection handling", "next step"],
        "communication_style": "Direct and brief.",
        "initial_openness": 25,
        "starting_interest": 25,
        "price_sensitivity": 50,
        "urgency": 20,
        "trust_baseline": 20,
    }
    defaults.update(overrides)
    return PersonaProfile(**defaults)  # type: ignore[arg-type]
