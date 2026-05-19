import { useEffect, useState } from "react";
import { getOrganizationUserAnalytics } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState, StatCard } from "./components/AdminPrimitives";
import type { AdminUserAnalyticsDetailDTO } from "./types";
import { buildClientAnalyticsViewModel, buildHistorySessionViewModel, buildTeamUserViewModel } from "../viewModels";
import { getErrorMessage } from "./utils";

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

  const userVm = buildTeamUserViewModel(detail.user);
  const analyticsVm = buildClientAnalyticsViewModel(detail.analytics);
  const historyVms = detail.history.map(buildHistorySessionViewModel);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <a
            href={`/admin/organizations/${organizationId}?tab=users`}
            className="admin-link-button"
            onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate(`/admin/organizations/${organizationId}?tab=users`); }}
          >
            ← Пользователи
          </a>
          <h1>{detail.user.email}</h1>
          <p className="admin-muted">
            {userVm.roleLabel}
            {detail.user.client_account ? ` · ${detail.user.client_account.name} (${detail.user.client_account.slug})` : ""}
          </p>
        </div>
        <Badge tone={userVm.statusTone}>{userVm.statusLabel}</Badge>
      </div>
      <section className="admin-stats-grid">
        <AdminAnalyticsStatCard label="Всего тренировок" value={analyticsVm.totalSessions} trend={detail.analytics.trends_7d.total_sessions} />
        <AdminAnalyticsStatCard label="Завершено" value={analyticsVm.finishedSessions} trend={detail.analytics.trends_7d.finished_sessions} />
        <AdminAnalyticsStatCard label="Активные" value={analyticsVm.activeSessions} />
        <AdminAnalyticsStatCard label="Доля завершённых" value={analyticsVm.completionRateLabel} trend={detail.analytics.trends_7d.completion_rate} />
        <AdminAnalyticsStatCard label="Средний интерес" value={analyticsVm.avgFinalInterestScore} trend={detail.analytics.trends_7d.avg_final_interest_score} />
        <AdminAnalyticsStatCard label="Среднее число ходов" value={analyticsVm.avgTurnCount} trend={detail.analytics.trends_7d.avg_turn_count} />
        <AdminAnalyticsStatCard label="Средняя оценка тренировки" value={analyticsVm.avgJudgementScore} trend={detail.analytics.trends_7d.avg_judgement_score} />
        <AdminAnalyticsStatCard label="С оценкой тренировки" value={analyticsVm.sessionsWithJudgement} trend={detail.analytics.trends_7d.sessions_with_judgement} />
        <StatCard label="Сильнейший навык" value={analyticsVm.strongestSkillTitle} detail={analyticsVm.strongestSkillDetail} />
        <StatCard label="Зона роста" value={analyticsVm.weakestSkillTitle} detail={analyticsVm.weakestSkillDetail} />
        <StatCard label="Последняя активность" value={analyticsVm.lastActivityAtLabel} detail="последнее действие" />
      </section>
      {analyticsVm.sessionsWithJudgement === 0 && (
        <section className="admin-panel">
          <p className="admin-muted">Структурные оценки появятся после завершённых тренировок с отчётом.</p>
        </section>
      )}
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>По статусам</h2></div>
        <AdminBars values={analyticsVm.statusBreakdown} />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>По сценариям</h2></div>
        <AdminBars values={analyticsVm.scenarioBreakdown} />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>Последние тренировки</h2></div>
        {detail.history.length === 0 ? <EmptyState title="Сохранённых тренировок пока нет" /> : <AdminHistoryTable vms={historyVms} onNavigate={onNavigate} />}
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

function formatTrendNumber(value: number): string {
  /** Trim trend numbers to integers or one decimal place for compact labels. */
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function AdminBars({ values }: { values: { key: string; label: string; value: number }[] }) {
  /** Render small internal-admin bars without introducing a chart library. */
  const max = Math.max(1, ...values.map((v) => v.value));
  return (
    <div className="admin-bars">
      {values.map((row) => (
        <div key={row.key} className="admin-bars__row">
          <span>{row.label}</span>
          <div><i style={{ width: `${Math.max(6, (row.value / max) * 100)}%` }} /></div>
          <strong>{row.value}</strong>
        </div>
      ))}
    </div>
  );
}

function AdminHistoryTable({ vms, onNavigate }: { vms: ReturnType<typeof buildHistorySessionViewModel>[]; onNavigate: (path: string) => void }) {
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
          {vms.map((vm) => (
            <tr key={vm.sessionId}>
              <td>{vm.startedAtLabel}</td>
              <td><Badge>{vm.statusLabel}</Badge></td>
              <td>{vm.scenarioLabel}</td>
              <td>{vm.turnCount}</td>
              <td>{vm.finalInterestScore}</td>
              <td>
                <a
                  href={`/admin/history/sessions/${vm.sessionId}`}
                  className="admin-link-button"
                  onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate(`/admin/history/sessions/${vm.sessionId}`); }}
                >
                  Открыть
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
