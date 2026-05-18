from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Seed config accepts free-form strings for these fields;
# strict enum validation is intentionally relaxed so the generator
# can introduce new values without backend changes.
TrainingType = str
TargetAction = str
Role = str
ObjectionType = str


class TrainingContextBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_area: str
    target_segment: str
    training_type: TrainingType
    target_action: TargetAction
    target_action_description: str
    target_action_proper_name: str
    call_goal: str
    call_goal_is_not: list[str] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    negative_behaviors: list[str] = Field(default_factory=list)


class ProductBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    value_proposition: str
    what_manager_sells_now: str
    full_product_name: str
    product_area_short: str


class LprAndRolesBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed_roles: list[Role] = Field(default_factory=list)
    authority_level: str = "final_decider"
    role_requirements: str


class SegmentAndScaleBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industries: list[str] = Field(default_factory=list)
    company_sizes: list[str] = Field(default_factory=list)


class ObjectionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    type: ObjectionType = "anti_presentation"


class InternalConflictBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    side_a: list[str] = Field(default_factory=list)
    side_b: list[str] = Field(default_factory=list)


class CurrentSolutionsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    solution_types: list[str] = Field(default_factory=list)
    alternative_solutions: list[str] = Field(default_factory=list)


class NoveltyBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anti_patterns: list[str] = Field(default_factory=list)
    avoid_clusters: list[str] = Field(default_factory=list)


class StartingParamsBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initial_openness: dict[str, int]
    starting_interest: dict[str, int]
    trust_baseline: dict[str, int]
    price_sensitivity: dict[str, int]
    urgency: dict[str, int]

    @model_validator(mode="after")
    def _check_ranges(self) -> "StartingParamsBlock":
        for field_name, bounds in self:
            mn = bounds.get("min")
            mx = bounds.get("max")
            if mn is None or mx is None:
                raise ValueError(f"{field_name} must have 'min' and 'max'")
            if not (0 <= mn <= 100 and 0 <= mx <= 100):
                raise ValueError(f"{field_name} bounds must be within 0..100")
            if mn >= mx:
                raise ValueError(f"{field_name} min must be less than max")
        return self


class PersonaSeedConfig(BaseModel):
    """Structured 16-block seed configuration for persona generation.

    Each block corresponds to a thematic section rendered into the
    universal prompt template.  Product-specific data only — no
    instructions or selection logic.
    """

    model_config = ConfigDict(extra="forbid")

    training_context: TrainingContextBlock
    product: ProductBlock
    lpr_and_roles: LprAndRolesBlock
    segment_and_scale: SegmentAndScaleBlock = Field(default_factory=SegmentAndScaleBlock)
    triggers: list[str] = Field(default_factory=list)
    pains: list[str] = Field(default_factory=list)
    objections: list[ObjectionItem] = Field(default_factory=list)
    decision_criteria: list[str] = Field(default_factory=list)
    hidden_constraints: list[str] = Field(default_factory=list)
    motivations: list[str] = Field(default_factory=list)
    internal_conflict: InternalConflictBlock = Field(default_factory=InternalConflictBlock)
    current_solutions: CurrentSolutionsBlock = Field(default_factory=CurrentSolutionsBlock)
    information_gaps: list[str] = Field(default_factory=list)
    trust_requirements: list[str] = Field(default_factory=list)
    novelty: NoveltyBlock = Field(default_factory=NoveltyBlock)
    starting_params: StartingParamsBlock
