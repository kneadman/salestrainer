import { useEffect, useState } from "react";
import { roleLabel, scenarioLabel, statusLabel as entityStatusLabel } from "../labels";
import { getOrganizationUserAnalytics } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState, StatCard } from "./components/AdminPrimitives";
import type { AdminUserAnalyticsDetailDTO, HistorySessionSummaryDTO } from "./types";
import { formatDate, getErrorMessage, statusLabel } from "./utils";

type AdminUserAnalyticsPageProps = {
  organizationId: string;
  userId: string;
  onNavigate: (path: string) => void;
};

export function AdminUserAnalyticsPage({ organizationId, userId, onNavigate }: AdminUserAnalyticsPageProps) {
  /** Render a permalink internal-admin analytics screen for one organization user. */
  const [detail, setDetail] = useState<AdminUserAnalyticsDetailDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Load one user's analytics and recent history from the internal admin API. */
    const load = async () => {
      try {
        setDetail(await getOrganizationUserAnalytics(organizationId, userId));
      } catch (loadError) {
        setError(getErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [organizationId, userId]);

  if (loading) {
    return <LoadingState title="Загрузка аналитики пользователя" />;
  }
  if (error || !detail) {
    return <ErrorState title="Аналитика пользователя недоступна" detail={error ?? "Пользователь не найден."} />;
  }
  const { user, analytics, history } = detail;
  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <button
            type="button"
            className="admin-link-button"
            onClick={() => onNavigate(`/admin/organizations/${organizationId}?tab=users`)}
          >
            ← Пользователи
          </button>
          <h1>{user.email}</h1>
          <p className="admin-muted">
            {roleLabel(user.role)}
            {user.client_account ? ` · ${user.client_account.name} (${user.client_account.slug})` : ""}
          </p>
        </div>
        <Badge tone={user.is_active ? "good" : "danger"}>{statusLabel(user.is_active)}</Badge>
      </div>
      <section className="admin-stats-grid">
        <AdminAnalyticsStatCard label="Всего тренировок" value={analytics.total_sessions} trend={analytics.trends_7d.total_sessions} />
        <AdminAnalyticsStatCard label="Завершено" value={analytics.finished_sessions} trend={analytics.trends_7d.finished_sessions} />
        <AdminAnalyticsStatCard label="Активные" value={analytics.active_sessions} />
        <AdminAnalyticsStatCard label="Доля завершённых" value={formatPercent(analytics.completion_rate)} trend={analytics.trends_7d.completion_rate} />
        <AdminAnalyticsStatCard label="Средний интерес" value={formatMetricValue(analytics.avg_final_interest_score)} trend={analytics.trends_7d.avg_final_interest_score} />
        <AdminAnalyticsStatCard label="Среднее число ходов" value={formatMetricValue(analytics.avg_turn_count)} trend={analytics.trends_7d.avg_turn_count} />
        <AdminAnalyticsStatCard label="Средняя оценка тренировки" value={formatMetricValue(analytics.avg_judgement_score)} trend={analytics.trends_7d.avg_judgement_score} />
        <AdminAnalyticsStatCard label="С оценкой тренировки" value={analytics.sessions_with_judgement} trend={analytics.trends_7d.sessions_with_judgement} />
        <StatCard label="Последняя активность" value={formatDate(analytics.last_activity_at)} detail="последнее действие" />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>По статусам</h2></div>
        <AdminBars values={analytics.sessions_by_status} labelFormatter={entityStatusLabel} />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>По сценариям</h2></div>
        <AdminBars values={analytics.sessions_by_scenario} labelFormatter={scenarioLabel} />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>Последние тренировки</h2></div>
        {history.length === 0 ? <EmptyState title="Сохранённых тренировок пока нет" /> : <AdminHistoryTable history={history} onNavigate={onNavigate} />}
      </section>
    </div>
  );
}

function AdminAnalyticsStatCard({
  label,
  value,
  trend,
}: {
  label: string;
  value: string | number;
  trend?: {
    current_7d: number | null;
    previous_7d: number | null;
    delta: number | null;
    delta_percent: number | null;
    direction: "up" | "down" | "flat" | "none";
  };
}) {
  /** Render one admin analytics metric with a compact backend-provided 7-day trend line. */
  return (
    <StatCard
      label={label}
      value={value}
      detail={trend ? `${trendWindowLabel(trend)} · ${trendDeltaLabel(trend)}` : undefined}
    />
  );
}

function trendWindowLabel(trend: {
  current_7d: number | null;
  direction: "up" | "down" | "flat" | "none";
}): string {
  /** Show the current 7-day value or a neutral no-data marker. */
  if (trend.current_7d === null) {
    return "за 7 дней: —";
  }
  return `за 7 дней: ${formatTrendNumber(trend.current_7d)}`;
}

function trendDeltaLabel(trend: {
  delta: number | null;
  delta_percent: number | null;
}): string {
  /** Show the delta against the previous 7-day window without inventing missing data. */
  if (trend.delta === null) {
    return "нет данных за 7 дней";
  }
  const prefix = trend.delta > 0 ? "+" : "";
  const percentLabel = trend.delta_percent === null ? "" : ` (${prefix}${formatTrendNumber(trend.delta_percent)}%)`;
  return `Δ ${prefix}${formatTrendNumber(trend.delta)} к прошлым 7 дням${percentLabel}`;
}

function formatPercent(value: number): string {
  /** Format decimal ratios as whole percentages for admin cards. */
  return `${Math.round(value * 100)}%`;
}

function formatMetricValue(value: number | null): string {
  /** Keep averages compact and human-readable. */
  return value === null ? "—" : value.toFixed(1);
}

function formatTrendNumber(value: number): string {
  /** Trim trend numbers to integers or one decimal place for compact labels. */
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function AdminBars({ values, labelFormatter }: { values: Record<string, number>; labelFormatter?: (key: string) => string }) {
  /** Render small internal-admin bars without introducing a chart library. */
  const max = Math.max(1, ...Object.values(values));
  return (
    <div className="admin-bars">
      {Object.entries(values).map(([key, value]) => (
        <div key={key} className="admin-bars__row">
          <span>{labelFormatter ? labelFormatter(key) : key}</span>
          <div><i style={{ width: `${Math.max(6, (value / max) * 100)}%` }} /></div>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function AdminHistoryTable({ history, onNavigate }: { history: HistorySessionSummaryDTO[]; onNavigate: (path: string) => void }) {
  /** Render recent public-safe history rows for one user with deep links to admin history detail. */
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Статус</th>
            <th>Сценарий</th>
            <th>Ходы</th>
            <th>Интерес</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {history.map((session) => (
            <tr key={session.session_id}>
              <td>{formatDate(session.started_at)}</td>
              <td><Badge>{entityStatusLabel(session.status)}</Badge></td>
              <td>{scenarioLabel(session.scenario_id)}</td>
              <td>{session.turn_count}</td>
              <td>{session.final_interest_score ?? "—"}</td>
              <td>
                <button
                  type="button"
                  className="admin-link-button"
                  onClick={() => onNavigate(`/admin/history/sessions/${session.session_id}`)}
                >
                  Открыть
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
