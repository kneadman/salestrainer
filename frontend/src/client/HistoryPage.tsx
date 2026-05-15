import { useEffect, useMemo, useState } from "react";
import { getHistorySessionDetail, getHistorySessions, getTrainingConfigs } from "./api";
import { ReportSurface } from "../components/ReportSurface";
import { ClientBadge, ClientState } from "./components/ClientPrimitives";
import type { HistorySessionDetailDTO, HistorySessionSummaryDTO, HistoryTurnDTO, TrainingConfigOptionDTO } from "./types";
import { scenarioLabel, stageLabel, statusLabel } from "../labels";
import { formatClientDate, getClientErrorMessage } from "./utils";

type HistoryPageProps = {
  sessionId?: string;
  path?: string;
  onNavigate: (path: string, replace?: boolean) => void;
};

export function HistoryPage({ sessionId, path = "/app/history", onNavigate }: HistoryPageProps) {
  /** Route history list and detail screens within the client cabinet. */
  if (sessionId) {
    return <HistoryDetail sessionId={sessionId} onNavigate={onNavigate} />;
  }
  return <HistoryList path={path} onNavigate={onNavigate} />;
}

function historyFiltersFromPath(path: string): { status: string; trainingConfigId: string } {
  /** Read history filters from the current URL query string. */
  const query = path.includes("?") ? path.slice(path.indexOf("?")) : "";
  const params = new URLSearchParams(query);
  return {
    status: params.get("status") ?? "",
    trainingConfigId: params.get("training_config_id") ?? "",
  };
}

function historyFiltersPath(status: string, trainingConfigId: string): string {
  /** Build the canonical client history URL for selected filters. */
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (trainingConfigId) {
    params.set("training_config_id", trainingConfigId);
  }
  const query = params.toString();
  return query ? `/app/history?${query}` : "/app/history";
}

function trainingConfigLabel(item: HistorySessionSummaryDTO): string {
  /** Prefer the saved training config name and keep scenario label only as legacy fallback. */
  return item.training_config_name || scenarioLabel(item.scenario_id);
}

function HistoryList({ path, onNavigate }: { path: string; onNavigate: (path: string, replace?: boolean) => void }) {
  /** Render role-scoped persistent training history with simple filters. */
  const routeFilters = useMemo(() => historyFiltersFromPath(path), [path]);
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [trainingConfigs, setTrainingConfigs] = useState<TrainingConfigOptionDTO[]>([]);
  const [status, setStatus] = useState(routeFilters.status);
  const [trainingConfigId, setTrainingConfigId] = useState(routeFilters.trainingConfigId);
  const [configsLoading, setConfigsLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Keep form controls aligned with browser navigation and shareable URLs. */
    setStatus(routeFilters.status);
    setTrainingConfigId(routeFilters.trainingConfigId);
  }, [routeFilters.status, routeFilters.trainingConfigId]);

  useEffect(() => {
    /** Load filter options once without coupling them to route-driven history refetches. */
    const loadTrainingConfigs = async () => {
      try {
        setTrainingConfigs(await getTrainingConfigs());
      } catch (loadError) {
        setError(getClientErrorMessage(loadError));
      } finally {
        setConfigsLoading(false);
      }
    };
    void loadTrainingConfigs();
  }, []);

  useEffect(() => {
    /** Reload history whenever the route-derived filters change. */
    const loadHistory = async () => {
      setHistoryLoading(true);
      setError(null);
      try {
        setHistory(await getHistorySessions({ status, training_config_id: trainingConfigId, limit: 100, offset: 0 }));
      } catch (loadError) {
        setError(getClientErrorMessage(loadError));
      } finally {
        setHistoryLoading(false);
      }
    };
    void loadHistory();
  }, [routeFilters.status, routeFilters.trainingConfigId]);

  const applyFilters = (nextStatus: string, nextTrainingConfigId: string) => {
    /** Keep URL query as the single source of truth for history filters. */
    setStatus(nextStatus);
    setTrainingConfigId(nextTrainingConfigId);
    onNavigate(historyFiltersPath(nextStatus, nextTrainingConfigId), true);
  };

  const resetFilters = () => {
    /** Clear all active filters and return to the canonical history route. */
    applyFilters("", "");
  };

  if (configsLoading || historyLoading) {
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
      <HistoryFilters
        status={status}
        trainingConfigId={trainingConfigId}
        trainingConfigs={trainingConfigs}
        onStatusChange={(value) => applyFilters(value, trainingConfigId)}
        onTrainingConfigChange={(value) => applyFilters(status, value)}
        onReset={resetFilters}
      />
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
  trainingConfigId: string;
  trainingConfigs: TrainingConfigOptionDTO[];
  onStatusChange: (value: string) => void;
  onTrainingConfigChange: (value: string) => void;
  onReset: () => void;
}) {
  /** Render client-safe history filters without exposing backend enum names as input hints. */
  const hasFilters = Boolean(props.status || props.trainingConfigId);

  return (
    <section className="client-panel">
      <div className="client-form client-form--inline">
        <label>
          <span>Статус</span>
          <select value={props.status} onChange={(event) => props.onStatusChange(event.target.value)}>
            <option value="">Все статусы</option>
            <option value="active">Активные</option>
            <option value="finished">Завершённые</option>
            <option value="expired">Истёкшие</option>
          </select>
        </label>
        <label>
          <span>Настройка тренировки</span>
          <select value={props.trainingConfigId} onChange={(event) => props.onTrainingConfigChange(event.target.value)}>
            <option value="">Все настройки</option>
            {props.trainingConfigs.map((config) => (
              <option key={config.id} value={config.id}>
                {config.name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="client-button" onClick={props.onReset} disabled={!hasFilters}>
          Сбросить фильтры
        </button>
      </div>
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
            <th>Настройка</th>
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
      <td>{trainingConfigLabel(item)}</td>
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
