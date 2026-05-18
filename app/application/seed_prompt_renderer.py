from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Template

from app.domain.seed_config import PersonaSeedConfig

logger = logging.getLogger(__name__)

_DEFAULT_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "prompts" / "persona_seed_template.md"


class SeedPromptRenderer:
    """Render a seed configuration into the universal persona-generation prompt."""

    def __init__(self, template_text: str | None = None) -> None:
        """Load template from disk or accept an override for testing."""
        text = template_text if template_text is not None else _load_template_text()
        self._template = Template(text, trim_blocks=True, lstrip_blocks=True, autoescape=False)

    def render(self, seed: PersonaSeedConfig) -> str:
        """Return a fully-populated prompt string ready for the LLM."""
        context = _build_template_context(seed)
        result: str = self._template.render(context)
        return result.strip()


def _load_template_text() -> str:
    if not _DEFAULT_TEMPLATE_PATH.exists():
        logger.warning("persona_seed_template.md not found at %s", _DEFAULT_TEMPLATE_PATH)
        raise FileNotFoundError(f"Template file missing: {_DEFAULT_TEMPLATE_PATH}")
    return _DEFAULT_TEMPLATE_PATH.read_text(encoding="utf-8")


def _build_template_context(seed: PersonaSeedConfig) -> dict[str, object]:
    """Flatten a PersonaSeedConfig into the variable dictionary expected by the template."""
    ctx: dict[str, object] = {}

    # Block 1: training_context (FIXED)
    tc = seed.training_context
    ctx["product_area"] = tc.product_area
    ctx["target_segment"] = tc.target_segment
    ctx["training_type"] = tc.training_type
    ctx["target_action"] = tc.target_action
    ctx["target_action_description"] = tc.target_action_description
    ctx["target_action_proper_name"] = tc.target_action_proper_name
    ctx["call_goal"] = tc.call_goal
    ctx["call_goal_is_not"] = tc.call_goal_is_not
    ctx["preconditions"] = tc.preconditions
    ctx["negative_behaviors"] = tc.negative_behaviors

    # Block 2: product (FIXED)
    pr = seed.product
    ctx["category"] = pr.category
    ctx["value_proposition"] = pr.value_proposition
    ctx["what_manager_sells_now"] = pr.what_manager_sells_now
    ctx["full_product_name"] = pr.full_product_name
    ctx["product_area_short"] = pr.product_area_short

    # Block 3: lpr_and_roles (FIXED)
    lr = seed.lpr_and_roles
    ctx["allowed_roles"] = lr.allowed_roles
    ctx["authority_level"] = lr.authority_level
    ctx["role_requirements"] = lr.role_requirements

    # Block 4: segment_and_scale (ORIENTATION LIST)
    ss = seed.segment_and_scale
    ctx["industries"] = ss.industries
    ctx["company_sizes"] = ss.company_sizes

    # Block 5: triggers
    ctx["triggers"] = seed.triggers

    # Block 6: pains
    ctx["pains"] = seed.pains

    # Block 7: objections (with type)
    ctx["objections"] = [{"text": o.text, "type": o.type} for o in seed.objections]

    # Block 8: decision_criteria
    ctx["decision_criteria"] = seed.decision_criteria

    # Block 9: hidden_constraints
    ctx["hidden_constraints"] = seed.hidden_constraints

    # Block 10: motivations
    ctx["motivations"] = seed.motivations

    # Block 11: internal_conflict
    ic = seed.internal_conflict
    ctx["conflict_side_a"] = ic.side_a
    ctx["conflict_side_b"] = ic.side_b

    # Block 12: current_solutions
    cs = seed.current_solutions
    ctx["solution_types"] = cs.solution_types
    ctx["alternative_solutions"] = cs.alternative_solutions

    # Block 13: information_gaps
    ctx["information_gaps"] = seed.information_gaps

    # Block 14: trust_requirements
    ctx["trust_factors"] = seed.trust_requirements

    # Block 15: novelty
    nv = seed.novelty
    ctx["anti_patterns"] = nv.anti_patterns
    ctx["avoid_clusters"] = nv.avoid_clusters

    # Block 16: starting_params (FIXED)
    sp = seed.starting_params
    ctx["initial_openness_min"] = sp.initial_openness.get("min", 12)
    ctx["initial_openness_max"] = sp.initial_openness.get("max", 35)
    ctx["starting_interest_min"] = sp.starting_interest.get("min", 18)
    ctx["starting_interest_max"] = sp.starting_interest.get("max", 35)
    ctx["trust_baseline_min"] = sp.trust_baseline.get("min", 12)
    ctx["trust_baseline_max"] = sp.trust_baseline.get("max", 30)
    ctx["price_sensitivity_min"] = sp.price_sensitivity.get("min", 35)
    ctx["price_sensitivity_max"] = sp.price_sensitivity.get("max", 75)
    ctx["urgency_min"] = sp.urgency.get("min", 20)
    ctx["urgency_max"] = sp.urgency.get("max", 65)

    return ctx
