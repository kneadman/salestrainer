import { useEffect, useState } from "react";
import { getMyAnalytics } from "./api";
import { ClientState, ClientStat, SimpleBars } from "./components/ClientPrimitives";
import type { ClientUserAnalyticsDTO } from "./types";
import { scenarioLabel, statusLabel } from "../labels";
import { formatClientDate, getClientErrorMessage, percent } from "./utils";

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
  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <span className="client-kicker">Моя аналитика</span>
          <h1>Прогресс</h1>
        </div>
      </div>
      <section className="client-stats-grid">
        <ClientStat label="Всего" value={analytics.total_sessions} />
        <ClientStat label="Завершено" value={analytics.finished_sessions} />
        <ClientStat label="Доля завершённых" value={percent(analytics.completion_rate)} />
        <ClientStat label="Средний интерес" value={analytics.avg_final_interest_score?.toFixed(1) ?? "—"} />
        <ClientStat label="Среднее число ходов" value={analytics.avg_turn_count?.toFixed(1) ?? "—"} />
        <ClientStat label="Средняя оценка тренировки" value={analytics.avg_judgement_score?.toFixed(1) ?? "—"} />
        <ClientStat label="С оценкой тренировки" value={analytics.sessions_with_judgement} />
        <ClientStat label="Слабейший навык" value={analytics.weakest_skill_title ?? "—"} />
        <ClientStat label="Последняя активность" value={formatClientDate(analytics.last_activity_at)} />
      </section>
      <section className="client-panel">
        <h2>По статусам</h2>
        <SimpleBars values={analytics.sessions_by_status} labelFormatter={statusLabel} />
      </section>
      <section className="client-panel">
        <h2>По сценариям</h2>
        <SimpleBars values={analytics.sessions_by_scenario} labelFormatter={scenarioLabel} />
      </section>
      <section className="client-panel">
        <h2>Оценки навыков</h2>
        <ClientState
          title={analytics.weakest_skill_title ?? "Данных по навыкам пока нет"}
          detail={
            analytics.weakest_skill_title
              ? `Средняя оценка: ${analytics.weakest_skill_avg_score?.toFixed(1) ?? "—"}`
              : undefined
          }
        />
      </section>
    </div>
  );
}
