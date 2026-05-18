from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.seed_config import (
    LprAndRolesBlock,
    ObjectionItem,
    PersonaSeedConfig,
    StartingParamsBlock,
    TrainingContextBlock,
)


def _minimal_training_context() -> TrainingContextBlock:
    return TrainingContextBlock(
        product_area="bukhgalterskiy autsorsing",
        target_segment="rossiyskoe B2B, maliy biznes",
        training_type="cold_call_presentation",
        target_action="request_product_presentation",
        target_action_description="prezentatsiyu autsorsinga",
        target_action_proper_name="Predmetnaya prezentatsiya",
        call_goal="ponyat potrebnosti klienta",
    )


def _minimal_product() -> dict:
    return {
        "category": "Autsorsing",
        "value_proposition": "Vneshnyaya komanda",
        "what_manager_sells_now": "pokaz",
        "full_product_name": "perekhod na autsorsing",
        "product_area_short": "bukhgalteriya",
    }


def _minimal_starting_params() -> StartingParamsBlock:
    return StartingParamsBlock(
        initial_openness={"min": 12, "max": 35},
        starting_interest={"min": 18, "max": 35},
        trust_baseline={"min": 12, "max": 30},
        price_sensitivity={"min": 35, "max": 75},
        urgency={"min": 20, "max": 65},
    )


def test_valid_minimal_seed_config() -> None:
    seed = PersonaSeedConfig(
        training_context=_minimal_training_context(),
        product=_minimal_product(),
        lpr_and_roles={"role_requirements": "vladelets ili direktor"},
        starting_params=_minimal_starting_params(),
    )
    assert seed.training_context.product_area == "bukhgalterskiy autsorsing"
    assert seed.segment_and_scale.industries == []


def test_invalid_training_type_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TrainingContextBlock(
            product_area="x",
            target_segment="y",
            training_type="invalid_type",  # type: ignore[arg-type]
            target_action="request_product_presentation",
            target_action_description="z",
            target_action_proper_name="Z",
            call_goal="goal",
        )
    assert "training_type" in str(exc_info.value)


def test_invalid_target_action_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TrainingContextBlock(
            product_area="x",
            target_segment="y",
            training_type="cold_call_presentation",
            target_action="buy_now",  # type: ignore[arg-type]
            target_action_description="z",
            target_action_proper_name="Z",
            call_goal="goal",
        )
    assert "target_action" in str(exc_info.value)


def test_invalid_role_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        LprAndRolesBlock(
            allowed_roles=["invalid_role"],  # type: ignore[list-item]
            role_requirements="test",
        )
    assert "allowed_roles" in str(exc_info.value)


def test_starting_params_range_validation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        StartingParamsBlock(
            initial_openness={"min": 80, "max": 20},
            starting_interest={"min": 18, "max": 35},
            trust_baseline={"min": 12, "max": 30},
            price_sensitivity={"min": 35, "max": 75},
            urgency={"min": 20, "max": 65},
        )
    assert "min must be less than max" in str(exc_info.value)


def test_starting_params_bounds_validation() -> None:
    with pytest.raises(ValidationError) as exc_info:
        StartingParamsBlock(
            initial_openness={"min": -1, "max": 35},
            starting_interest={"min": 18, "max": 35},
            trust_baseline={"min": 12, "max": 30},
            price_sensitivity={"min": 35, "max": 75},
            urgency={"min": 20, "max": 65},
        )
    assert "within 0..100" in str(exc_info.value)


def test_objection_item_defaults_to_anti_presentation() -> None:
    obj = ObjectionItem(text="Net vremeni")
    assert obj.type == "anti_presentation"


def test_full_seed_config_with_orientation_lists() -> None:
    seed = PersonaSeedConfig(
        training_context=_minimal_training_context(),
        product=_minimal_product(),
        lpr_and_roles={
            "allowed_roles": ["owner", "ceo"],
            "role_requirements": "vladelets ili generalnyy direktor",
        },
        segment_and_scale={
            "industries": ["Set klinik", "Proizvodstvo"],
            "company_sizes": ["42 sotrudnika", "28 sotrudnikov"],
        },
        triggers=["rost kompanii", "otkrytie filiala"],
        pains=["nepryaznost", "peregruzka"],
        objections=[
            {"text": "Net vremeni", "type": "anti_presentation"},
            {"text": "Dorogo", "type": "price"},
        ],
        decision_criteria=["spetsifika", "prozrachnost"],
        hidden_constraints=["luchniy bukhgalter"],
        motivations=["vremya", "spokoystvie"],
        internal_conflict={
            "side_a": ["ne khochu menyat"],
            "side_b": ["khochu proverit"],
        },
        current_solutions={
            "solution_types": ["shtatnyy bukhgalter"],
            "alternative_solutions": ["shtatnyy bukhgalter", "autsorsing"],
        },
        information_gaps=["stoimost", "process"],
        trust_requirements=["keisy", "voprosy"],
        novelty={
            "anti_patterns": ["sobstvennik + FNS"],
            "avoid_clusters": ["IT + ceo"],
        },
        starting_params=_minimal_starting_params(),
    )
    assert len(seed.objections) == 2
    assert seed.novelty.anti_patterns[0] == "sobstvennik + FNS"
