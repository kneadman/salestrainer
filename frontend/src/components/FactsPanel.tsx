import type { ClientStatePublic } from "../types";

type FactsPanelProps = {
  state: ClientStatePublic;
};

type FactSection = {
  label: string;
  values: string[];
};

function normalizeList(values?: string[] | null): string[] {
  if (!values) {
    return [];
  }
  return values.filter((value) => value.trim().length > 0);
}

export function FactsPanel({ state }: FactsPanelProps) {
  const sections: FactSection[] = [
    {
      label: "Роль",
      values: state.discovered_role ? [state.discovered_role] : [],
    },
    {
      label: "Уровень влияния",
      values: state.discovered_authority_level ? [state.discovered_authority_level] : [],
    },
    {
      label: "Текущий процесс",
      values: normalizeList(state.discovered_current_process),
    },
    {
      label: "Критерии решения",
      values: normalizeList(state.discovered_decision_criteria),
    },
    {
      label: "Ограничения",
      values: normalizeList(state.discovered_constraints),
    },
    {
      label: "Сигналы интереса",
      values: normalizeList(state.buying_signals),
    },
    {
      label: "Выявленные боли",
      values: normalizeList(state.known_pains),
    },
  ];

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
