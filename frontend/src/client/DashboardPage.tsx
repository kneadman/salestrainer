import { useEffect, useState } from "react";
import type { AuthUser } from "../types";
import { getHistorySessions, getMyAnalytics, getTeamUsageSummary } from "./api";
import { ClientState, ClientStat } from "./components/ClientPrimitives";
import type { ClientUserAnalyticsDTO, HistorySessionSummaryDTO, TeamUsageSummaryDTO } from "./types";
import { buildClientAnalyticsViewModel, buildClientHistorySessionViewModel } from "../viewModels";
import { getErrorMessage } from "../errorMessage";

type DashboardPageProps = {
  user: AuthUser;
  onNavigate: (path: string) => void;
};

export function DashboardPage({ user, onNavigate }: DashboardPageProps) {
  /** Render the client cabinet overview with personal and lead team summaries. */
  const [analytics, setAnalytics] = useState<ClientUserAnalyticsDTO | null>(null);
  const [teamSummary, setTeamSummary] = useState<TeamUsageSummaryDTO | null>(null);
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Load dashboard data from real history/team endpoints only. */
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [myAnalytics, recentHistory] = await Promise.all([
          getMyAnalytics(),
          getHistorySessions({ limit: 5, offset: 0 }),
        ]);
        setAnalytics(myAnalytics);
        setHistory(recentHistory);
        if (user.role === "client_lead") {
          setTeamSummary(await getTeamUsageSummary().catch(() => null));
        }
      } catch (loadError) {
        setError(getErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [user.role]);

  if (loading) {
    return <ClientState title="Загрузка кабинета" />;
  }

  if (error) {
    return <ClientState title="Не удалось загрузить обзор" detail={error} tone="error" />;
  }

  const analyticsVm = analytics ? buildClientAnalyticsViewModel(analytics) : null;
  const historyVms = history.map(buildClientHistorySessionViewModel);

  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <span className="client-kicker">Личный кабинет</span>
          <h1>Обзор</h1>
          <p>Добро пожаловать, {user.email}</p>
        </div>
        <a href="/app/trainer" className="client-button client-button--primary" onClick={(event) => { event.preventDefault(); onNavigate("/app/trainer"); }}>
          Начать тренировку
        </a>
      </div>
      <section className="client-stats-grid">
        <ClientStat label="Всего тренировок" value={analyticsVm?.totalSessions ?? 0} />
        <ClientStat label="Завершено" value={analyticsVm?.finishedSessions ?? 0} />
        <ClientStat label="Средний интерес" value={analyticsVm?.avgFinalInterestScore ?? <span className="client-muted">Нет данных</span>} />
        <ClientStat label="Среднее число ходов" value={analyticsVm?.avgTurnCount ?? <span className="client-muted">Нет данных</span>} />
        <ClientStat label="Последняя активность" value={analyticsVm?.lastActivityAtLabel ?? <span className="client-muted">Нет данных</span>} />
      </section>
      {user.role === "client_lead" ? (
        <section className="client-stats-grid">
          <ClientStat label="Менеджеров" value={teamSummary?.users.length ?? <span className="client-muted">Нет данных</span>} />
          <ClientStat label="Тренировок команды" value={teamSummary?.total_sessions ?? <span className="client-muted">Нет данных</span>} />
          <ClientStat label="Завершено командой" value={teamSummary?.finished_sessions ?? <span className="client-muted">Нет данных</span>} />
          <ClientStat label="Средний интерес команды" value={teamSummary?.avg_final_interest_score?.toFixed(1) ?? <span className="client-muted">Нет данных</span>} />
        </section>
      ) : null}
      <section className="client-panel">
        <div className="client-panel__header">
          <h2>Последние тренировки</h2>
          <a href="/app/history" className="client-link-button" onClick={(event) => { event.preventDefault(); onNavigate("/app/history"); }}>Открыть историю</a>
        </div>
        {history.length === 0 ? (
          <ClientState title="Аналитика появится после первых завершенных тренировок." />
        ) : (
          <div className="client-table-wrap">
            <table className="client-table">
              <thead><tr><th>Дата</th><th>Статус</th><th>Сценарий</th><th>Ходы</th><th>Интерес</th></tr></thead>
              <tbody>{historyVms.map((vm) => <tr key={vm.sessionId}><td>{vm.startedAtLabel}</td><td>{vm.statusLabel}</td><td>{vm.scenarioLabel}</td><td>{vm.turnCount}</td><td>{vm.finalInterestScore}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
