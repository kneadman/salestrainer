import { useEffect, useState } from "react";
import { ReportSurface } from "../components/ReportSurface";
import { buildHistorySessionViewModel, buildHistoryTurnViewModel } from "../viewModels";
import { getHistorySession, listOrganizationHistory, listOrganizations, listTrainingConfigs } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import type { HistorySessionDetailDTO, HistorySessionSummaryDTO, OrganizationDTO, TrainingConfigDTO } from "./types";
import { getErrorMessage } from "./utils";

type HistoryPageProps = {
  sessionId?: string;
  onNavigate: (path: string) => void;
};

export function HistoryPage({ sessionId, onNavigate }: HistoryPageProps) {
  /** Route to either global history list or session detail depending on path state. */
  if (sessionId) {
    return <HistoryDetail sessionId={sessionId} onNavigate={onNavigate} />;
  }
  return <HistoryList onNavigate={onNavigate} />;
}

function HistoryList({ onNavigate }: { onNavigate: (path: string) => void }) {
  /** Load organization-scoped history for the selected organization filter. */
  const [organizations, setOrganizations] = useState<OrganizationDTO[]>([]);
  const [trainingConfigs, setTrainingConfigs] = useState<TrainingConfigDTO[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [status, setStatus] = useState("");
  const [trainingConfigId, setTrainingConfigId] = useState("");
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async (selectedOrganizationId: string, selectedStatus = status, selectedTrainingConfigId = trainingConfigId) => {
    /** Fetch history rows only when an organization is selected. */
    if (!selectedOrganizationId) {
      setHistory([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setHistory(
        await listOrganizationHistory(selectedOrganizationId, {
          status: selectedStatus,
          training_config_id: selectedTrainingConfigId,
          limit: 100,
          offset: 0,
        }),
      );
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    /** Bootstrap organizations and load history for the first organization when available. */
    const bootstrap = async () => {
      setLoading(true);
      setError(null);
      try {
        const orgs = await listOrganizations();
        setOrganizations(orgs);
        const firstId = orgs[0]?.id ?? "";
        setOrganizationId(firstId);
        const [configs] = await Promise.all([
          firstId ? listTrainingConfigs(firstId) : Promise.resolve([]),
          load(firstId, "", ""),
        ]);
        setTrainingConfigs(configs);
      } catch (bootstrapError) {
        setError(getErrorMessage(bootstrapError));
        setLoading(false);
      }
    };
    void bootstrap();
  }, []);

  if (loading) {
    return <LoadingState title="Загрузка истории тренировок" />;
  }

  if (error) {
    return <ErrorState title="История недоступна" detail={error} />;
  }

  const vms = history.map(buildHistorySessionViewModel);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <span className="admin-kicker">Постоянная история</span>
          <h1>История тренировок</h1>
        </div>
      </div>
      <section className="admin-panel">
        <form
          className="admin-form admin-form--inline"
          onSubmit={(event) => {
            event.preventDefault();
            void load(organizationId);
          }}
        >
          <label>
            <span>Организация</span>
            <select
              value={organizationId}
              onChange={(event) => {
                setOrganizationId(event.target.value);
                setTrainingConfigId("");
                const selectedOrganizationId = event.target.value;
                void listTrainingConfigs(selectedOrganizationId).then(setTrainingConfigs).catch(() => setTrainingConfigs([]));
                void load(selectedOrganizationId, status, "");
              }}
            >
              {organizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Статус</span>
            <select value={status} onChange={(event) => setStatus(event.target.value)}>
              <option value="">Все статусы</option>
              <option value="active">Активные</option>
              <option value="finished">Завершённые</option>
              <option value="expired">Истёкшие</option>
            </select>
          </label>
          <label>
            <span>Настройка тренировки</span>
            <select value={trainingConfigId} onChange={(event) => setTrainingConfigId(event.target.value)}>
              <option value="">Все настройки</option>
              {trainingConfigs.map((config) => (
                <option key={config.id} value={config.id}>{config.name}</option>
              ))}
            </select>
          </label>
          <button type="submit" className="admin-button admin-button--primary">
            Применить
          </button>
        </form>
      </section>
      <section className="admin-panel">
        {history.length === 0 ? (
          <EmptyState title="Истории нет" detail="Нет сессий под выбранные фильтры." />
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Начало</th>
                  <th>Пользователь</th>
                  <th>Статус</th>
                  <th>Настройка</th>
                  <th>Ходы</th>
                  <th>Интерес</th>
                  <th>Действия</th>
                </tr>
              </thead>
              <tbody>
                {vms.map((vm) => (
                  <tr key={vm.sessionId}>
                    <td>{vm.startedAtLabel}</td>
                    <td>{vm.userEmail}</td>
                    <td>
                      <Badge>{vm.statusLabel}</Badge>
                    </td>
                    <td>{vm.trainingConfigLabel}</td>
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
        )}
      </section>
    </div>
  );
}

function HistoryDetail({ sessionId, onNavigate }: { sessionId: string; onNavigate: (path: string) => void }) {
  /** Load and render one public-safe persistent history session detail. */
  const [detail, setDetail] = useState<HistorySessionDetailDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Fetch session detail from the history API by id. */
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        setDetail(await getHistorySession(sessionId));
      } catch (loadError) {
        setError(getErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [sessionId]);

  if (loading) {
    return <LoadingState title="Загрузка истории сессии" />;
  }

  if (error || !detail) {
    return <ErrorState title="История сессии недоступна" detail={error ?? "Сессия не найдена."} />;
  }

  const sessionVm = buildHistorySessionViewModel(detail.session);
  const turnVms = detail.turns.map(buildHistoryTurnViewModel);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <a href="/admin/history" className="admin-link-button" onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate("/admin/history"); }}>
            ← История
          </a>
          <h1>Тренировка от {sessionVm.startedAtLabel}</h1>
          <p className="admin-muted">
            {detail.session.user_email} · {sessionVm.trainingConfigLabel}
          </p>
        </div>
        <Badge>{sessionVm.statusLabel}</Badge>
      </div>
      <section className="admin-panel">
        <h2>Сводка</h2>
        <p>{detail.session.summary ?? "Сводки нет."}</p>
        <p className="admin-muted">{detail.public_brief ?? ""}</p>
      </section>
      <section className="admin-panel">
        <h2>Ходы</h2>
        {detail.turns.length === 0 ? (
          <EmptyState title="Ходов нет" />
        ) : (
          <div className="admin-history-turns">
            {turnVms.map((vm) => (
              <article key={vm.turnIndex}>
                <div>
                  <Badge>#{vm.turnIndex}</Badge>
                  <span>{vm.createdAtLabel}</span>
                </div>
                <p>
                  <strong>Менеджер:</strong> {vm.managerMessage}
                </p>
                <p>
                  <strong>Клиент:</strong> {vm.clientAnswer}
                </p>
                <p className="admin-muted">
                  Интерес {vm.interestBefore} → {vm.interestAfter}; этап {vm.stageBeforeLabel} → {vm.stageAfterLabel}
                </p>
              </article>
            ))}
          </div>
        )}
      </section>
      <section className="admin-panel admin-report-panel">
        <div className="admin-panel__header">
          <div>
            <h2>Отчёт</h2>
            <p className="admin-muted">Структурированная оценка тренировки</p>
          </div>
        </div>
        {!detail.report ? (
          <EmptyState title="Сохранённого отчёта нет" />
        ) : (
          <div className="admin-structured-report">
            <ReportSurface
              report={detail.report.report}
              reportPayload={detail.report.report_payload ?? null}
              fallbackClassName="admin-report-fallback"
              fallbackTextClassName="admin-report-block"
            />
          </div>
        )}
      </section>
    </div>
  );
}
