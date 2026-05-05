import { FormEvent, useEffect, useMemo, useState } from "react";
import { roleLabel, scenarioLabel, statusLabel as entityStatusLabel } from "../labels";
import {
  assignTrainingConfig,
  createTrainingConfig,
  createUser,
  disableTrainingConfig,
  disableUser,
  enableTrainingConfig,
  enableUser,
  getUsageSummary,
  listAuditLog,
  listOrganizationHistory,
  listOrganizations,
  listScenarios,
  listTrainingConfigs,
  listUserTrainingConfigs,
  listUsers,
  makeDefaultTrainingConfig,
  resetUserPassword,
  unassignTrainingConfig,
  updateTrainingConfig,
  updateUser,
} from "./api";
import { Badge, EmptyState, ErrorState, LoadingState, StatCard } from "./components/AdminPrimitives";
import type {
  AuditLogDTO,
  HistorySessionSummaryDTO,
  OrganizationDTO,
  ScenarioOptionDTO,
  TrainingConfigDTO,
  TrainingConfigPayload,
  UsageSummaryDTO,
  UserDTO,
  UserTrainingConfigAssignmentDTO,
} from "./types";
import { FALLBACK_SCENARIOS, compactJson, formatDate, getErrorMessage, parseJsonObject, statusLabel, stringifyJson } from "./utils";

type OrganizationDetailPageProps = {
  organizationId: string;
  onNavigate: (path: string) => void;
};

type DetailTab = "overview" | "users" | "configs" | "history" | "usage" | "audit";

type UserForm = {
  email: string;
  password: string;
  role: "client_lead" | "client_manager";
};

type ConfigForm = {
  id?: string;
  name: string;
  default_scenario_id: string;
  persona_generation_prompt: string;
  persona_policy: string;
  ui_config: string;
  limits: string;
};

const DEFAULT_CONFIG_FORM: ConfigForm = {
  name: "",
  default_scenario_id: "first_contact_discovery",
  persona_generation_prompt: "",
  persona_policy: "{}",
  ui_config: "{}",
  limits: "{}",
};

const TAB_LABELS: Record<DetailTab, string> = {
  overview: "Обзор",
  users: "Пользователи",
  configs: "Конфиги",
  history: "История",
  usage: "Использование",
  audit: "Аудит",
};

export function OrganizationDetailPage({ organizationId, onNavigate }: OrganizationDetailPageProps) {
  /** Render one organization workspace with users, training configs, history, usage, and audit sections. */
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [organization, setOrganization] = useState<OrganizationDTO | null>(null);
  const [users, setUsers] = useState<UserDTO[]>([]);
  const [configs, setConfigs] = useState<TrainingConfigDTO[]>([]);
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [usage, setUsage] = useState<UsageSummaryDTO | null>(null);
  const [audit, setAudit] = useState<AuditLogDTO[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioOptionDTO[]>([]);
  const [assignmentsByUser, setAssignmentsByUser] = useState<Record<string, UserTrainingConfigAssignmentDTO[]>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [userForm, setUserForm] = useState<UserForm>({ email: "", password: "", role: "client_manager" });
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [resetPasswordByUser, setResetPasswordByUser] = useState<Record<string, string>>({});
  const [configForm, setConfigForm] = useState<ConfigForm>(DEFAULT_CONFIG_FORM);

  const scenarioIds = useMemo(() => {
    /** Prefer backend scenario options but keep known ids when the list endpoint is unavailable. */
    return scenarios.length > 0 ? scenarios.map((scenario) => scenario.scenario_id) : FALLBACK_SCENARIOS;
  }, [scenarios]);

  const loadAll = async () => {
    /** Load all organization detail data from internal admin endpoints. */
    setLoading(true);
    setError(null);
    try {
      const orgs = await listOrganizations();
      const selectedOrg = orgs.find((item) => item.id === organizationId) ?? null;
      setOrganization(selectedOrg);
      if (!selectedOrg) {
        throw new Error("Организация не найдена.");
      }
      const [loadedUsers, loadedConfigs, loadedHistory, loadedUsage, loadedAudit, loadedScenarios] = await Promise.all([
        listUsers(organizationId),
        listTrainingConfigs(organizationId),
        listOrganizationHistory(organizationId, { limit: 50, offset: 0 }).catch(() => []),
        getUsageSummary(organizationId).catch(() => null),
        listAuditLog({ organization_id: organizationId, limit: 50, offset: 0 }).catch(() => []),
        listScenarios().catch(() => []),
      ]);
      setUsers(loadedUsers);
      setConfigs(loadedConfigs);
      setHistory(loadedHistory);
      setUsage(loadedUsage);
      setAudit(loadedAudit);
      setScenarios(loadedScenarios);
      const assignmentEntries = await Promise.all(
        loadedUsers.map(async (user) => [user.id, await listUserTrainingConfigs(user.id).catch(() => [])] as const),
      );
      setAssignmentsByUser(Object.fromEntries(assignmentEntries));
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    /** Refresh detail data when the organization id changes. */
    void loadAll();
  }, [organizationId]);

  const submitUser = async (event: FormEvent<HTMLFormElement>) => {
    /** Create or update a client user without allowing internal_admin role creation. */
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      if (editingUserId) {
        await updateUser(editingUserId, { email: userForm.email, role: userForm.role });
        setSuccess("Пользователь обновлён.");
      } else {
        await createUser(organizationId, userForm);
        setSuccess("Пользователь создан.");
      }
      setUserForm({ email: "", password: "", role: "client_manager" });
      setEditingUserId(null);
      await loadAll();
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setBusy(false);
    }
  };

  const toggleUser = async (user: UserDTO) => {
    /** Enable or disable one client user after confirmation for disable. */
    if (user.is_active && !window.confirm(`Отключить пользователя ${user.email}?`)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (user.is_active) {
        await disableUser(user.id);
      } else {
        await enableUser(user.id);
      }
      setSuccess(user.is_active ? "Пользователь отключён." : "Пользователь включён.");
      await loadAll();
    } catch (toggleError) {
      setError(getErrorMessage(toggleError));
    } finally {
      setBusy(false);
    }
  };

  const resetPassword = async (user: UserDTO) => {
    /** Reset a user password and clear the local password field afterwards. */
    const password = resetPasswordByUser[user.id] ?? "";
    if (!password || !window.confirm(`Сбросить пароль для ${user.email}?`)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetUserPassword(user.id, password);
      setResetPasswordByUser({ ...resetPasswordByUser, [user.id]: "" });
      setSuccess("Пароль сброшен.");
      await loadAll();
    } catch (resetError) {
      setError(getErrorMessage(resetError));
    } finally {
      setBusy(false);
    }
  };

  const configPayload = (): TrainingConfigPayload => {
    /** Build a training config payload after validating JSON textareas. */
    return {
      name: configForm.name,
      default_scenario_id: configForm.default_scenario_id,
      persona_generation_prompt: configForm.persona_generation_prompt,
      persona_policy: parseJsonObject(configForm.persona_policy, "persona_policy"),
      ui_config: parseJsonObject(configForm.ui_config, "ui_config"),
      limits: parseJsonObject(configForm.limits, "limits"),
      llm_provider_config_id: null,
    };
  };

  const submitConfig = async (event: FormEvent<HTMLFormElement>) => {
    /** Create or update a training config with client-side JSON validation. */
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      if (configForm.id) {
        await updateTrainingConfig(configForm.id, configPayload());
        setSuccess("Тренировочный конфиг обновлён.");
      } else {
        await createTrainingConfig(organizationId, configPayload());
        setSuccess("Тренировочный конфиг создан.");
      }
      setConfigForm(DEFAULT_CONFIG_FORM);
      await loadAll();
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setBusy(false);
    }
  };

  const toggleConfig = async (config: TrainingConfigDTO) => {
    /** Enable or disable one training config after confirmation for disable. */
    if (config.is_active && !window.confirm(`Отключить тренировочный конфиг ${config.name}?`)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (config.is_active) {
        await disableTrainingConfig(config.id);
      } else {
        await enableTrainingConfig(config.id);
      }
      setSuccess(config.is_active ? "Тренировочный конфиг отключён." : "Тренировочный конфиг включён.");
      await loadAll();
    } catch (toggleError) {
      setError(getErrorMessage(toggleError));
    } finally {
      setBusy(false);
    }
  };

  const handleAssignment = async (userId: string, configId: string, action: "assign" | "default" | "unassign") => {
    /** Run one training config assignment action for a user. */
    if (action === "unassign" && !window.confirm("Убрать этот конфиг у пользователя?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (action === "assign") {
        await assignTrainingConfig(userId, configId);
      } else if (action === "default") {
        await makeDefaultTrainingConfig(userId, configId);
      } else {
        await unassignTrainingConfig(userId, configId);
      }
      setSuccess("Назначение обновлено.");
      await loadAll();
    } catch (assignmentError) {
      setError(getErrorMessage(assignmentError));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <LoadingState title="Загрузка организации" />;
  }

  if (error && !organization) {
    return <ErrorState title="Организация недоступна" detail={error} />;
  }

  if (!organization) {
    return <EmptyState title="Организация не найдена" />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <button type="button" className="admin-link-button" onClick={() => onNavigate("/admin/organizations")}>
            ← Организации
          </button>
          <h1>{organization.name}</h1>
          <p className="admin-muted">
            {organization.slug} · создана {formatDate(organization.created_at)} · обновлена {formatDate(organization.updated_at)}
          </p>
        </div>
        <Badge tone={organization.is_active ? "good" : "danger"}>{entityStatusLabel(organization.is_active)}</Badge>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      {success ? <div className="admin-alert">{success}</div> : null}
      <div className="admin-tabs">
        {(["overview", "users", "configs", "history", "usage", "audit"] as DetailTab[]).map((tab) => (
          <button key={tab} type="button" className={activeTab === tab ? "admin-tab admin-tab--active" : "admin-tab"} onClick={() => setActiveTab(tab)}>
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      {activeTab === "overview" ? (
        <OverviewSection organization={organization} usage={usage} />
      ) : null}
      {activeTab === "users" ? (
        <UsersSection
          users={users}
          configs={configs}
          assignmentsByUser={assignmentsByUser}
          userForm={userForm}
          setUserForm={setUserForm}
          editingUserId={editingUserId}
          setEditingUserId={setEditingUserId}
          resetPasswordByUser={resetPasswordByUser}
          setResetPasswordByUser={setResetPasswordByUser}
          busy={busy}
          onSubmit={submitUser}
          onToggle={toggleUser}
          onReset={resetPassword}
          onAssignment={handleAssignment}
        />
      ) : null}
      {activeTab === "configs" ? (
        <ConfigsSection
          configs={configs}
          scenarioIds={scenarioIds}
          form={configForm}
          setForm={setConfigForm}
          busy={busy}
          onSubmit={submitConfig}
          onToggle={toggleConfig}
        />
      ) : null}
      {activeTab === "history" ? <HistorySection history={history} onNavigate={onNavigate} /> : null}
      {activeTab === "usage" ? <UsageSection usage={usage} /> : null}
      {activeTab === "audit" ? <AuditSection audit={audit} /> : null}
    </div>
  );
}

function OverviewSection({ organization, usage }: { organization: OrganizationDTO; usage: UsageSummaryDTO | null }) {
  /** Render organization summary cards and MVP LLM architecture note. */
  return (
    <>
      <section className="admin-stats-grid">
        <StatCard label="Пользователи" value={organization.users_count} detail={`${organization.active_users_count} активны`} />
        <StatCard label="Тренировочные конфиги" value={organization.training_configs_count} />
        <StatCard label="Всего сессий" value={usage?.total_sessions ?? "—"} />
        <StatCard label="Завершено сессий" value={usage?.finished_sessions ?? "—"} />
        <StatCard label="Всего сообщений" value={usage?.total_turns ?? "—"} />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>MVP LLM flow</h2></div>
        <p className="admin-muted">
          Для MVP организация настраивает только бизнес-контекст тренировки. Глобальные Yandex API key, persona agent и
          dialogue agent берутся из конфигурации приложения и не редактируются в UI организации.
        </p>
      </section>
    </>
  );
}

function UsersSection(props: {
  users: UserDTO[];
  configs: TrainingConfigDTO[];
  assignmentsByUser: Record<string, UserTrainingConfigAssignmentDTO[]>;
  userForm: UserForm;
  setUserForm: (form: UserForm) => void;
  editingUserId: string | null;
  setEditingUserId: (id: string | null) => void;
  resetPasswordByUser: Record<string, string>;
  setResetPasswordByUser: (value: Record<string, string>) => void;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (user: UserDTO) => void;
  onReset: (user: UserDTO) => void;
  onAssignment: (userId: string, configId: string, action: "assign" | "default" | "unassign") => void;
}) {
  /** Render user form, assignments, and reset-password actions. */
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Пользователи</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label><span>Email</span><input type="email" value={props.userForm.email} onChange={(event) => props.setUserForm({ ...props.userForm, email: event.target.value })} required /></label>
          <label><span>Пароль</span><input type="password" minLength={8} value={props.userForm.password} onChange={(event) => props.setUserForm({ ...props.userForm, password: event.target.value })} required={!props.editingUserId} /></label>
          <label><span>Роль</span><select value={props.userForm.role} onChange={(event) => props.setUserForm({ ...props.userForm, role: event.target.value as UserForm["role"] })}><option value="client_manager">Менеджер</option><option value="client_lead">Руководитель</option></select></label>
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.editingUserId ? "Обновить пользователя" : "Создать пользователя"}</button>
      </form>
      {props.users.length === 0 ? <EmptyState title="Пользователей нет" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Email</th><th>Роль</th><th>Статус</th><th>Конфиги</th><th>Пароль</th><th>Действия</th></tr></thead>
            <tbody>
              {props.users.map((user) => {
                const assignments = props.assignmentsByUser[user.id] ?? [];
                return (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>{roleLabel(user.role)}</td>
                    <td><Badge tone={user.is_active ? "good" : "danger"}>{statusLabel(user.is_active)}</Badge></td>
                    <td>
                      <div className="admin-assignment-list">
                        {props.configs.map((config) => {
                          const assigned = assignments.find((item) => item.training_config_id === config.id);
                          return (
                            <div key={config.id}>
                              <span>{config.name}</span>
                              {assigned?.is_default ? <Badge tone="good">по умолчанию</Badge> : null}
                              <button type="button" className="admin-link-button" onClick={() => props.onAssignment(user.id, config.id, assigned ? "default" : "assign")}>
                                {assigned ? "По умолчанию" : "Назначить"}
                              </button>
                              {assigned ? <button type="button" className="admin-link-button" onClick={() => props.onAssignment(user.id, config.id, "unassign")}>Убрать</button> : null}
                            </div>
                          );
                        })}
                      </div>
                    </td>
                    <td>
                      <div className="admin-password-reset">
                        <input
                          type="password"
                          placeholder="Новый временный пароль"
                          minLength={8}
                          value={props.resetPasswordByUser[user.id] ?? ""}
                          onChange={(event) => props.setResetPasswordByUser({ ...props.resetPasswordByUser, [user.id]: event.target.value })}
                        />
                        <button type="button" className="admin-link-button" onClick={() => props.onReset(user)}>Сбросить</button>
                      </div>
                    </td>
                    <td>
                      <div className="admin-row-actions">
                        <button type="button" className="admin-link-button" onClick={() => {
                          props.setEditingUserId(user.id);
                          props.setUserForm({ email: user.email, password: "", role: user.role === "client_lead" ? "client_lead" : "client_manager" });
                        }}>Изменить</button>
                        <button type="button" className="admin-link-button" onClick={() => props.onToggle(user)}>{user.is_active ? "Отключить" : "Включить"}</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ConfigsSection(props: {
  configs: TrainingConfigDTO[];
  scenarioIds: string[];
  form: ConfigForm;
  setForm: (form: ConfigForm) => void;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (config: TrainingConfigDTO) => void;
}) {
  /** Render training config form, prompt field, JSON fields, and config list. */
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Тренировочные конфиги</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label><span>Название</span><input value={props.form.name} onChange={(event) => props.setForm({ ...props.form, name: event.target.value })} required /></label>
          <label><span>Формат тренировки</span><select value={props.form.default_scenario_id} onChange={(event) => props.setForm({ ...props.form, default_scenario_id: event.target.value })}>{props.scenarioIds.map((id) => <option key={id} value={id}>{scenarioLabel(id)}</option>)}</select></label>
        </div>
        <label>
          <span>Промпт генерации личности</span>
          <textarea
            rows={8}
            value={props.form.persona_generation_prompt}
            onChange={(event) => props.setForm({ ...props.form, persona_generation_prompt: event.target.value })}
          />
          <small className="admin-muted">
            Мастер-промпт является источником продуктовой логики: продукт, рынок, ЦА, роли ЛПР, боли, возражения, критерии выбора, ограничения и поведение клиента.
          </small>
        </label>
        <div className="admin-json-grid">
          <label><span>Дополнительные JSON-настройки личности</span><textarea value={props.form.persona_policy} onChange={(event) => props.setForm({ ...props.form, persona_policy: event.target.value })} /></label>
          <label><span>UI-конфиг JSON</span><textarea value={props.form.ui_config} onChange={(event) => props.setForm({ ...props.form, ui_config: event.target.value })} /></label>
          <label><span>Лимиты JSON</span><textarea value={props.form.limits} onChange={(event) => props.setForm({ ...props.form, limits: event.target.value })} /></label>
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.form.id ? "Обновить конфиг" : "Создать конфиг"}</button>
      </form>
      {props.configs.length === 0 ? <EmptyState title="Тренировочных конфигов нет" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Название</th><th>Формат</th><th>Промпт</th><th>Статус</th><th>Действия</th></tr></thead>
            <tbody>
              {props.configs.map((config) => (
                <tr key={config.id}>
                  <td>{config.name}</td>
                  <td>{scenarioLabel(config.default_scenario_id)}</td>
                  <td>{config.persona_generation_prompt ? `${config.persona_generation_prompt.slice(0, 120)}${config.persona_generation_prompt.length > 120 ? "..." : ""}` : "—"}</td>
                  <td><Badge tone={config.is_active ? "good" : "danger"}>{statusLabel(config.is_active)}</Badge></td>
                  <td>
                    <div className="admin-row-actions">
                      <button
                        type="button"
                        className="admin-link-button"
                        onClick={() => props.setForm({
                          id: config.id,
                          name: config.name,
                          default_scenario_id: config.default_scenario_id,
                          persona_generation_prompt: config.persona_generation_prompt,
                          persona_policy: stringifyJson(config.persona_policy),
                          ui_config: stringifyJson(config.ui_config),
                          limits: stringifyJson(config.limits),
                        })}
                      >
                        Изменить
                      </button>
                      <button type="button" className="admin-link-button" onClick={() => props.onToggle(config)}>{config.is_active ? "Отключить" : "Включить"}</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function HistorySection({ history, onNavigate }: { history: HistorySessionSummaryDTO[]; onNavigate: (path: string) => void }) {
  /** Render persistent training history rows without hidden snapshots. */
  if (history.length === 0) {
    return <EmptyState title="История тренировок пуста" detail="История появится после первых сохранённых тренировок." />;
  }
  return <section className="admin-panel"><div className="admin-panel__header"><h2>История тренировок</h2></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>ID сессии</th><th>Пользователь</th><th>Статус</th><th>Сценарий</th><th>Сообщения</th><th>Интерес</th><th>Начало</th><th>Действия</th></tr></thead><tbody>{history.map((session) => <tr key={session.session_id}><td>{session.session_id.slice(0, 8)}</td><td>{session.user_email}</td><td><Badge>{entityStatusLabel(session.status)}</Badge></td><td>{scenarioLabel(session.scenario_id)}</td><td>{session.turn_count}</td><td>{session.final_interest_score ?? "—"}</td><td>{formatDate(session.started_at)}</td><td><button type="button" className="admin-link-button" onClick={() => onNavigate(`/admin/history/sessions/${session.session_id}`)}>Открыть</button></td></tr>)}</tbody></table></div></section>;
}

function UsageSection({ usage }: { usage: UsageSummaryDTO | null }) {
  /** Render basic usage analytics from the persistent history summary endpoint. */
  if (!usage) {
    return <EmptyState title="Сводка использования недоступна" detail="Backend не вернул сводку использования для этой организации." />;
  }
  return <section className="admin-panel"><div className="admin-panel__header"><h2>Аналитика использования</h2></div><div className="admin-stats-grid"><StatCard label="Всего сессий" value={usage.total_sessions} /><StatCard label="Завершено" value={usage.finished_sessions} /><StatCard label="Активно" value={usage.active_sessions} /><StatCard label="Уникальные пользователи" value={usage.unique_users} /><StatCard label="Всего сообщений" value={usage.total_turns} /><StatCard label="Средний интерес" value={usage.avg_final_interest_score ?? "—"} /><StatCard label="Среднее число ходов" value={usage.avg_turn_count ?? "—"} /><StatCard label="События использования" value={usage.usage_events_count} /></div><pre className="admin-json-block">{compactJson({ sessions_by_status: usage.sessions_by_status, sessions_by_scenario: usage.sessions_by_scenario, sessions_by_training_config: usage.sessions_by_training_config })}</pre></section>;
}

function AuditSection({ audit }: { audit: AuditLogDTO[] }) {
  /** Render organization-scoped audit events with compact JSON payloads. */
  if (audit.length === 0) {
    return <EmptyState title="Событий аудита нет" />;
  }
  return <section className="admin-panel"><div className="admin-panel__header"><h2>Аудит</h2></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Время</th><th>Действие</th><th>Сущность</th><th>Автор</th><th>Данные</th></tr></thead><tbody>{audit.map((event) => <tr key={event.id}><td>{formatDate(event.created_at)}</td><td>{event.action}</td><td>{event.entity_type}</td><td>{event.actor_user_id ?? "система"}</td><td><pre className="admin-json-cell">{compactJson(event.payload)}</pre></td></tr>)}</tbody></table></div></section>;
}
