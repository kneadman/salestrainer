import { useRef, useState } from "react";
import { TagInput } from "./TagInput";
import type { SeedConfig } from "../types";
import { validateSeedJson, normalizeSeedJson, type ValidationError } from "./seedConfigImport";

const TRAINING_TYPES = [
  { value: "cold_call_presentation", label: "Холодный звонок / Презентация" },
  { value: "inbound_lead_qualification", label: "Входящий лид / Квалификация" },
  { value: "follow_up_after_meeting", label: "Follow-up после встречи" },
  { value: "reactivation_call", label: "Реактивация" },
  { value: "objection_handling", label: "Работа с возражениями" },
  { value: "upsell_existing_client", label: "Апселл существующему клиенту" },
  { value: "first_contact_after_event", label: "Первый контакт после мероприятия" },
  { value: "referral_call", label: "Реферальный звонок" },
];

const TARGET_ACTIONS = [
  { value: "request_product_presentation", label: "Запросить продуктовую презентацию" },
  { value: "schedule_demo_meeting", label: "Назначить демо-встречу" },
  { value: "agree_to_proposal_review", label: "Согласие на просмотр предложения" },
  { value: "introduce_to_decision_maker", label: "Познакомить с ЛПР" },
  { value: "agree_to_pilot_project", label: "Согласие на пилот" },
  { value: "provide_documents_for_audit", label: "Предоставить документы для аудита" },
  { value: "schedule_second_call", label: "Назначить второй звонок" },
  { value: "agree_to_cost_estimate", label: "Согласие на оценку стоимости" },
];

function defaultSeedConfig(): SeedConfig {
  return {
    training_context: {
      product_area: "",
      target_segment: "",
      training_type: "cold_call_presentation",
      target_action: "request_product_presentation",
      target_action_description: "",
      target_action_proper_name: "",
      call_goal: "",
      call_goal_is_not: [],
      preconditions: [],
      negative_behaviors: [],
    },
    product: {
      category: "",
      value_proposition: "",
      what_manager_sells_now: "",
      full_product_name: "",
      product_area_short: "",
    },
    lpr_and_roles: {
      allowed_roles: [],
      authority_level: "final_decider",
      role_requirements: "",
    },
    segment_and_scale: { industries: [], company_sizes: [] },
    triggers: [],
    pains: [],
    objections: [],
    decision_criteria: [],
    hidden_constraints: [],
    motivations: [],
    internal_conflict: { side_a: [], side_b: [] },
    current_solutions: { solution_types: [], alternative_solutions: [] },
    information_gaps: [],
    trust_requirements: [],
    novelty: { anti_patterns: [], avoid_clusters: [] },
    starting_params: {
      initial_openness: { min: 12, max: 35 },
      starting_interest: { min: 18, max: 35 },
      trust_baseline: { min: 12, max: 30 },
      price_sensitivity: { min: 35, max: 75 },
      urgency: { min: 20, max: 65 },
    },
  };
}

export function SeedConfigForm(props: {
  seedConfig: SeedConfig | null;
  onChange: (seed: SeedConfig) => void;
}) {
  const seed = props.seedConfig ?? defaultSeedConfig();
  const [importErrors, setImportErrors] = useState<ValidationError[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const update = (patch: Partial<SeedConfig>) => {
    props.onChange({ ...seed, ...patch });
  };

  const updateTrainingContext = (patch: Partial<SeedConfig["training_context"]>) => {
    update({ training_context: { ...seed.training_context, ...patch } });
  };

  const updateProduct = (patch: Partial<SeedConfig["product"]>) => {
    update({ product: { ...seed.product, ...patch } });
  };

  const updateLpr = (patch: Partial<SeedConfig["lpr_and_roles"]>) => {
    update({ lpr_and_roles: { ...seed.lpr_and_roles, ...patch } });
  };

  const updateSegment = (patch: Partial<SeedConfig["segment_and_scale"]>) => {
    update({ segment_and_scale: { ...seed.segment_and_scale, ...patch } });
  };

  const updateConflict = (patch: Partial<SeedConfig["internal_conflict"]>) => {
    update({ internal_conflict: { ...seed.internal_conflict, ...patch } });
  };

  const updateSolutions = (patch: Partial<SeedConfig["current_solutions"]>) => {
    update({ current_solutions: { ...seed.current_solutions, ...patch } });
  };

  const updateNovelty = (patch: Partial<SeedConfig["novelty"]>) => {
    update({ novelty: { ...seed.novelty, ...patch } });
  };

  const updateStartingParams = (
    field: keyof SeedConfig["starting_params"],
    bound: "min" | "max",
    value: number
  ) => {
    update({
      starting_params: {
        ...seed.starting_params,
        [field]: { ...seed.starting_params[field], [bound]: value },
      },
    });
  };

  const parseTagString = (value: string): string[] =>
    value
      .split(";")
      .map((t) => t.trim())
      .filter(Boolean);

  const formatTagString = (values: string[]): string => values.join("; ");

  const parseObjections = (value: string) => {
    return value
      .split(";")
      .map((t) => t.trim())
      .filter(Boolean)
      .map((item) => {
        const [text, type] = item.split("|").map((s) => s.trim());
        return { text, type: type || "anti_presentation" };
      });
  };

  const formatObjections = (items: { text: string; type: string }[]): string =>
    items.map((o) => (o.type === "anti_presentation" ? o.text : `${o.text} | ${o.type}`)).join("; ");

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setImportErrors([]);
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 100 * 1024) {
      setImportErrors([{ field: "", message: "Файл слишком большой (макс. 100 КБ)" }]);
      e.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = String(event.target?.result ?? "");
        const parsed = JSON.parse(text);
        const errors = validateSeedJson(parsed);
        if (errors.length > 0) {
          setImportErrors(errors);
          return;
        }
        const normalized = normalizeSeedJson(parsed);
        if (normalized) {
          props.onChange(normalized);
        }
      } catch (err) {
        setImportErrors([{ field: "", message: `Ошибка парсинга JSON: ${err instanceof Error ? err.message : String(err)}` }]);
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  return (
    <div className="seed-config-form">
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <button
          type="button"
          className="admin-button"
          onClick={() => fileInputRef.current?.click()}
        >
          📁 Импортировать из JSON
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          style={{ display: "none" }}
          onChange={handleFileSelect}
        />
        {importErrors.length === 0 && (
          <span className="admin-muted" style={{ fontSize: 12 }}>
            JSON-файл сгенерированный моделью-генератором
          </span>
        )}
      </div>
      {importErrors.length > 0 && (
        <div className="admin-alert admin-alert--error" style={{ marginBottom: 16 }}>
          <strong>Ошибки валидации JSON:</strong>
          <ul style={{ margin: "8px 0 0 0", paddingLeft: 20 }}>
            {importErrors.map((err, i) => (
              <li key={i}>
                {err.field ? <code>{err.field}</code> : "JSON"}: {err.message}
              </li>
            ))}
          </ul>
        </div>
      )}
      <fieldset className="admin-fieldset">
        <legend>Контекст тренировки</legend>
        <div className="admin-form-grid">
          <label>
            <span>Продуктовая область</span>
            <input
              value={seed.training_context.product_area}
              onChange={(e) => updateTrainingContext({ product_area: e.target.value })}
            />
          </label>
          <label>
            <span>Целевой сегмент</span>
            <input
              value={seed.training_context.target_segment}
              onChange={(e) => updateTrainingContext({ target_segment: e.target.value })}
            />
          </label>
          <label>
            <span>Тип тренировки</span>
            <select
              value={seed.training_context.training_type}
              onChange={(e) => updateTrainingContext({ training_type: e.target.value })}
            >
              {TRAINING_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Целевое действие</span>
            <select
              value={seed.training_context.target_action}
              onChange={(e) => updateTrainingContext({ target_action: e.target.value })}
            >
              {TARGET_ACTIONS.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Описание целевого действия</span>
            <input
              value={seed.training_context.target_action_description}
              onChange={(e) => updateTrainingContext({ target_action_description: e.target.value })}
            />
          </label>
          <label>
            <span>Правильное название действия</span>
            <input
              value={seed.training_context.target_action_proper_name}
              onChange={(e) => updateTrainingContext({ target_action_proper_name: e.target.value })}
            />
          </label>
          <label>
            <span>Цель звонка</span>
            <input
              value={seed.training_context.call_goal}
              onChange={(e) => updateTrainingContext({ call_goal: e.target.value })}
            />
          </label>
        </div>
        <TagInput
          label="Что НЕ является целью звонка"
          value={formatTagString(seed.training_context.call_goal_is_not ?? [])}
          onChange={(v) => updateTrainingContext({ call_goal_is_not: parseTagString(v) })}
        />
        <TagInput
          label="Предусловия для целевого действия"
          value={formatTagString(seed.training_context.preconditions ?? [])}
          onChange={(v) => updateTrainingContext({ preconditions: parseTagString(v) })}
        />
        <TagInput
          label="Нежелательные поведения менеджера"
          value={formatTagString(seed.training_context.negative_behaviors ?? [])}
          onChange={(v) => updateTrainingContext({ negative_behaviors: parseTagString(v) })}
        />
      </fieldset>

      <fieldset className="admin-fieldset">
        <legend>Продукт</legend>
        <div className="admin-form-grid">
          <label>
            <span>Категория</span>
            <input value={seed.product.category} onChange={(e) => updateProduct({ category: e.target.value })} />
          </label>
          <label>
            <span>Ценностное предложение</span>
            <input
              value={seed.product.value_proposition}
              onChange={(e) => updateProduct({ value_proposition: e.target.value })}
            />
          </label>
          <label>
            <span>Что менеджер продаёт сейчас</span>
            <input
              value={seed.product.what_manager_sells_now}
              onChange={(e) => updateProduct({ what_manager_sells_now: e.target.value })}
            />
          </label>
          <label>
            <span>Полное название продукта</span>
            <input
              value={seed.product.full_product_name}
              onChange={(e) => updateProduct({ full_product_name: e.target.value })}
            />
          </label>
          <label>
            <span>Краткое название области</span>
            <input
              value={seed.product.product_area_short}
              onChange={(e) => updateProduct({ product_area_short: e.target.value })}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="admin-fieldset">
        <legend>ЛПР и роли</legend>
        <div className="admin-form-grid">
          <TagInput
            label="Допустимые роли (через ;)"
            value={formatTagString(seed.lpr_and_roles.allowed_roles ?? [])}
            onChange={(v) => updateLpr({ allowed_roles: parseTagString(v) })}
          />
          <label>
            <span>Требования к роли</span>
            <input
              value={seed.lpr_and_roles.role_requirements}
              onChange={(e) => updateLpr({ role_requirements: e.target.value })}
            />
          </label>
        </div>
      </fieldset>

      <fieldset className="admin-fieldset">
        <legend>Ориентиры (SEED)</legend>
        <TagInput
          label="Отрасли"
          value={formatTagString(seed.segment_and_scale?.industries ?? [])}
          onChange={(v) => updateSegment({ industries: parseTagString(v) })}
        />
        <TagInput
          label="Размеры компаний"
          value={formatTagString(seed.segment_and_scale?.company_sizes ?? [])}
          onChange={(v) => updateSegment({ company_sizes: parseTagString(v) })}
        />
        <TagInput
          label="Триггеры актуальности"
          value={formatTagString(seed.triggers ?? [])}
          onChange={(v) => update({ triggers: parseTagString(v) })}
        />
        <TagInput
          label="Боли клиента"
          value={formatTagString(seed.pains ?? [])}
          onChange={(v) => update({ pains: parseTagString(v) })}
        />
        <label>
          <span>Возражения (формат: Текст | тип; ...)</span>
          <textarea
            rows={4}
            value={formatObjections(seed.objections ?? [])}
            onChange={(e) => update({ objections: parseObjections(e.target.value) })}
          />
          <small className="admin-muted">
            anti_presentation, emotional, trust, price, control, risk. Пример: Нет времени | anti_presentation; Дорого | price
          </small>
        </label>
        <TagInput
          label="Критерии принятия решения"
          value={formatTagString(seed.decision_criteria ?? [])}
          onChange={(v) => update({ decision_criteria: parseTagString(v) })}
        />
        <TagInput
          label="Скрытые ограничения"
          value={formatTagString(seed.hidden_constraints ?? [])}
          onChange={(v) => update({ hidden_constraints: parseTagString(v) })}
        />
        <TagInput
          label="Мотивация к покупке"
          value={formatTagString(seed.motivations ?? [])}
          onChange={(v) => update({ motivations: parseTagString(v) })}
        />
        <TagInput
          label="Внутренний конфликт — сторона А (не хочет менять)"
          value={formatTagString(seed.internal_conflict?.side_a ?? [])}
          onChange={(v) => updateConflict({ side_a: parseTagString(v) })}
        />
        <TagInput
          label="Внутренний конфликт — сторона Б (есть причина рассмотреть)"
          value={formatTagString(seed.internal_conflict?.side_b ?? [])}
          onChange={(v) => updateConflict({ side_b: parseTagString(v) })}
        />
        <TagInput
          label="Типы текущих решений"
          value={formatTagString(seed.current_solutions?.solution_types ?? [])}
          onChange={(v) => updateSolutions({ solution_types: parseTagString(v) })}
        />
        <TagInput
          label="Альтернативные решения (включая статус-кво)"
          value={formatTagString(seed.current_solutions?.alternative_solutions ?? [])}
          onChange={(v) => updateSolutions({ alternative_solutions: parseTagString(v) })}
        />
        <TagInput
          label="Информационные пробелы"
          value={formatTagString(seed.information_gaps ?? [])}
          onChange={(v) => update({ information_gaps: parseTagString(v) })}
        />
        <TagInput
          label="Факторы доверия"
          value={formatTagString(seed.trust_requirements ?? [])}
          onChange={(v) => update({ trust_requirements: parseTagString(v) })}
        />
      </fieldset>

      <fieldset className="admin-fieldset">
        <legend>Антипаттерны и вариативность</legend>
        <TagInput
          label="Антипаттерны (чего избегать)"
          value={formatTagString(seed.novelty?.anti_patterns ?? [])}
          onChange={(v) => updateNovelty({ anti_patterns: parseTagString(v) })}
        />
        <TagInput
          label="Кластеры для избегания"
          value={formatTagString(seed.novelty?.avoid_clusters ?? [])}
          onChange={(v) => updateNovelty({ avoid_clusters: parseTagString(v) })}
        />
      </fieldset>

      <fieldset className="admin-fieldset">
        <legend>Стартовые параметры</legend>
        <div className="admin-form-grid">
          {(
            [
              ["initial_openness", "Начальная открытость"],
              ["starting_interest", "Стартовый интерес"],
              ["trust_baseline", "Базовое доверие"],
              ["price_sensitivity", "Ценовая чувствительность"],
              ["urgency", "Срочность"],
            ] as const
          ).map(([field, label]) => (
            <label key={field}>
              <span>{label}</span>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={seed.starting_params[field].min}
                  onChange={(e) => updateStartingParams(field, "min", Number(e.target.value))}
                  style={{ width: "50%" }}
                />
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={seed.starting_params[field].max}
                  onChange={(e) => updateStartingParams(field, "max", Number(e.target.value))}
                  style={{ width: "50%" }}
                />
              </div>
            </label>
          ))}
        </div>
      </fieldset>
    </div>
  );
}
