from __future__ import annotations

import random

from app.domain.models import PersonaProfile, Scenario

GENERIC_ROLES = [
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

GENERIC_BEHAVIOR_MODELS = [
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

GENERIC_COMPANY_SIZES = ["10-30", "30-100", "100-500", "500+"]
GENERIC_INDUSTRIES = ["manufacturing", "retail", "beauty", "ecommerce", "saas", "distribution", "services"]
GENERIC_CARES_ABOUT = ["ROI", "stability", "team capacity", "predictability", "implementation risk"]
GENERIC_DECISION_CRITERIA = ["business fit", "credibility", "speed", "economics", "clarity of next step"]
GENERIC_CONSTRAINTS = ["Limited time for meetings.", "Needs internal alignment before commitment."]
GENERIC_PROOF_SENSITIVITY = ["relevant cases", "clear numbers", "implementation plan"]
GENERIC_CALL_SCORING = ["discovery depth", "objection handling", "clarity of next step", "context relevance"]

GENERIC_CURRENT_SOLUTIONS = [
    "ручной процесс",
    "Excel + мессенджеры",
    "текущий подрядчик",
    "самописный скрипт",
    "нет полноценного решения",
    "гибрид: частично автоматизировано, частично вручную",
]

GENERIC_ALTERNATIVE_SOLUTIONS = [
    "статус-кво: ничего не менять",
    "нанять сотрудника в штат",
    "доработать текущий процесс",
    "купить конкурирующее решение",
    "отдать задачу внешнему подрядчику",
    "сделать самописное решение",
]

GENERIC_INFORMATION_GAPS = [
    "Думает, что внедрение займёт значительно дольше, чем возможно при пилотном запуске.",
    "Не понимает, чем безопасный первый шаг отличается от полноценного внедрения.",
    "Считает, что новое решение обязательно перегрузит команду.",
    "Не знает, какие доказательства результата можно проверить до покупки.",
]

SCENARIO_BEHAVIOR_HINTS = {
    "first_contact_discovery": "busy_and_short",
    "qualification_and_authority": "formal_and_distant",
    "needs_diagnosis": "analytical_and_cautious",
    "objection_handling": "skeptical_but_rational",
    "price_and_value": "price_sensitive",
    "bad_experience_recovery": "distrustful_due_to_bad_experience",
    "next_step_booking": "interested_but_overloaded",
    "follow_up_after_pause": "friendly_but_distrustful",
}

SCENARIO_OBJECTIONS = {
    "first_contact_discovery": ["We are not looking right now.", "What exactly is this about?"],
    "qualification_and_authority": ["I am not the only one involved.", "You need the right contact first."],
    "needs_diagnosis": ["We need to understand your approach first.", "We already have a process in place."],
    "objection_handling": ["We had a bad experience before.", "I do not want another long pitch."],
    "price_and_value": ["It sounds expensive.", "How is this better than doing nothing?"],
    "bad_experience_recovery": ["Last vendor overpromised.", "Trust is the main problem."],
    "next_step_booking": ["Send something first.", "I am not ready to book time yet."],
    "follow_up_after_pause": ["The priority moved.", "We paused this for now."],
}

SCENARIO_PAINS = {
    "first_contact_discovery": [
        "The team struggles to surface the real situation early.",
        "Initial calls often miss the real stakeholder.",
    ],
    "qualification_and_authority": [
        "Too many conversations happen with the wrong stakeholder.",
        "Time is wasted on contacts who cannot decide.",
    ],
    "needs_diagnosis": [
        "Symptoms are discussed, but root causes stay vague.",
        "Surface-level answers hide the real constraints.",
    ],
    "objection_handling": [
        "Objections stop progress because value is not grounded in context.",
        "Generic responses fail to address specific concerns.",
    ],
    "price_and_value": [
        "Budget concerns dominate before business value is clear.",
        "ROI is demanded before the problem is quantified.",
    ],
    "bad_experience_recovery": [
        "Prior disappointment makes every promise sound weak.",
        "The contact is scanning for proof, not pitches.",
    ],
    "next_step_booking": [
        "Good conversations still end without a concrete next step.",
        "Follow-up momentum fades after the call.",
    ],
    "follow_up_after_pause": [
        "Momentum is lost after long silence.",
        "The contact feels the vendor gave up.",
    ],
}


class UniversalFakePersonaGenerator:
    def __init__(self, seed: int | None = None) -> None:
        """Keep deterministic local persona generation for tests and local development."""
        self._random = random.Random(seed)

    def generate(
        self,
        scenario: Scenario | None = None,
        persona_policy: dict[str, object] | None = None,
        *,
        policy: dict[str, object] | None = None,
    ) -> PersonaProfile:
        """Build a generic B2B hidden persona without product-specific datasets."""
        if persona_policy is not None and policy is not None:
            raise ValueError("Use either 'persona_policy' or 'policy', not both.")

        resolved_policy = persona_policy if persona_policy is not None else policy
        resolved_scenario = scenario
        allowed_roles = self._coerce_allowed_values(
            resolved_policy,
            key="allowed_roles",
            available_values=GENERIC_ROLES,
        )
        role = self._random.choice(allowed_roles or GENERIC_ROLES)
        scenario_id = resolved_scenario.id if resolved_scenario is not None else "first_contact_discovery"
        behavior_model = SCENARIO_BEHAVIOR_HINTS.get(scenario_id, self._random.choice(GENERIC_BEHAVIOR_MODELS))
        target_action = self._string_policy_value(resolved_policy, "target_action") or "confirm_next_step"
        manager_goal = self._string_policy_value(resolved_policy, "manager_training_goal")
        current_context = self._build_current_context(resolved_scenario, manager_goal)
        business_facts = self._build_business_facts(resolved_scenario, target_action)

        return PersonaProfile(
            id=f"generated_{scenario_id}_{role}",
            display_name="Unknown B2B contact",
            role=role,  # type: ignore[arg-type]
            industry=self._random.choice(GENERIC_INDUSTRIES),
            company_size=self._random.choice(GENERIC_COMPANY_SIZES),
            authority_level="final_decider",
            behavior_model=behavior_model,  # type: ignore[arg-type]
            target_action=target_action,
            current_business_context=current_context,
            business_facts=business_facts,
            cares_about=list(GENERIC_CARES_ABOUT),
            current_solution=self._random.choice(GENERIC_CURRENT_SOLUTIONS),
            alternative_solutions=self._pick_alternative_solutions(),
            information_gaps=self._pick_information_gaps(),
            latent_pains=list(SCENARIO_PAINS.get(scenario_id, ["The current process is underperforming.", "No one owns the metric."])),
            buying_motivation=["Reduce uncertainty.", "Find a workable next step."],
            decision_criteria=list(GENERIC_DECISION_CRITERIA),
            hidden_constraints=list(GENERIC_CONSTRAINTS),
            typical_objections=list(SCENARIO_OBJECTIONS.get(scenario_id, ["We need more context first.", "Not the right time."])),
            proof_sensitivity=list(GENERIC_PROOF_SENSITIVITY),
            call_scoring_criteria=list(GENERIC_CALL_SCORING),
            communication_style=self._communication_style_for_behavior(behavior_model),
            initial_openness=self._random.randint(15, 35),
            starting_interest=self._pick_starting_interest(resolved_scenario),
            price_sensitivity=self._pick_price_sensitivity(behavior_model),
            urgency=self._pick_urgency(resolved_scenario),
            trust_baseline=self._pick_trust_baseline(behavior_model),
        )

    def _coerce_allowed_values(
        self,
        persona_policy: dict[str, object] | None,
        *,
        key: str,
        available_values: list[str],
    ) -> list[str]:
        """Restrict string-list policy values to supported fake-generator enums."""
        if persona_policy is None:
            return []
        raw_value = persona_policy.get(key)
        if raw_value is None:
            return []
        if not isinstance(raw_value, list):
            raise ValueError(f"Persona policy '{key}' must be a list.")

        available = set(available_values)
        resolved = [value for value in raw_value if isinstance(value, str) and value in available]
        if not resolved:
            raise ValueError(f"Persona policy '{key}' does not contain supported values.")
        return resolved

    def _string_policy_value(self, persona_policy: dict[str, object] | None, key: str) -> str | None:
        """Read non-empty string overrides from optional fake-generator policy."""
        if persona_policy is None:
            return None
        value = persona_policy.get(key)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _build_current_context(self, scenario: Scenario | None, manager_goal: str | None) -> str:
        """Compose a neutral business context aligned with the selected training format."""
        scenario_name = scenario.name if scenario is not None else "Universal training"
        if manager_goal:
            return f"The contact is evaluating whether this conversation can help with: {manager_goal}."
        return f"The contact is in a '{scenario_name}' training format and expects a relevant, concise conversation."

    def _build_business_facts(self, scenario: Scenario | None, target_action: str) -> list[str]:
        """Expose only generic internal facts that help the simulator stay coherent."""
        if scenario is None:
            return [
                f"Preferred next action: {target_action}.",
                "Generic B2B training scenario.",
            ]
        return [
            f"Training format: {scenario.training_format}.",
            f"Manager goal: {scenario.manager_goal}.",
            f"Preferred next action: {target_action}.",
        ]

    def _communication_style_for_behavior(self, behavior_model: str) -> str:
        """Keep tone consistent with the generated behavior model."""
        styles = {
            "busy_and_short": "Brief and impatient.",
            "formal_and_distant": "Formal and reserved.",
            "analytical_and_cautious": "Analytical and careful.",
            "price_sensitive": "Direct, practical, and cost-aware.",
            "distrustful_due_to_bad_experience": "Guarded and skeptical.",
            "interested_but_overloaded": "Interested but time-constrained.",
        }
        return styles.get(behavior_model, "Calm, pragmatic, and selective.")

    def _pick_starting_interest(self, scenario: Scenario | None) -> int:
        """Keep fallback interest anchored to the selected training format."""
        if scenario is not None:
            return scenario.default_starting_interest
        return self._random.randint(20, 35)

    def _pick_price_sensitivity(self, behavior_model: str) -> int:
        """Bias sensitivity upward for explicitly price-focused personas."""
        if behavior_model == "price_sensitive":
            return self._random.randint(60, 80)
        return self._random.randint(35, 65)

    def _pick_urgency(self, scenario: Scenario | None) -> int:
        """Translate training format pressure into a generic urgency baseline."""
        if scenario is not None and scenario.id in {"bad_experience_recovery", "follow_up_after_pause"}:
            return self._random.randint(25, 45)
        return self._random.randint(20, 55)

    def _pick_trust_baseline(self, behavior_model: str) -> int:
        """Lower starting trust for distrustful recovery-oriented personas."""
        if behavior_model == "distrustful_due_to_bad_experience":
            return self._random.randint(10, 22)
        return self._random.randint(18, 35)

    def _pick_alternative_solutions(self) -> list[str]:
        status_quo = "статус-кво: ничего не менять"
        options = [x for x in GENERIC_ALTERNATIVE_SOLUTIONS if x != status_quo]
        picked = self._random.sample(options, k=2)
        return [status_quo, *picked]

    def _pick_information_gaps(self) -> list[str]:
        return self._random.sample(GENERIC_INFORMATION_GAPS, k=2)


PersonaGenerator = UniversalFakePersonaGenerator
