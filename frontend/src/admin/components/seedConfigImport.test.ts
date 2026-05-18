import { describe, it, expect } from "vitest";
import { validateSeedJson, normalizeSeedJson } from "./seedConfigImport";

const validSeed = {
  training_context: {
    product_area: "Профессиональная косметика",
    target_segment: "B2B beauty",
    training_type: "cold_call_presentation",
    target_action: "request_product_presentation",
    target_action_description: "Запросить презентацию",
    target_action_proper_name: "Презентация",
    call_goal: "Договориться о встрече",
    call_goal_is_not: ["Продать сразу"],
    preconditions: ["Клиент в сегменте"],
    negative_behaviors: ["Давление"],
  },
  product: {
    category: "Косметика",
    value_proposition: "Широкая линейка",
    what_manager_sells_now: "Презентация продукта",
    full_product_name: "ProCosmetics",
    product_area_short: "Косметика",
  },
  lpr_and_roles: {
    allowed_roles: ["owner", "commercial_director"],
    authority_level: "final_decider",
    role_requirements: "Владельцы салонов",
  },
  segment_and_scale: {
    industries: ["Beauty"],
    company_sizes: ["Малый бизнес"],
  },
  triggers: ["Сезонность"],
  pains: ["Высокая себестоимость"],
  objections: [{ text: "Дорого", type: "price" }],
  decision_criteria: ["Цена"],
  hidden_constraints: ["Бюджет"],
  motivations: ["Рост прибыли"],
  internal_conflict: {
    side_a: ["Не хочет менять"],
    side_b: ["Хочет роста"],
  },
  current_solutions: {
    solution_types: ["Текущий поставщик"],
    alternative_solutions: ["Статус-кво"],
  },
  information_gaps: ["Не знает о нас"],
  trust_requirements: ["Отзывы"],
  novelty: {
    anti_patterns: ["Избегать давления"],
    avoid_clusters: ["Кластер А"],
  },
  starting_params: {
    initial_openness: { min: 20, max: 45 },
    starting_interest: { min: 25, max: 50 },
    trust_baseline: { min: 18, max: 35 },
    price_sensitivity: { min: 40, max: 70 },
    urgency: { min: 30, max: 65 },
  },
};

describe("validateSeedJson", () => {
  it("returns empty errors for valid seed", () => {
    expect(validateSeedJson(validSeed)).toEqual([]);
  });

  it("errors on non-object root", () => {
    expect(validateSeedJson(null)).toEqual([
      { field: "", message: "Ожидается JSON-объект" },
    ]);
    expect(validateSeedJson("string")).toEqual([
      { field: "", message: "Ожидается JSON-объект" },
    ]);
  });

  it("errors on missing required blocks", () => {
    const errors = validateSeedJson({});
    expect(errors).toHaveLength(3);
    expect(errors.map((e) => e.field)).toContain("training_context");
    expect(errors.map((e) => e.field)).toContain("product");
    expect(errors.map((e) => e.field)).toContain("starting_params");
  });

  it("errors on invalid training_type", () => {
    const seed = { ...validSeed, training_context: { ...validSeed.training_context, training_type: "invalid" } };
    const errors = validateSeedJson(seed);
    expect(errors).toContainEqual({
      field: "training_context.training_type",
      message: expect.stringContaining("cold_call_presentation"),
    });
  });

  it("errors on invalid target_action", () => {
    const seed = { ...validSeed, training_context: { ...validSeed.training_context, target_action: "invalid" } };
    const errors = validateSeedJson(seed);
    expect(errors).toContainEqual({
      field: "training_context.target_action",
      message: expect.stringContaining("request_product_presentation"),
    });
  });

  it("errors on starting_params min >= max", () => {
    const seed = {
      ...validSeed,
      starting_params: { ...validSeed.starting_params, initial_openness: { min: 50, max: 50 } },
    };
    const errors = validateSeedJson(seed);
    expect(errors).toContainEqual({
      field: "starting_params.initial_openness",
      message: "min должен быть меньше max",
    });
  });

  it("errors on starting_params out of range", () => {
    const seed = {
      ...validSeed,
      starting_params: { ...validSeed.starting_params, initial_openness: { min: -1, max: 101 } },
    };
    const errors = validateSeedJson(seed);
    expect(errors).toContainEqual({
      field: "starting_params.initial_openness",
      message: "Значения должны быть в диапазоне 0–100",
    });
  });

  it("errors on invalid role", () => {
    const seed = { ...validSeed, lpr_and_roles: { ...validSeed.lpr_and_roles, allowed_roles: ["owner", "invalid_role"] } };
    const errors = validateSeedJson(seed);
    expect(errors).toContainEqual({
      field: "lpr_and_roles.allowed_roles",
      message: expect.stringContaining("invalid_role"),
    });
  });

  it("errors on invalid objection type", () => {
    const seed = { ...validSeed, objections: [{ text: "X", type: "invalid" }] };
    const errors = validateSeedJson(seed);
    expect(errors).toContainEqual({
      field: "objections[0].type",
      message: expect.stringContaining("anti_presentation"),
    });
  });
});

describe("normalizeSeedJson", () => {
  it("returns normalized SeedConfig for valid input", () => {
    const result = normalizeSeedJson(validSeed);
    expect(result).not.toBeNull();
    expect(result!.training_context.product_area).toBe("Профессиональная косметика");
    expect(result!.starting_params.initial_openness).toEqual({ min: 20, max: 45 });
    expect(result!.objections).toEqual([{ text: "Дорого", type: "price" }]);
  });

  it("fills defaults for missing optional fields", () => {
    const minimal = {
      training_context: validSeed.training_context,
      product: validSeed.product,
      starting_params: validSeed.starting_params,
    };
    const result = normalizeSeedJson(minimal);
    expect(result).not.toBeNull();
    expect(result!.triggers).toEqual([]);
    expect(result!.lpr_and_roles.allowed_roles).toEqual([]);
    expect(result!.novelty.anti_patterns).toEqual([]);
  });

  it("returns null for non-object", () => {
    expect(normalizeSeedJson(null)).toBeNull();
    expect(normalizeSeedJson("string")).toBeNull();
  });

  it("coerces string list fields from semicolon-separated string", () => {
    const seed = {
      ...validSeed,
      triggers: "A; B; C",
    };
    const result = normalizeSeedJson(seed);
    expect(result!.triggers).toEqual(["A", "B", "C"]);
  });
});
