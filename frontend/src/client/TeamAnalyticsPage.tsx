import { useEffect, useState } from "react";
import { getTeamUsageSummary } from "./api";
import { ClientState, ClientStat, SimpleBars } from "./components/ClientPrimitives";
import type { TeamUsageSummaryDTO } from "./types";
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
      <div className="client-page__header"><div><span className="client-kicker">Команда</span><h1>Аналитика команды</h1></div></div>
      <section className="client-stats-grid">
        <ClientStat label="Всего тренировок" value={summary.total_sessions} />
        <ClientStat label="Завершено" value={summary.finished_sessions} />
        <ClientStat label="Активные сессии" value={summary.active_sessions} />
        <ClientStat label="Пользователей" value={summary.unique_users} />
        <ClientStat label="Всего ходов" value={summary.total_turns} />
        <ClientStat label="Средний интерес" value={summary.avg_final_interest_score?.toFixed(1) ?? "—"} />
      </section>
      <section className="client-panel"><h2>По менеджерам</h2><div className="client-table-wrap"><table className="client-table"><thead><tr><th>Email</th><th>Всего</th><th>Завершено</th><th>Средний интерес</th></tr></thead><tbody>{summary.users.map((user) => <tr key={user.id}><td>{user.email}</td><td>{user.total_sessions}</td><td>{user.finished_sessions}</td><td>{user.avg_final_interest_score?.toFixed(1) ?? "—"}</td></tr>)}</tbody></table></div></section>
      <section className="client-panel"><h2>По статусам</h2><SimpleBars values={summary.sessions_by_status} /></section>
      <section className="client-panel"><h2>По сценариям</h2><SimpleBars values={summary.sessions_by_scenario} /></section>
    </div>
  );
}
