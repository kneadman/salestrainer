import type { ClientStatePublic, SessionPublicDTO } from "../types";

type MetricsPanelProps = {
  session: SessionPublicDTO;
};

const toneLabels: Record<string, string> = {
  cold: "Холодный",
  skeptical: "Скептичный",
  neutral: "Нейтральный",
  interested: "Заинтересованный",
  warm: "Тёплый",
  ready_next_step: "Готов к следующему шагу",
};

const interestBandLabels: Record<string, string> = {
  cold: "Холодный",
  skeptical: "Скептичный",
  neutral: "Нейтральный",
  warm: "Тёплый",
  hot: "Горячий",
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

function readTrust(state: ClientStatePublic): number {
  return typeof state.trust === "number" ? state.trust : 0;
}

function localizeTone(value?: string): string {
  if (!value) {
    return "Неизвестно";
  }
  return toneLabels[value] ?? value;
}

function localizeInterestBand(value: string): string {
  return interestBandLabels[value] ?? value;
}

export function MetricsPanel({ session }: MetricsPanelProps) {
  const state = session.client_state_public;

  return (
    <section className="panel-card">
      <div className="panel-card__header">
        <h2>Метрики</h2>
      </div>
      <ProgressBar label="Интерес" value={session.interest.score} tone="interest" />
      <ProgressBar label="Доверие" value={readTrust(state)} tone="trust" />
      <dl className="metrics-list">
        <div>
          <dt>Тон</dt>
          <dd>{localizeTone(state.tone)}</dd>
        </div>
        <div>
          <dt>Количество ходов</dt>
          <dd>{session.turn_count}</dd>
        </div>
        <div>
          <dt>Уровень интереса</dt>
          <dd>{localizeInterestBand(session.interest.band)}</dd>
        </div>
      </dl>
    </section>
  );
}
