import type { SeedConfig } from "../types";

export type ValidationError = { field: string; message: string };

const PARAM_NAMES = [
  "initial_openness",
  "starting_interest",
  "trust_baseline",
  "price_sensitivity",
  "urgency",
] as const;

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

export function validateSeedJson(data: unknown): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!isPlainObject(data)) {
    return [{ field: "", message: "Ожидается JSON-объект" }];
  }

  // Обязательные блоки
  for (const block of ["training_context", "product", "starting_params"]) {
    if (!(block in data)) {
      errors.push({ field: block, message: `Отсутствует обязательный блок: ${block}` });
    }
  }

  // training_context — enum-валидация отключена; фактическая проверка на совести backend
  const tc = data.training_context;
  if (isPlainObject(tc)) {
    // collectEnumErrors disabled: accept any string from generator
  }

  // starting_params
  const params = data.starting_params;
  if (isPlainObject(params)) {
    for (const name of PARAM_NAMES) {
      const p = params[name];
      if (!isPlainObject(p)) {
        errors.push({
          field: `starting_params.${name}`,
          message: "Должен быть объектом {min: number, max: number}",
        });
        continue;
      }
      const mn = p.min;
      const mx = p.max;
      if (typeof mn !== "number" || typeof mx !== "number") {
        errors.push({
          field: `starting_params.${name}`,
          message: "min и max должны быть числами",
        });
        continue;
      }
      if (mn < 0 || mx > 100) {
        errors.push({
          field: `starting_params.${name}`,
          message: "Значения должны быть в диапазоне 0–100",
        });
      }
      if (mn >= mx) {
        errors.push({
          field: `starting_params.${name}`,
          message: "min должен быть меньше max",
        });
      }
    }
  }

  // lpr_and_roles — enum-валидация отключена; фактическая проверка на совести backend
  const lpr = data.lpr_and_roles;
  if (isPlainObject(lpr)) {
    // collectEnumErrors disabled: accept any string from generator
  }

  // objections — enum-валидация отключена; фактическая проверка на совести backend
  const objections = data.objections;
  if (Array.isArray(objections)) {
    objections.forEach((o, i) => {
      if (!isPlainObject(o)) {
        errors.push({ field: `objections[${i}]`, message: "Должен быть объектом" });
        return;
      }
      // collectEnumErrors disabled: accept any string from generator
    });
  }

  return errors;
}

function ensureStringArray(value: unknown): string[] {
  if (isStringArray(value)) return value;
  if (typeof value === "string") {
    return value
      .split(";")
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return [];
}

function ensureObjectionArray(value: unknown): SeedConfig["objections"] {
  if (!Array.isArray(value)) return [];
  return value
    .filter(isPlainObject)
    .map((o) => ({
      text: typeof o.text === "string" ? o.text : "",
      type: typeof o.type === "string" ? o.type : "anti_presentation",
    }));
}

function ensureStartingParam(value: unknown): { min: number; max: number } | undefined {
  if (!isPlainObject(value)) return undefined;
  const mn = value.min;
  const mx = value.max;
  if (typeof mn !== "number" || typeof mx !== "number") return undefined;
  return { min: mn, max: mx };
}

export function normalizeSeedJson(data: unknown): SeedConfig | null {
  if (!isPlainObject(data)) return null;

  const tc = isPlainObject(data.training_context) ? data.training_context : {};
  const prod = isPlainObject(data.product) ? data.product : {};
  const lpr = isPlainObject(data.lpr_and_roles) ? data.lpr_and_roles : {};
  const seg = isPlainObject(data.segment_and_scale) ? data.segment_and_scale : {};
  const conflict = isPlainObject(data.internal_conflict) ? data.internal_conflict : {};
  const solutions = isPlainObject(data.current_solutions) ? data.current_solutions : {};
  const novelty = isPlainObject(data.novelty) ? data.novelty : {};
  const params = isPlainObject(data.starting_params) ? data.starting_params : {};

  const seed: SeedConfig = {
    training_context: {
      product_area: typeof tc.product_area === "string" ? tc.product_area : "",
      target_segment: typeof tc.target_segment === "string" ? tc.target_segment : "",
      training_type: typeof tc.training_type === "string" ? tc.training_type : "cold_call_presentation",
      target_action: typeof tc.target_action === "string" ? tc.target_action : "request_product_presentation",
      target_action_description: typeof tc.target_action_description === "string" ? tc.target_action_description : "",
      target_action_proper_name: typeof tc.target_action_proper_name === "string" ? tc.target_action_proper_name : "",
      call_goal: typeof tc.call_goal === "string" ? tc.call_goal : "",
      call_goal_is_not: ensureStringArray(tc.call_goal_is_not),
      preconditions: ensureStringArray(tc.preconditions),
      negative_behaviors: ensureStringArray(tc.negative_behaviors),
    },
    product: {
      category: typeof prod.category === "string" ? prod.category : "",
      value_proposition: typeof prod.value_proposition === "string" ? prod.value_proposition : "",
      what_manager_sells_now: typeof prod.what_manager_sells_now === "string" ? prod.what_manager_sells_now : "",
      full_product_name: typeof prod.full_product_name === "string" ? prod.full_product_name : "",
      product_area_short: typeof prod.product_area_short === "string" ? prod.product_area_short : "",
    },
    lpr_and_roles: {
      allowed_roles: ensureStringArray(lpr.allowed_roles),
      authority_level: typeof lpr.authority_level === "string" ? lpr.authority_level : "final_decider",
      role_requirements: typeof lpr.role_requirements === "string" ? lpr.role_requirements : "",
    },
    segment_and_scale: {
      industries: ensureStringArray(seg.industries),
      company_sizes: ensureStringArray(seg.company_sizes),
    },
    triggers: ensureStringArray(data.triggers),
    pains: ensureStringArray(data.pains),
    objections: ensureObjectionArray(data.objections),
    decision_criteria: ensureStringArray(data.decision_criteria),
    hidden_constraints: ensureStringArray(data.hidden_constraints),
    motivations: ensureStringArray(data.motivations),
    internal_conflict: {
      side_a: ensureStringArray(conflict.side_a),
      side_b: ensureStringArray(conflict.side_b),
    },
    current_solutions: {
      solution_types: ensureStringArray(solutions.solution_types),
      alternative_solutions: ensureStringArray(solutions.alternative_solutions),
    },
    information_gaps: ensureStringArray(data.information_gaps),
    trust_requirements: ensureStringArray(data.trust_requirements),
    novelty: {
      anti_patterns: ensureStringArray(novelty.anti_patterns),
      avoid_clusters: ensureStringArray(novelty.avoid_clusters),
    },
    starting_params: {
      initial_openness: ensureStartingParam(params.initial_openness) ?? { min: 12, max: 35 },
      starting_interest: ensureStartingParam(params.starting_interest) ?? { min: 18, max: 35 },
      trust_baseline: ensureStartingParam(params.trust_baseline) ?? { min: 12, max: 30 },
      price_sensitivity: ensureStartingParam(params.price_sensitivity) ?? { min: 35, max: 75 },
      urgency: ensureStartingParam(params.urgency) ?? { min: 20, max: 65 },
    },
  };

  return seed;
}
