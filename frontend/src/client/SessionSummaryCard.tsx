import { scenarioLabel, statusLabel } from "../labels";

type SummaryPrimitive = string | number | boolean | null;

type SummaryItem = {
  label: string;
  value: SummaryPrimitive | SummaryPrimitive[];
};

type FormattedSessionSummary =
  | { kind: "empty" }
  | { kind: "plain"; text: string }
  | { kind: "items"; items: SummaryItem[] };

type SessionSummaryCardProps = {
  summary: string | null | undefined;
  publicBrief?: string | null;
};

const SUMMARY_LABELS: Record<string, string> = {
  outcome: "Итог",
  final_interest_score: "Итоговый интерес",
  interest_score: "Интерес",
  turn_count: "Сообщений",
  key_takeaway: "Ключевой вывод",
  summary: "Сводка",
  recommendation: "Рекомендация",
  recommendations: "Рекомендации",
  strengths: "Сильные стороны",
  weaknesses: "Зоны роста",
  risks: "Риски",
  next_step: "Следующий шаг",
  stage: "Этап",
  scenario_id: "Сценарий",
  status: "Статус",
};

const OUTCOME_LABELS: Record<string, string> = {
  meeting: "встреча / следующий шаг",
  next_step: "следующий шаг",
  no_next_step: "без следующего шага",
  lost: "интерес потерян",
  active: "в работе",
};

const UNSAFE_KEY_PARTS = [
  "api_key",
  "secret",
  "token",
  "password",
  "cookie",
  "payload",
  "raw",
  "response",
  "prompt",
  "persona",
  "hidden",
  "snapshot",
  "credential",
];

export function SessionSummaryCard({ summary, publicBrief }: SessionSummaryCardProps) {
  /** Render a client-safe training summary without exposing raw JSON or hidden technical fields. */
  const formatted = formatSessionSummary(summary);
  const trimmedBrief = publicBrief?.trim() ?? "";
  const trimmedSummary = summary?.trim() ?? "";
  const shouldShowBrief = trimmedBrief.length > 0 && trimmedBrief !== trimmedSummary;

  return (
    <section className="client-panel client-summary-card">
      <h2>Сводка тренировки</h2>
      <SummaryBody formatted={formatted} />
      {shouldShowBrief ? (
        <div className="client-summary-brief">
          <h3>Контекст тренировки</h3>
          <p>{trimmedBrief}</p>
        </div>
      ) : null}
    </section>
  );
}

export function formatSessionSummary(summary: string | null | undefined): FormattedSessionSummary {
  /** Convert a nullable summary string into a small display model for safe rendering. */
  const trimmed = summary?.trim() ?? "";
  if (!trimmed) {
    return { kind: "empty" };
  }
  if (!looksLikeJson(trimmed)) {
    return { kind: "plain", text: trimmed };
  }
  try {
    const parsed: unknown = JSON.parse(trimmed);
    return formatParsedSummary(parsed, trimmed);
  } catch {
    return { kind: "plain", text: trimmed };
  }
}

function SummaryBody({ formatted }: { formatted: FormattedSessionSummary }) {
  /** Render the formatted summary model with compact, readable primitives and lists. */
  if (formatted.kind === "empty") {
    return <p className="client-muted">Сводка тренировки пока недоступна.</p>;
  }
  if (formatted.kind === "plain") {
    return <p className="client-summary-text">{formatted.text}</p>;
  }
  return (
    <div className="client-summary-grid">
      {formatted.items.map((item, index) => (
        <div className="client-summary-item" key={`${item.label}-${index}`}>
          <small>{item.label}</small>
          {Array.isArray(item.value) ? (
            <ul>
              {item.value.map((value, valueIndex) => (
                <li key={`${item.label}-${valueIndex}`}>{formatPrimitive(value)}</li>
              ))}
            </ul>
          ) : (
            <span>{formatPrimitive(item.value)}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function formatParsedSummary(parsed: unknown, fallbackText: string): FormattedSessionSummary {
  /** Turn parsed JSON into displayable summary items while dropping complex or unsafe values. */
  if (Array.isArray(parsed)) {
    const values = parsed.map((item) => summarizeArrayItem(item)).filter((item): item is SummaryPrimitive => item !== null);
    return values.length > 0 ? { kind: "items", items: [{ label: "Сводка", value: values }] } : { kind: "plain", text: fallbackText };
  }
  if (isPlainObject(parsed)) {
    const items = Object.entries(parsed)
      .filter(([key]) => !isUnsafeSummaryKey(key))
      .map(([key, value]) => formatSummaryEntry(key, value))
      .filter((item): item is SummaryItem => item !== null);
    return items.length > 0 ? { kind: "items", items } : { kind: "plain", text: fallbackText };
  }
  if (isPrimitive(parsed)) {
    return parsed === null ? { kind: "empty" } : { kind: "plain", text: formatPrimitive(parsed) };
  }
  return { kind: "plain", text: fallbackText };
}

function formatSummaryEntry(key: string, value: unknown): SummaryItem | null {
  /** Format one object entry with known labels and conservative handling for nested values. */
  if (isPrimitive(value)) {
    return { label: labelForKey(key), value: formatValueForKey(key, value) };
  }
  if (Array.isArray(value)) {
    const values = value.map((item) => summarizeArrayItem(item)).filter((item): item is SummaryPrimitive => item !== null);
    return values.length > 0 ? { label: labelForKey(key), value: values } : null;
  }
  if (isPlainObject(value)) {
    const nestedValues = Object.entries(value)
      .filter(([nestedKey]) => !isUnsafeSummaryKey(nestedKey))
      .map(([nestedKey, nestedValue]) => {
        if (!isPrimitive(nestedValue)) {
          return null;
        }
        return `${labelForKey(nestedKey)}: ${formatPrimitive(formatValueForKey(nestedKey, nestedValue))}`;
      })
      .filter((item): item is string => item !== null);
    return nestedValues.length > 0 ? { label: labelForKey(key), value: nestedValues } : null;
  }
  return null;
}

function summarizeArrayItem(item: unknown): SummaryPrimitive {
  /** Extract a safe one-line value from primitive array items or simple object summaries. */
  if (isPrimitive(item)) {
    return item;
  }
  if (!isPlainObject(item)) {
    return null;
  }
  const preferredKeys = ["summary", "title", "text", "recommendation", "key_takeaway", "name"];
  for (const key of preferredKeys) {
    const value = item[key];
    if (!isUnsafeSummaryKey(key) && isPrimitive(value) && value !== null && String(value).trim()) {
      return formatValueForKey(key, value);
    }
  }
  return null;
}

function formatValueForKey(key: string, value: SummaryPrimitive): SummaryPrimitive {
  /** Apply domain labels for values that are known enum-like identifiers. */
  if (typeof value !== "string") {
    return value;
  }
  if (key === "scenario_id") {
    return scenarioLabel(value);
  }
  if (key === "status") {
    return statusLabel(value);
  }
  if (key === "outcome") {
    return OUTCOME_LABELS[value] ?? prettifyKey(value).toLowerCase();
  }
  return value;
}

function labelForKey(key: string): string {
  /** Prefer explicit product labels and fall back to readable non-technical wording. */
  return SUMMARY_LABELS[key] ?? prettifyKey(key);
}

function prettifyKey(key: string): string {
  /** Convert unknown identifiers into readable labels without showing raw snake_case. */
  const text = key.replace(/[_-]+/g, " ").trim();
  if (!text) {
    return "Дополнительно";
  }
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function formatPrimitive(value: SummaryPrimitive): string {
  /** Normalize primitive values for display inside text nodes. */
  if (value === null) {
    return "Не указано";
  }
  if (typeof value === "boolean") {
    return value ? "Да" : "Нет";
  }
  return String(value);
}

function looksLikeJson(value: string): boolean {
  /** Parse only strings that have a JSON-looking outer shape. */
  return (value.startsWith("{") && value.endsWith("}")) || (value.startsWith("[") && value.endsWith("]"));
}

function isPrimitive(value: unknown): value is SummaryPrimitive {
  /** Keep rendering constrained to primitive values that cannot contain nested raw payloads. */
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  /** Accept ordinary JSON objects and reject null, arrays, and class instances. */
  return Object.prototype.toString.call(value) === "[object Object]";
}

function isUnsafeSummaryKey(key: string): boolean {
  /** Drop fields that are likely to contain hidden persona data, raw LLM payloads, or secrets. */
  const normalized = key.toLowerCase();
  return UNSAFE_KEY_PARTS.some((part) => normalized.includes(part));
}
