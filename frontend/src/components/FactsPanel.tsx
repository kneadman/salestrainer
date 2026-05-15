import type { FactsPanelDTO } from "../types";
import { buildFactsViewModel } from "../viewModels";

type FactsPanelProps = {
  factsPanel: FactsPanelDTO;
};

export function FactsPanel({ factsPanel }: FactsPanelProps) {
  /** Render revealed facts grouped by category with technical-value filtering. */
  const sections = buildFactsViewModel(factsPanel);

  return (
    <section className="panel-card">
      <div className="panel-card__header">
        <h2>Факты и боли</h2>
      </div>
      {sections.length === 0 ? (
        <p className="panel-empty">
          Пока фактов мало. Задайте вопросы о роли, процессе, боли и критериях решения.
        </p>
      ) : (
        <div className="facts-sections">
          {sections.map((section) => (
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
