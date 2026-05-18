from __future__ import annotations

import pytest

from app.application.seed_prompt_renderer import SeedPromptRenderer
from app.domain.seed_config import (
    CurrentSolutionsBlock,
    InternalConflictBlock,
    LprAndRolesBlock,
    NoveltyBlock,
    ObjectionItem,
    PersonaSeedConfig,
    ProductBlock,
    SegmentAndScaleBlock,
    StartingParamsBlock,
    TrainingContextBlock,
)


def _minimal_seed() -> PersonaSeedConfig:
    return PersonaSeedConfig(
        training_context=TrainingContextBlock(
            product_area="bukhgalterskiy autsorsing",
            target_segment="rossiyskoe B2B, maliy biznes",
            training_type="cold_call_presentation",
            target_action="request_product_presentation",
            target_action_description="prezentatsiyu autsorsinga",
            target_action_proper_name="Predmetnaya prezentatsiya",
            call_goal="ponyat potrebnosti",
            call_goal_is_not=["audit", "KP"],
            preconditions=["ponyat model"],
            negative_behaviors=["davleniye"],
        ),
        product=ProductBlock(
            category="Autsorsing",
            value_proposition="Vneshnyaya komanda",
            what_manager_sells_now="pokaz",
            full_product_name="perekhod na autsorsing",
            product_area_short="bukhgalteriya",
        ),
        lpr_and_roles=LprAndRolesBlock(
            allowed_roles=["owner", "ceo"],
            role_requirements="vladelets ili direktor",
        ),
        segment_and_scale=SegmentAndScaleBlock(
            industries=["Set klinik", "Proizvodstvo"],
            company_sizes=["42 sotrudnika", "28 sotrudnikov"],
        ),
        triggers=["rost", "otkrytie filiala"],
        pains=["nepryaznost"],
        objections=[
            ObjectionItem(text="Net vremeni", type="anti_presentation"),
            ObjectionItem(text="Dorogo", type="price"),
        ],
        decision_criteria=["spetsifika"],
        hidden_constraints=["luchniy bukhgalter"],
        motivations=["vremya"],
        internal_conflict=InternalConflictBlock(
            side_a=["ne khochu"],
            side_b=["khochu proverit"],
        ),
        current_solutions=CurrentSolutionsBlock(
            solution_types=["shtatnyy"],
            alternative_solutions=["shtatnyy", "autsorsing"],
        ),
        information_gaps=["stoimost"],
        trust_requirements=["keisy"],
        novelty=NoveltyBlock(
            anti_patterns=["sobstvennik + FNS"],
            avoid_clusters=["IT + ceo"],
        ),
        starting_params=StartingParamsBlock(
            initial_openness={"min": 12, "max": 35},
            starting_interest={"min": 18, "max": 35},
            trust_baseline={"min": 12, "max": 30},
            price_sensitivity={"min": 35, "max": 75},
            urgency={"min": 20, "max": 65},
        ),
    )


def test_render_includes_training_context() -> None:
    renderer = SeedPromptRenderer()
    prompt = renderer.render(_minimal_seed())
    assert "bukhgalterskiy autsorsing" in prompt
    assert "rossiyskoe B2B, maliy biznes" in prompt
    assert "cold_call_presentation" in prompt
    assert "request_product_presentation" in prompt
    assert "Predmetnaya prezentatsiya" in prompt
    assert "owner, ceo" in prompt


def test_render_includes_seed_blocks() -> None:
    renderer = SeedPromptRenderer()
    prompt = renderer.render(_minimal_seed())
    assert "[SEED]" in prompt
    assert "Set klinik" in prompt
    assert "42 sotrudnika" in prompt
    assert "rost" in prompt
    assert "nepryaznost" in prompt
    assert "Net vremeni" in prompt
    assert "spetsifika" in prompt
    assert "luchniy bukhgalter" in prompt
    assert "vremya" in prompt
    assert "ne khochu" in prompt
    assert "khochu proverit" in prompt
    assert "shtatnyy" in prompt
    assert "stoimost" in prompt
    assert "keisy" in prompt
    assert "sobstvennik + FNS" in prompt
    assert "IT + ceo" in prompt


def test_render_includes_starting_params() -> None:
    renderer = SeedPromptRenderer()
    prompt = renderer.render(_minimal_seed())
    assert "12" in prompt
    assert "35" in prompt
    assert "18" in prompt
    assert "75" in prompt
    assert "65" in prompt


def test_render_skips_empty_lists() -> None:
    seed = PersonaSeedConfig(
        training_context=TrainingContextBlock(
            product_area="test",
            target_segment="test",
            training_type="cold_call_presentation",
            target_action="request_product_presentation",
            target_action_description="test",
            target_action_proper_name="Test",
            call_goal="test",
        ),
        product=ProductBlock(
            category="Test",
            value_proposition="Test",
            what_manager_sells_now="Test",
            full_product_name="Test",
            product_area_short="test",
        ),
        lpr_and_roles=LprAndRolesBlock(role_requirements="test"),
        starting_params=StartingParamsBlock(
            initial_openness={"min": 10, "max": 20},
            starting_interest={"min": 10, "max": 20},
            trust_baseline={"min": 10, "max": 20},
            price_sensitivity={"min": 10, "max": 20},
            urgency={"min": 10, "max": 20},
        ),
    )
    renderer = SeedPromptRenderer()
    prompt = renderer.render(seed)
    # Should render without errors even when all optional lists are empty
    assert "test" in prompt
    assert "[SEED]" in prompt


def test_render_with_custom_template() -> None:
    renderer = SeedPromptRenderer(template_text="Product: {{product_area}} | Industries: {% for i in industries %}{{i}}{% endfor %}")
    prompt = renderer.render(_minimal_seed())
    assert "Product: bukhgalterskiy autsorsing" in prompt
    assert "Set klinik" in prompt


def test_render_no_orphan_placeholders() -> None:
    """Ensure every {{variable}} in the default template receives a value."""
    renderer = SeedPromptRenderer()
    prompt = renderer.render(_minimal_seed())
    # Simple heuristic: count unrendered jinja2 placeholders
    import re
    orphan_placeholders = re.findall(r"\{\{\s*\w+\s*\}\}", prompt)
    assert not orphan_placeholders, f"Unrendered placeholders found: {orphan_placeholders}"
