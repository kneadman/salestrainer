import type { SessionPublicDTO } from "../types";
import { buildMetricsViewModel } from "../viewModels";

type MetricsPanelProps = {
  session: SessionPublicDTO;
  trainingConfigName?: string;
};

function ProgressBar({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "interest" | "trust";
}) {
  return (
    <div className="metric-block">
      <div className="metric-label-row">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="progress-track">
        <div
          className={`progress-fill progress-fill--${tone}`}
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

export function MetricsPanel({ session, trainingConfigName }: MetricsPanelProps) {
  /** Render session metrics with localized labels from the view model. */
  const vm = buildMetricsViewModel(session, trainingConfigName);

  return (
    <section className="panel-card">
      <div className="panel-card__header">
        <h2>Метрики</h2>
      </div>
      <ProgressBar label="Интерес" value={vm.interestScore} tone="interest" />
      <ProgressBar label="Доверие" value={vm.trust} tone="trust" />
      <dl className="metrics-list">
        {vm.trainingConfigName ? (
          <div>
            <dt>Сценарий</dt>
            <dd>{vm.trainingConfigName}</dd>
          </div>
        ) : null}
        <div>
          <dt>Тон</dt>
          <dd>{vm.toneLabel}</dd>
        </div>
        <div>
          <dt>Количество ходов</dt>
          <dd>{vm.turnCount}</dd>
        </div>
        <div>
          <dt>Уровень интереса</dt>
          <dd>{vm.interestBandLabel}</dd>
        </div>
      </dl>
    </section>
  );
}
