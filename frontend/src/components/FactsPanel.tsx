import type { ClientStatePublic, RevealedFactCategory } from "../types";

type FactsPanelProps = {
  state: ClientStatePublic;
};

type FactSection = {
  label: string;
  values: string[];
};

const CATEGORY_LABELS: Record<RevealedFactCategory, string> = {
  role: "Роль",
  authority: "Полномочия",
  current_process: "Текущий процесс",
  decision_criterion: "Критерии решения",
  constraint: "Ограничения",
  buying_signal: "Сигналы интереса",
  pain: "Выявленные боли",
  objection: "Возражения",
};

const CATEGORY_ORDER: RevealedFactCategory[] = [
  "role",
  "authority",
  "current_process",
  "decision_criterion",
  "constraint",
  "buying_signal",
  "pain",
  "objection",
];

function normalizeFactText(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

function isTechnicalValue(value: string): boolean {
  const normalized = value.trim();
  return normalized.length === 0 || normalized.includes("_") || /^[a-z][a-z0-9_]*$/.test(normalized);
}

export function FactsPanel({ state }: FactsPanelProps) {
  const grouped = new Map<RevealedFactCategory, string[]>();
  for (const fact of state.revealed_facts ?? []) {
    const text = normalizeFactText(fact.text);
    if (isTechnicalValue(text)) {
      continue;
    }
    const values = grouped.get(fact.category) ?? [];
    if (!values.some((value) => value.toLocaleLowerCase() === text.toLocaleLowerCase())) {
      values.push(text);
      grouped.set(fact.category, values);
    }
  }

  const sections: FactSection[] = CATEGORY_ORDER.map((category) => ({
    label: CATEGORY_LABELS[category],
    values: grouped.get(category) ?? [],
  }));
  const visibleSections = sections.filter((section) => section.values.length > 0);

  return (
    <section className="panel-card">
      <div className="panel-card__header">
        <h2>Факты и боли</h2>
      </div>
      {visibleSections.length === 0 ? (
        <p className="panel-empty">
          Пока фактов мало. Задайте вопросы о роли, процессе, боли и критериях решения.
        </p>
      ) : (
        <div className="facts-sections">
          {visibleSections.map((section) => (
            <div key={section.label} className="fact-group">
              <h3>{section.label}</h3>
              <ul>
                {section.values.map((value) => (
                  <li key={`${section.label}-${value}`}>{value}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
