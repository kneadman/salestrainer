import { FormEvent, useEffect, useState } from "react";
import { getHistorySessionDetail, getHistorySessions } from "./api";
import { ReportSurface } from "../components/ReportSurface";
import { ClientBadge, ClientState } from "./components/ClientPrimitives";
import type { HistorySessionDetailDTO, HistorySessionSummaryDTO, HistoryTurnDTO } from "./types";
import { SCENARIO_OPTIONS, scenarioLabel, stageLabel, statusLabel } from "../labels";
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
      <div className="client-page__header">
        <div>
          <span className="client-kicker">История</span>
          <h1>Тренировки</h1>
        </div>
      </div>
      <HistoryFilters status={status} scenarioId={scenarioId} setStatus={setStatus} setScenarioId={setScenarioId} onSubmit={submit} />
      <section className="client-panel">
        {history.length === 0 ? <ClientState title="История появится после первых тренировок." /> : <HistoryTable history={history} onNavigate={onNavigate} />}
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
  const startedAtLabel = formatClientDate(detail.session.started_at);
  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <button type="button" className="client-link-button" onClick={() => onNavigate("/app/history")}>
            ← История
          </button>
          <h1>{startedAtLabel === "—" ? "Тренировка" : `Тренировка ${startedAtLabel}`}</h1>
        </div>
        <ClientBadge>{statusLabel(detail.session.status)}</ClientBadge>
      </div>
      <HistoryTurnsList turns={detail.turns} />
      <section className="client-panel">
        <h2>Отчёт</h2>
        {detail.report ? (
          <ReportSurface
            report={detail.report.report}
            reportPayload={detail.report.report_payload ?? null}
            fallbackClassName="training-report-modal__fallback client-report-fallback"
            fallbackTextClassName="report-block client-report"
          />
        ) : (
          <ClientState title="Сохранённого отчёта нет" />
        )}
      </section>
    </div>
  );
}

function HistoryFilters(props: {
  status: string;
  scenarioId: string;
  setStatus: (value: string) => void;
  setScenarioId: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  /** Render client-safe history filters without exposing backend enum names as input hints. */
  return (
    <section className="client-panel">
      <form className="client-form client-form--inline" onSubmit={props.onSubmit}>
        <label>
          <span>Статус</span>
          <select value={props.status} onChange={(event) => props.setStatus(event.target.value)}>
            <option value="">Все статусы</option>
            <option value="active">Активные</option>
            <option value="finished">Завершённые</option>
            <option value="expired">Истёкшие</option>
          </select>
        </label>
        <label>
          <span>Сценарий</span>
          <select value={props.scenarioId} onChange={(event) => props.setScenarioId(event.target.value)}>
            <option value="">Все сценарии</option>
            {SCENARIO_OPTIONS.map((scenarioId) => (
              <option key={scenarioId} value={scenarioId}>
                {scenarioLabel(scenarioId)}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="client-button client-button--primary">
          Применить
        </button>
      </form>
    </section>
  );
}

function HistoryTable({ history, onNavigate }: { history: HistorySessionSummaryDTO[]; onNavigate: (path: string) => void }) {
  /** Render the client history table using public-safe fields only. */
  return (
    <div className="client-table-wrap">
      <table className="client-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Пользователь</th>
            <th>Статус</th>
            <th>Сценарий</th>
            <th>Ходы</th>
            <th>Интерес</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {history.map((item) => <HistoryTableRow key={item.session_id} item={item} onNavigate={onNavigate} />)}
        </tbody>
      </table>
    </div>
  );
}

function HistoryTableRow({ item, onNavigate }: { item: HistorySessionSummaryDTO; onNavigate: (path: string) => void }) {
  /** Render one history row without technical database identifiers. */
  return (
    <tr>
      <td>{formatClientDate(item.started_at)}</td>
      <td>{item.user_email}</td>
      <td><ClientBadge>{statusLabel(item.status)}</ClientBadge></td>
      <td>{scenarioLabel(item.scenario_id)}</td>
      <td>{item.turn_count}</td>
      <td>{item.final_interest_score ?? "—"}</td>
      <td>
        <button type="button" className="client-link-button" onClick={() => onNavigate(`/app/history/${item.session_id}`)}>
          Открыть
        </button>
      </td>
    </tr>
  );
}

function HistoryTurnsList({ turns }: { turns: HistoryTurnDTO[] }) {
  /** Render manager/client turns from public history without hidden persona state. */
  return (
    <section className="client-panel">
      <h2>Ходы</h2>
      {turns.length === 0 ? (
        <ClientState title="Ходов нет" />
      ) : (
        <div className="client-turn-list">
          {turns.map((turn) => (
            <article key={turn.turn_index}>
              <ClientBadge>#{turn.turn_index}</ClientBadge>
              <p><strong>Менеджер:</strong> {turn.manager_message}</p>
              <p><strong>Клиент:</strong> {turn.client_answer}</p>
              <p className="client-muted">
                Интерес {turn.interest_before} → {turn.interest_after}; этап {stageLabel(turn.stage_before)} → {stageLabel(turn.stage_after)}
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
