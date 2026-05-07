import { FormEvent, useEffect, useState } from "react";
import { getHistorySessionDetail, getHistorySessions } from "./api";
import { StructuredReportSummary } from "../components/StructuredReportSummary";
import { ClientBadge, ClientState } from "./components/ClientPrimitives";
import type { HistorySessionDetailDTO, HistorySessionSummaryDTO } from "./types";
import { scenarioLabel, statusLabel } from "../labels";
import { formatClientDate, getClientErrorMessage } from "./utils";

type HistoryPageProps = {
  sessionId?: string;
  onNavigate: (path: string) => void;
};

export function HistoryPage({ sessionId, onNavigate }: HistoryPageProps) {
  /** Route history list and detail screens within the client cabinet. */
  if (sessionId) {
    return <HistoryDetail sessionId={sessionId} onNavigate={onNavigate} />;
  }
  return <HistoryList onNavigate={onNavigate} />;
}

function HistoryList({ onNavigate }: { onNavigate: (path: string) => void }) {
  /** Render role-scoped persistent training history with simple filters. */
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [status, setStatus] = useState("");
  const [scenarioId, setScenarioId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    /** Load history from the client-facing history endpoint. */
    setLoading(true);
    setError(null);
    try {
      setHistory(await getHistorySessions({ status, scenario_id: scenarioId, limit: 100, offset: 0 }));
    } catch (loadError) {
      setError(getClientErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    /** Load initial history on mount. */
    void load();
  }, []);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    /** Apply filters without navigating. */
    event.preventDefault();
    void load();
  };

  if (loading) {
    return <ClientState title="Загрузка истории" />;
  }
  if (error) {
    return <ClientState title="История недоступна" detail={error} tone="error" />;
  }
  return (
    <div className="client-page">
      <div className="client-page__header"><div><span className="client-kicker">История</span><h1>Тренировки</h1></div></div>
      <section className="client-panel">
        <form className="client-form client-form--inline" onSubmit={submit}>
          <label><span>Статус</span><input value={status} onChange={(event) => setStatus(event.target.value)} placeholder="active / finished" /></label>
          <label><span>Сценарий</span><input value={scenarioId} onChange={(event) => setScenarioId(event.target.value)} /></label>
          <button type="submit" className="client-button client-button--primary">Применить</button>
        </form>
      </section>
      <section className="client-panel">
        {history.length === 0 ? <ClientState title="История появится после первых тренировок." /> : (
          <div className="client-table-wrap"><table className="client-table"><thead><tr><th>Дата</th><th>Пользователь</th><th>Статус</th><th>Сценарий</th><th>Ходы</th><th>Интерес</th><th>Действия</th></tr></thead><tbody>{history.map((item) => <tr key={item.session_id}><td>{formatClientDate(item.started_at)}</td><td>{item.user_email}</td><td><ClientBadge>{statusLabel(item.status)}</ClientBadge></td><td>{scenarioLabel(item.scenario_id)}</td><td>{item.turn_count}</td><td>{item.final_interest_score ?? "—"}</td><td><button type="button" className="client-link-button" onClick={() => onNavigate(`/app/history/${item.session_id}`)}>Открыть</button></td></tr>)}</tbody></table></div>
        )}
      </section>
    </div>
  );
}

function HistoryDetail({ sessionId, onNavigate }: { sessionId: string; onNavigate: (path: string) => void }) {
  /** Render one public-safe history session detail without hidden payloads. */
  const [detail, setDetail] = useState<HistorySessionDetailDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Load one history detail by session id. */
    const load = async () => {
      try {
        setDetail(await getHistorySessionDetail(sessionId));
      } catch (loadError) {
        setError(getClientErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [sessionId]);

  if (loading) {
    return <ClientState title="Загрузка тренировки" />;
  }
  if (error || !detail) {
    return <ClientState title="Тренировка недоступна" detail={error ?? "Не найдена."} tone="error" />;
  }
  return (
    <div className="client-page">
      <div className="client-page__header"><div><button type="button" className="client-link-button" onClick={() => onNavigate("/app/history")}>← История</button><h1>Тренировка {detail.session.session_id.slice(0, 8)}</h1><p>{detail.session.summary ?? "Сводки нет."}</p></div><ClientBadge>{statusLabel(detail.session.status)}</ClientBadge></div>
      <section className="client-panel"><h2>Ходы</h2>{detail.turns.length === 0 ? <ClientState title="Ходов нет" /> : <div className="client-turn-list">{detail.turns.map((turn) => <article key={turn.turn_index}><ClientBadge>#{turn.turn_index}</ClientBadge><p><strong>Менеджер:</strong> {turn.manager_message}</p><p><strong>Клиент:</strong> {turn.client_answer}</p><p className="client-muted">Интерес {turn.interest_before} → {turn.interest_after}; этап {turn.stage_before} → {turn.stage_after}</p></article>)}</div>}</section>
      <section className="client-panel">
        <h2>Отчёт</h2>
        {detail.report ? (
          <>
            <StructuredReportSummary payload={detail.report.report_payload ?? null} />
            <pre className="client-report">{detail.report.report}</pre>
          </>
        ) : (
          <ClientState title="Сохранённого отчёта нет" />
        )}
      </section>
    </div>
  );
}
