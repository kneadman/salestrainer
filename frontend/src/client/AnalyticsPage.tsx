import { useEffect, useState } from "react";
import { getMyAnalytics } from "./api";
import { ClientState, SimpleBars } from "./components/ClientPrimitives";
import type { ClientUserAnalyticsDTO, MetricTrendDTO } from "./types";
import { buildClientAnalyticsViewModel } from "../viewModels";
import { scenarioLabel, statusLabel } from "../labels";
import { getClientErrorMessage } from "./utils";

type AnalyticsCardProps = {
  label: string;
  value: string;
  trend?: MetricTrendDTO;
  wide?: boolean;
  accent?: boolean;
  hideDelta?: boolean;
  footer?: string;
};

export function AnalyticsPage() {
  /** Render personal analytics for the current manager or lead. */
  const [analytics, setAnalytics] = useState<ClientUserAnalyticsDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Load personal analytics from the client portal endpoint. */
    const load = async () => {
      try {
        setAnalytics(await getMyAnalytics());
      } catch (loadError) {
        setError(getClientErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return <ClientState title="Загрузка аналитики" />;
  }
  if (error) {
    return <ClientState title="Аналитика недоступна" detail={error} tone="error" />;
  }
  if (!analytics || analytics.total_sessions === 0) {
    return <ClientState title="Аналитика появится после первых тренировок." />;
  }

  const vm = buildClientAnalyticsViewModel(analytics);

  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <span className="client-kicker">Моя аналитика</span>
          <h1>Прогресс</h1>
        </div>
      </div>
      <section className="analytics-bento-grid">
        <AnalyticsBentoCard
          label="Всего тренировок"
          value={String(analytics.total_sessions)}
          trend={analytics.trends_7d.total_sessions}
          accent
        />
        <AnalyticsBentoCard
          label="Завершено"
          value={String(analytics.finished_sessions)}
          trend={analytics.trends_7d.finished_sessions}
        />
        <AnalyticsBentoCard
          label="Доля завершённых"
          value={vm.completionRateLabel}
          trend={analytics.trends_7d.completion_rate}
        />
        <AnalyticsBentoCard
          label="Средний интерес"
          value={vm.avgFinalInterestScore}
          trend={analytics.trends_7d.avg_final_interest_score}
        />
        <AnalyticsBentoCard
          label="Среднее число ходов"
          value={vm.avgTurnCount}
          trend={analytics.trends_7d.avg_turn_count}
        />
        <AnalyticsBentoCard
          label="Средняя оценка тренировки"
          value={vm.avgJudgementScore}
          trend={analytics.trends_7d.avg_judgement_score}
        />
        <AnalyticsBentoCard
          label="С оценкой тренировки"
          value={String(analytics.sessions_with_judgement)}
          trend={analytics.trends_7d.sessions_with_judgement}
        />
        <AnalyticsBentoCard
          label="Сильнейший навык"
          value={vm.strongestSkillTitle}
          footer={vm.strongestSkillDetail}
          hideDelta
          wide
        />
        <AnalyticsBentoCard
          label="Зона роста"
          value={vm.weakestSkillTitle}
          footer={vm.weakestSkillDetail}
          hideDelta
          wide
        />
        <AnalyticsBentoCard
          label="Последняя активность"
          value={vm.lastActivityAtLabel}
          footer="последнее действие"
          hideDelta
          wide
        />
      </section>
      {analytics.sessions_with_judgement === 0 && (
        <section className="client-panel">
          <p className="client-muted">Структурные оценки и навыки появятся после завершённых тренировок с отчётом.</p>
        </section>
      )}
      <section className="client-panel">
        <h2>По статусам</h2>
        <SimpleBars values={analytics.sessions_by_status} labelFormatter={statusLabel} />
      </section>
      <section className="client-panel">
        <h2>По сценариям</h2>
        <SimpleBars values={analytics.sessions_by_scenario} labelFormatter={scenarioLabel} />
      </section>
    </div>
  );
}

function AnalyticsBentoCard({ label, value, trend, wide = false, accent = false, hideDelta = false, footer }: AnalyticsCardProps) {
  /** Render one analytics card with all-time value plus real backend 7-day context. */
  const trendLabel = trendWindowLabel(trend);
  const deltaLabel = hideDelta ? footer : trendDeltaLabel(trend);
  const cardClassName = [
    "analytics-bento-card",
    wide ? "analytics-bento-card--wide" : "",
    accent ? "analytics-bento-card--accent" : "",
  ]
    .filter(Boolean)
    .join(" ");
  return (
    <section className={cardClassName}>
      <span className="analytics-bento-card__label">{label}</span>
      <strong className="analytics-bento-card__value">{value}</strong>
      <div className="analytics-bento-card__meta">
        <span>{trendLabel}</span>
        <span className={`analytics-bento-card__trend analytics-bento-card__trend--${trend?.direction ?? "none"}`}>{deltaLabel}</span>
      </div>
    </section>
  );
}

function trendWindowLabel(trend: MetricTrendDTO | undefined): string {
  /** Show the real current 7-day value or a neutral no-data label. */
  if (!trend || trend.current_7d === null) {
    return "за 7 дней: —";
  }
  return `за 7 дней: ${formatTrendNumber(trend.current_7d)}`;
}

function trendDeltaLabel(trend: MetricTrendDTO | undefined): string {
  /** Show comparison against the previous 7-day window only when backend provided data. */
  if (!trend || trend.delta === null) {
    return "нет данных за 7 дней";
  }
  const deltaPrefix = trend.delta > 0 ? "+" : "";
  const percentLabel = trend.delta_percent === null ? "" : ` (${deltaPrefix}${formatTrendNumber(trend.delta_percent)}%)`;
  return `Δ ${deltaPrefix}${formatTrendNumber(trend.delta)} к прошлым 7 дням${percentLabel}`;
}

function formatTrendNumber(value: number): string {
  /** Trim analytics trend numbers down to readable integers or one decimal place. */
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
