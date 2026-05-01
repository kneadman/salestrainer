from __future__ import annotations

import random

from app.domain.models import PersonaProfile
from app.domain.persona_data.accounting_outsourcing import (
    ACCOUNTING_MODELS,
    ACCOUNTING_OUTSOURCING_SCENARIOS,
    ACCOUNTING_SOFTWARE,
    ACCOUNTING_SOFTWARE_MODES,
    LEGAL_FORMS,
    PRIMARY_DOCS_OWNER,
    TAX_SYSTEMS,
)
from app.domain.persona_data.common import (
    BEHAVIOR_MODELS,
    CALL_SCORING_CRITERIA,
    COMMUNICATION_STYLES,
    COMPANY_SIZES,
    DECISION_CRITERIA,
    HIDDEN_CONSTRAINTS,
    OBJECTION_GROUPS,
    PROOF_POINTS,
    ROLES,
)
from app.domain.persona_data.outsourced_cfo import OUTSOURCED_CFO_SCENARIOS

DEFAULT_TARGET_ACTIONS = {
    "accounting_outsourcing": "book_express_audit",
    "outsourced_cfo": "book_financial_diagnostic",
}

PRODUCT_LINE_TARGET_ACTIONS = {
    "accounting_outsourcing": [
        "book_express_audit",
        "get_accounting_data_export",
        "schedule_audit_result_meeting",
        "send_personal_offer_after_audit",
    ],
    "outsourced_cfo": [
        "book_financial_diagnostic",
        "collect_financial_reports",
        "schedule_financial_model_meeting",
        "present_management_reporting_offer",
    ],
}

PRODUCT_SCENARIOS = {
    "accounting_outsourcing": ACCOUNTING_OUTSOURCING_SCENARIOS,
    "outsourced_cfo": OUTSOURCED_CFO_SCENARIOS,
}

ROLE_CARES_ABOUT = {
    "owner": ["контроль", "риски", "деньги", "стабильность"],
    "founder": ["рост", "контроль", "скорость решений", "прибыль"],
    "ceo": ["управляемость", "результат", "риски", "эффективность"],
    "general_director": ["устойчивость", "контроль", "порядок", "результат"],
    "managing_partner": ["прозрачность", "качество сервиса", "контроль", "прибыль"],
    "commercial_director": ["маржа", "продажи", "план", "эффективность"],
    "cfo": ["цифры", "прозрачность", "риск", "денежный поток"],
    "chief_accountant": ["точность", "безопасность", "сроки", "процесс"],
    "operations_director": ["устойчивость", "процессы", "нагрузка команды", "контроль"],
    "sales_director": ["конверсия", "маржа", "управляемость", "результат"],
}

PRODUCT_LINE_INDUSTRIES = {
    "accounting_outsourcing": ["services", "trade", "manufacturing", "construction", "professional_services"],
    "outsourced_cfo": ["wholesale", "distribution", "services", "group_companies", "ecommerce"],
}


class PersonaGenerator:
    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)

    def generate(
        self,
        product_line: str | None = None,
        persona_policy: dict[str, object] | None = None,
        *,
        policy: dict[str, object] | None = None,
    ) -> PersonaProfile:
        if persona_policy is not None and policy is not None:
            raise ValueError("Use either 'persona_policy' or 'policy', not both.")

        resolved_policy = persona_policy if persona_policy is not None else policy
        allowed_product_lines = self._coerce_allowed_values(
            resolved_policy,
            key="allowed_product_lines",
            available_values=PRODUCT_SCENARIOS.keys(),
        )
        resolved_product_line = self._resolve_product_line(product_line, allowed_product_lines)
        scenario_id, scenario_data = self._pick_scenario(resolved_product_line)
        allowed_roles = self._coerce_allowed_values(
            resolved_policy,
            key="allowed_roles",
            available_values=ROLES,
        )
        role = self._random.choice(allowed_roles or ROLES)
        behavior_model = self._pick_behavior_model(scenario_id)
        company_size = self._random.choice(COMPANY_SIZES)
        communication_style = self._random.choice(COMMUNICATION_STYLES)
        proof_sensitivity = list(scenario_data["proof_sensitivity"])
        target_action = self._resolve_target_action(
            resolved_product_line=resolved_product_line,
            persona_policy=resolved_policy,
        )
        current_accounting_model = self._pick_current_accounting_model(resolved_product_line)
        legal_form = self._pick_legal_form(resolved_product_line)
        tax_system = self._pick_tax_system(resolved_product_line)
        accounting_software = self._pick_accounting_software(resolved_product_line)
        accounting_software_mode = self._pick_accounting_software_mode(resolved_product_line)
        primary_docs_owner = self._pick_primary_docs_owner(resolved_product_line)

        return PersonaProfile(
            id=f"generated_{resolved_product_line}_{scenario_id}_{role}",
            display_name="Unknown B2B contact",
            role=role,  # type: ignore[arg-type]
            industry=self._random.choice(PRODUCT_LINE_INDUSTRIES[resolved_product_line]),
            company_size=company_size,
            authority_level="final_decider",
            behavior_model=behavior_model,  # type: ignore[arg-type]
            product_line=resolved_product_line,
            target_action=target_action,
            current_accounting_model=current_accounting_model,
            legal_form=legal_form,
            tax_system=tax_system,
            accounting_software=accounting_software,
            accounting_software_mode=accounting_software_mode,
            primary_docs_owner=primary_docs_owner,
            cares_about=self._pick_cares_about(role, resolved_product_line),
            typical_objections=self._pick_objections(scenario_data),
            current_business_context=scenario_data["current_business_context"],
            latent_pains=list(scenario_data["latent_pains"]),
            buying_motivation=list(scenario_data["buying_motivation"]),
            decision_criteria=self._pick_decision_criteria(),
            hidden_constraints=self._pick_hidden_constraints(scenario_data),
            business_facts=self._build_business_facts(
                resolved_product_line=resolved_product_line,
                scenario_id=scenario_id,
                scenario_data=scenario_data,
                current_accounting_model=current_accounting_model,
                legal_form=legal_form,
                tax_system=tax_system,
                accounting_software=accounting_software,
                primary_docs_owner=primary_docs_owner,
            ),
            proof_sensitivity=proof_sensitivity,
            call_scoring_criteria=list(CALL_SCORING_CRITERIA),
            communication_style=communication_style,
            initial_openness=self._pick_initial_openness(),
            starting_interest=self._pick_starting_interest(scenario_id),
            price_sensitivity=self._pick_price_sensitivity(behavior_model),
            urgency=self._pick_urgency(scenario_id),
            trust_baseline=self._pick_trust_baseline(scenario_id, behavior_model),
        )

    def _resolve_product_line(
        self,
        product_line: str | None,
        allowed_product_lines: list[str],
    ) -> str:
        if product_line is not None:
            if allowed_product_lines and product_line not in allowed_product_lines:
                raise ValueError(f"Product line '{product_line}' is not allowed by persona policy.")
            return product_line
        if allowed_product_lines:
            return self._random.choice(allowed_product_lines)
        return self._random.choice(list(PRODUCT_SCENARIOS.keys()))

    def _resolve_target_action(
        self,
        *,
        resolved_product_line: str,
        persona_policy: dict[str, object] | None,
    ) -> str:
        if persona_policy is not None:
            target_action = persona_policy.get("target_action")
            if isinstance(target_action, str) and target_action:
                return target_action
        return self._random.choice(PRODUCT_LINE_TARGET_ACTIONS[resolved_product_line])

    def _coerce_allowed_values(
        self,
        persona_policy: dict[str, object] | None,
        *,
        key: str,
        available_values,
    ) -> list[str]:
        if persona_policy is None:
            return []
        raw_value = persona_policy.get(key)
        if raw_value is None:
            return []
        if not isinstance(raw_value, list):
            raise ValueError(f"Persona policy '{key}' must be a list.")

        available = {str(value) for value in available_values}
        resolved = [value for value in raw_value if isinstance(value, str) and value in available]
        if not resolved:
            raise ValueError(f"Persona policy '{key}' does not contain supported values.")
        return resolved

    def _pick_scenario(self, product_line: str) -> tuple[str, dict[str, object]]:
        scenarios = PRODUCT_SCENARIOS[product_line]
        scenario_id = self._random.choice(list(scenarios.keys()))
        return scenario_id, scenarios[scenario_id]

    def _pick_behavior_model(self, scenario_id: str) -> str:
        if "bad_experience" in scenario_id:
            return "distrustful_due_to_bad_experience"
        if scenario_id in {"tax_risk_after_requirement", "messy_legal_entities"}:
            return self._random.choice(["analytical_and_cautious", "skeptical_but_rational"])
        if scenario_id in {"cash_gap_problem", "scaling_uncertainty"}:
            return self._random.choice(["interested_but_overloaded", "busy_and_short"])
        return self._random.choice(BEHAVIOR_MODELS)

    def _pick_cares_about(self, role: str, product_line: str) -> list[str]:
        base = list(ROLE_CARES_ABOUT[role])
        if product_line == "accounting_outsourcing":
            base.extend(["налоги", "документы"])
        else:
            base.extend(["маржа", "денежный поток"])
        return base[:5]

    def _pick_objections(self, scenario_data: dict[str, object]) -> list[str]:
        objections = list(scenario_data["typical_objections"])
        objections.extend(self._random.sample(OBJECTION_GROUPS["stalling"], k=1))
        if self._random.random() < 0.5:
            objections.extend(self._random.sample(OBJECTION_GROUPS["price"], k=1))
        if self._random.random() < 0.5:
            objections.extend(self._random.sample(OBJECTION_GROUPS["trust"], k=1))
        return objections

    def _pick_decision_criteria(self) -> list[str]:
        return self._random.sample(DECISION_CRITERIA, k=4)

    def _pick_hidden_constraints(self, scenario_data: dict[str, object]) -> list[str]:
        constraints = list(self._random.sample(HIDDEN_CONSTRAINTS, k=2))
        if "bad_experience" in str(scenario_data["current_business_context"]).lower():
            constraints.append("Есть негативный опыт с подрядчиками.")
        return constraints

    def _build_business_facts(
        self,
        *,
        resolved_product_line: str,
        scenario_id: str,
        scenario_data: dict[str, object],
        current_accounting_model: str,
        legal_form: str,
        tax_system: str,
        accounting_software: str,
        primary_docs_owner: str,
    ) -> list[str]:
        facts = list(scenario_data["business_facts"])
        facts.append(f"Продуктовая линия: {resolved_product_line}.")
        facts.append(f"Сценарий: {scenario_id}.")
        facts.append(f"Текущая модель учета: {current_accounting_model}.")
        if resolved_product_line == "accounting_outsourcing":
            facts.append(f"Оргформа: {legal_form}.")
            facts.append(f"Налоговый режим: {tax_system}.")
            facts.append(f"Учет ведется в: {accounting_software}.")
            facts.append(f"Первичка чаще всего у: {primary_docs_owner}.")
        return facts

    def _pick_current_accounting_model(self, product_line: str) -> str:
        if product_line == "accounting_outsourcing":
            return self._random.choice(ACCOUNTING_MODELS)
        return "unknown"

    def _pick_legal_form(self, product_line: str) -> str:
        if product_line == "accounting_outsourcing":
            return self._random.choice(LEGAL_FORMS)
        return self._random.choice(["ООО", "группа компаний", "несколько юрлиц"])

    def _pick_tax_system(self, product_line: str) -> str:
        if product_line == "accounting_outsourcing":
            return self._random.choice(TAX_SYSTEMS)
        return "неизвестно"

    def _pick_accounting_software(self, product_line: str) -> str:
        if product_line == "accounting_outsourcing":
            return self._random.choice(ACCOUNTING_SOFTWARE)
        return "Excel/таблицы"

    def _pick_accounting_software_mode(self, product_line: str) -> str:
        if product_line == "accounting_outsourcing":
            return self._random.choice(ACCOUNTING_SOFTWARE_MODES)
        return "unknown"

    def _pick_primary_docs_owner(self, product_line: str) -> str:
        if product_line == "accounting_outsourcing":
            return self._random.choice(PRIMARY_DOCS_OWNER)
        return "unknown"

    def _pick_initial_openness(self) -> int:
        return self._random.randint(12, 35)

    def _pick_starting_interest(self, scenario_id: str) -> int:
        if scenario_id in {"revenue_without_profit", "no_management_reporting"}:
            return self._random.randint(28, 45)
        return self._random.randint(18, 45)

    def _pick_price_sensitivity(self, behavior_model: str) -> int:
        if behavior_model == "price_sensitive":
            return self._random.randint(60, 85)
        return self._random.randint(35, 75)

    def _pick_urgency(self, scenario_id: str) -> int:
        if scenario_id in {"tax_risk_after_requirement", "cash_gap_problem"}:
            return self._random.randint(50, 75)
        return self._random.randint(20, 60)

    def _pick_trust_baseline(self, scenario_id: str, behavior_model: str) -> int:
        if "bad_experience" in scenario_id or behavior_model == "distrustful_due_to_bad_experience":
            return self._random.randint(12, 22)
        if scenario_id in {"revenue_without_profit", "no_management_reporting"}:
            return self._random.randint(18, 32)
        return self._random.randint(18, 40)


LEGACY_ROLE_TEMPLATES: dict[str, dict[str, object]] = {}
