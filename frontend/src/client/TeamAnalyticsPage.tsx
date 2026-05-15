import { useEffect, useState } from "react";
import { getTeamUsageSummary } from "./api";
import { ClientState, ClientStat, SimpleBars } from "./components/ClientPrimitives";
import type { TeamUsageSummaryDTO } from "./types";
import { scenarioLabel, statusLabel } from "../labels";
import { getClientErrorMessage } from "./utils";

export function TeamAnalyticsPage() {
  /** Render organization-level analytics for client leads. */
  const [summary, setSummary] = useState<TeamUsageSummaryDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Load team analytics from the client-lead endpoint. */
    const load = async () => {
      try {
        setSummary(await getTeamUsageSummary());
      } catch (loadError) {
        setError(getClientErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  if (loading) {
    return <ClientState title="Загрузка аналитики команды" />;
  }
  if (error) {
    return <ClientState title="Командная аналитика недоступна" detail={error} tone="error" />;
  }
  if (!summary || summary.total_sessions === 0) {
    return <ClientState title="Командная аналитика появится после первых тренировок." />;
  }
  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <span className="client-kicker">Команда</span>
          <h1>Аналитика команды</h1>
        </div>
      </div>
      <section className="client-stats-grid">
        <ClientStat label="Всего тренировок" value={summary.total_sessions} />
        <ClientStat label="Завершено" value={summary.finished_sessions} />
        <ClientStat label="Активные сессии" value={summary.active_sessions} />
        <ClientStat label="Пользователей" value={summary.unique_users} />
        <ClientStat label="Всего ходов" value={summary.total_turns} />
        <ClientStat label="Средний интерес" value={summary.avg_final_interest_score?.toFixed(1) ?? "—"} />
        <ClientStat label="Средняя оценка тренировки" value={summary.avg_judgement_score?.toFixed(1) ?? "—"} />
        <ClientStat label="С оценкой тренировки" value={summary.sessions_with_judgement} />
        <ClientStat label="Сильнейший навык" value={summary.strongest_skill_title ?? "—"} />
        <ClientStat label="Зона роста" value={summary.weakest_skill_title ?? "—"} />
      </section>
      {summary.sessions_with_judgement === 0 && (
        <section className="client-panel">
          <p className="client-muted">Структурные оценки команды появятся после завершённых тренировок с отчётом.</p>
        </section>
      )}
      <section className="client-panel">
        <h2>Рейтинг менеджеров</h2>
        <div className="client-table-wrap">
          <table className="client-table">
            <thead>
              <tr>
                <th>Место</th>
                <th>Email</th>
                <th>Итог</th>
                <th>Оценка</th>
                <th>Завершено</th>
                <th>Конверсия</th>
              </tr>
            </thead>
            <tbody>
              {summary.manager_ranking.map((item) => (
                <tr key={item.user_id}>
                  <td>{item.rank}</td>
                  <td>{item.user_email}</td>
                  <td>{item.score.toFixed(1)}</td>
                  <td>{item.avg_judgement_score?.toFixed(1) ?? "—"}</td>
                  <td>{item.finished_sessions}</td>
                  <td>{Math.round(item.completion_rate * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="client-panel">
        <h2>По менеджерам</h2>
        <div className="client-table-wrap">
          <table className="client-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Всего</th>
                <th>Завершено</th>
                <th>Средний интерес</th>
              </tr>
            </thead>
            <tbody>
              {summary.users.map((user) => (
                <tr key={user.id}>
                  <td>{user.email}</td>
                  <td>{user.total_sessions}</td>
                  <td>{user.finished_sessions}</td>
                  <td>{user.avg_final_interest_score?.toFixed(1) ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="client-panel">
        <h2>По статусам</h2>
        <SimpleBars values={summary.sessions_by_status} labelFormatter={statusLabel} />
      </section>
      <section className="client-panel">
        <h2>По сценариям</h2>
        <SimpleBars values={summary.sessions_by_scenario} labelFormatter={scenarioLabel} />
      </section>
    </div>
  );
}
