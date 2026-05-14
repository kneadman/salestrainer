import { FormEvent, useEffect, useState } from "react";
import { auditActionLabel, auditEntityLabel, roleLabel, scenarioLabel, statusLabel as entityStatusLabel } from "../labels";
import {
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
  listTrainingConfigs,
  listUsers,
  resetUserPassword,
  updateTrainingConfig,
  updateUser,
} from "./api";
import { Badge, EmptyState, ErrorState, LoadingState, StatCard } from "./components/AdminPrimitives";
import type {
  AuditLogDTO,
  HistorySessionSummaryDTO,
  OrganizationDetailTab,
  OrganizationDTO,
  TrainingConfigDTO,
  UsageSummaryDTO,
  UserDTO,
} from "./types";
import { auditPayloadSummary, formatDate, getErrorMessage, statusLabel } from "./utils";

type OrganizationDetailPageProps = {
  organizationId: string;
  initialTab?: OrganizationDetailTab;
  onNavigate: (path: string) => void;
};

type UserForm = {
  email: string;
  password: string;
  role: "client_lead" | "client_manager";
  default_training_config_id: string | null;
};

type ConfigForm = {
  id?: string;
  name: string;
  persona_generation_context: string;
};

const DEFAULT_CONFIG_FORM: ConfigForm = {
  name: "",
  persona_generation_context: "",
};

const TAB_LABELS: Record<OrganizationDetailTab, string> = {
  overview: "Обзор",
  users: "Пользователи",
  configs: "Настройки",
  history: "История",
  usage: "Использование",
  audit: "Аудит",
};

export function OrganizationDetailPage({ organizationId, initialTab, onNavigate }: OrganizationDetailPageProps) {
  /** Render one organization workspace with users, training configs, history, usage, and audit sections. */
  const [activeTab, setActiveTab] = useState<OrganizationDetailTab>(initialTab ?? "overview");
  const [organization, setOrganization] = useState<OrganizationDTO | null>(null);
  const [users, setUsers] = useState<UserDTO[]>([]);
  const [configs, setConfigs] = useState<TrainingConfigDTO[]>([]);
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [usage, setUsage] = useState<UsageSummaryDTO | null>(null);
  const [audit, setAudit] = useState<AuditLogDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [userForm, setUserForm] = useState<UserForm>({ email: "", password: "", role: "client_manager", default_training_config_id: null });
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [resetPasswordByUser, setResetPasswordByUser] = useState<Record<string, string>>({});
  const [configForm, setConfigForm] = useState<ConfigForm>(DEFAULT_CONFIG_FORM);

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
      const [loadedUsers, loadedConfigs, loadedHistory, loadedUsage, loadedAudit] = await Promise.all([
        listUsers(organizationId),
        listTrainingConfigs(organizationId),
        listOrganizationHistory(organizationId, { limit: 50, offset: 0 }).catch(() => []),
        getUsageSummary(organizationId).catch(() => null),
        listAuditLog({ organization_id: organizationId, limit: 50, offset: 0 }).catch(() => []),
      ]);
      setUsers(loadedUsers);
      setConfigs(loadedConfigs);
      setHistory(loadedHistory);
      setUsage(loadedUsage);
      setAudit(loadedAudit);
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

  useEffect(() => {
    /** Sync requested tab from the route when organization detail opens or changes. */
    setActiveTab(initialTab ?? "overview");
  }, [organizationId, initialTab]);

  const submitUser = async (event: FormEvent<HTMLFormElement>) => {
    /** Create or update a client user without allowing internal_admin role creation. */
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      if (editingUserId) {
        await updateUser(editingUserId, {
          email: userForm.email,
          role: userForm.role,
          default_training_config_id: userForm.default_training_config_id,
        });
        setSuccess("Пользователь обновлён.");
      } else {
        await createUser(organizationId, { email: userForm.email, password: userForm.password, role: userForm.role });
        setSuccess("Пользователь создан.");
      }
      setUserForm({ email: "", password: "", role: "client_manager", default_training_config_id: null });
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

  const submitConfig = async (event: FormEvent<HTMLFormElement>) => {
    /** Create or update the visible training config fields. */
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      if (configForm.id) {
        await updateTrainingConfig(configForm.id, {
          name: configForm.name,
          persona_generation_context: configForm.persona_generation_context,
        });
        setSuccess("Настройка тренировки обновлена.");
      } else {
        await createTrainingConfig(organizationId, {
          name: configForm.name,
          persona_generation_context: configForm.persona_generation_context,
        });
        setSuccess("Настройка тренировки создана.");
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
    if (config.is_active && !window.confirm(`Отключить настройку тренировки ${config.name}?`)) {
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
      setSuccess(config.is_active ? "Настройка тренировки отключена." : "Настройка тренировки включена.");
      await loadAll();
    } catch (toggleError) {
      setError(getErrorMessage(toggleError));
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
        {(["overview", "users", "configs", "history", "usage", "audit"] as OrganizationDetailTab[]).map((tab) => (
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
          onOpenAnalytics={(userId) => onNavigate(`/admin/organizations/${organizationId}/users/${userId}/analytics`)}
        />
      ) : null}
      {activeTab === "configs" ? (
        <ConfigsSection
          configs={configs}
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
  /** Render organization summary cards and a product-level training architecture note. */
  return (
    <>
      <section className="admin-stats-grid">
        <StatCard label="Пользователи" value={organization.users_count} detail={`${organization.active_users_count} активны`} />
        <StatCard label="Настройки тренировок" value={organization.training_configs_count} />
        <StatCard label="Всего сессий" value={usage?.total_sessions ?? "—"} />
        <StatCard label="Завершено сессий" value={usage?.finished_sessions ?? "—"} />
        <StatCard label="Всего сообщений" value={usage?.total_turns ?? "—"} />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header"><h2>Как устроена тренировка</h2></div>
        <p className="admin-muted">
          Организация задаёт бизнес-контекст и сценарий. Диалог, оценка и история работают через защищённые серверные
          контракты, поэтому скрытая персона и служебные данные не попадают в клиентский кабинет.
        </p>
      </section>
    </>
  );
}

function UsersSection(props: {
  users: UserDTO[];
  configs: TrainingConfigDTO[];
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
  onOpenAnalytics: (userId: string) => void;
}) {
  /** Render user form, assignments, and reset-password actions. */
  const activeConfigs = props.configs.filter((c) => c.is_active);
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Пользователи</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label><span>Email</span><input type="email" value={props.userForm.email} onChange={(event) => props.setUserForm({ ...props.userForm, email: event.target.value })} required /></label>
          <label><span>Пароль</span><input type="password" minLength={8} value={props.userForm.password} onChange={(event) => props.setUserForm({ ...props.userForm, password: event.target.value })} required={!props.editingUserId} /></label>
          <label><span>Роль</span><select value={props.userForm.role} onChange={(event) => props.setUserForm({ ...props.userForm, role: event.target.value as UserForm["role"] })}><option value="client_manager">Менеджер</option><option value="client_lead">Руководитель</option></select></label>
          {props.editingUserId ? (
            <label>
              <span>Конфиг по умолчанию</span>
              <select
                value={props.userForm.default_training_config_id ?? ""}
                onChange={(event) => props.setUserForm({ ...props.userForm, default_training_config_id: event.target.value || null })}
              >
                <option value="">— Не выбран —</option>
                {activeConfigs.map((config) => (
                  <option key={config.id} value={config.id}>{config.name}</option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.editingUserId ? "Обновить пользователя" : "Создать пользователя"}</button>
      </form>
      {props.users.length === 0 ? <EmptyState title="Пользователей нет" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Email</th><th>Роль</th><th>Статус</th><th>Конфиг по умолчанию</th><th>Пароль</th><th>Действия</th></tr></thead>
            <tbody>
              {props.users.map((user) => {
                const defaultConfig = props.configs.find((c) => c.id === user.default_training_config_id);
                return (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>{roleLabel(user.role)}</td>
                    <td><Badge tone={user.is_active ? "good" : "danger"}>{statusLabel(user.is_active)}</Badge></td>
                    <td>{defaultConfig?.name ?? "—"}</td>
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
                        <button type="button" className="admin-link-button" onClick={() => props.onOpenAnalytics(user.id)}>Аналитика</button>
                        <button type="button" className="admin-link-button" onClick={() => {
                          props.setEditingUserId(user.id);
                          props.setUserForm({
                            email: user.email,
                            password: "",
                            role: user.role === "client_lead" ? "client_lead" : "client_manager",
                            default_training_config_id: user.default_training_config_id ?? null,
                          });
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
  form: ConfigForm;
  setForm: (form: ConfigForm) => void;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (config: TrainingConfigDTO) => void;
}) {
  /** Render simplified training config form and config list. */
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Настройки тренировок</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label><span>Название</span><input value={props.form.name} onChange={(event) => props.setForm({ ...props.form, name: event.target.value })} required /></label>
        </div>
        <label>
          <span>Контекст генерации личности</span>
          <textarea
            rows={8}
            value={props.form.persona_generation_context}
            onChange={(event) => props.setForm({ ...props.form, persona_generation_context: event.target.value })}
          />
          <small className="admin-muted">
            Опишите продукт клиента, целевую аудиторию, типичные роли ЛПР, боли, возражения, критерии выбора и ограничения.
          </small>
        </label>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.form.id ? "Обновить настройку" : "Создать настройку"}</button>
      </form>
      {props.configs.length === 0 ? <EmptyState title="Настроек тренировок нет" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Название</th><th>Контекст</th><th>Статус</th><th>Действия</th></tr></thead>
            <tbody>
              {props.configs.map((config) => (
                <tr key={config.id}>
                  <td>{config.name}</td>
                  <td>{config.persona_generation_context ? `${config.persona_generation_context.slice(0, 120)}${config.persona_generation_context.length > 120 ? "..." : ""}` : "—"}</td>
                  <td><Badge tone={config.is_active ? "good" : "danger"}>{statusLabel(config.is_active)}</Badge></td>
                  <td>
                    <div className="admin-row-actions">
                      <button
                        type="button"
                        className="admin-link-button"
                        onClick={() => props.setForm({
                          id: config.id,
                          name: config.name,
                          persona_generation_context: config.persona_generation_context,
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
  return <section className="admin-panel"><div className="admin-panel__header"><h2>История тренировок</h2></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Начало</th><th>Пользователь</th><th>Статус</th><th>Сценарий</th><th>Сообщения</th><th>Интерес</th><th>Действия</th></tr></thead><tbody>{history.map((session) => <tr key={session.session_id}><td>{formatDate(session.started_at)}</td><td>{session.user_email}</td><td><Badge>{entityStatusLabel(session.status)}</Badge></td><td>{scenarioLabel(session.scenario_id)}</td><td>{session.turn_count}</td><td>{session.final_interest_score ?? "—"}</td><td><button type="button" className="admin-link-button" onClick={() => onNavigate(`/admin/history/sessions/${session.session_id}`)}>Открыть</button></td></tr>)}</tbody></table></div></section>;
}

function UsageSection({ usage }: { usage: UsageSummaryDTO | null }) {
  /** Render basic usage analytics from the persistent history summary endpoint. */
  if (!usage) {
    return <EmptyState title="Сводка использования недоступна" detail="Сервис не вернул сводку использования для этой организации." />;
  }
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Аналитика использования</h2></div>
      <div className="admin-stats-grid">
        <StatCard label="Всего сессий" value={usage.total_sessions} />
        <StatCard label="Завершено" value={usage.finished_sessions} />
        <StatCard label="Активно" value={usage.active_sessions} />
        <StatCard label="Уникальные пользователи" value={usage.unique_users} />
        <StatCard label="Всего сообщений" value={usage.total_turns} />
        <StatCard label="Средний интерес" value={usage.avg_final_interest_score ?? "—"} />
        <StatCard label="Среднее число ходов" value={usage.avg_turn_count ?? "—"} />
        <StatCard label="События использования" value={usage.usage_events_count} />
        <StatCard label="Настроек с тренировками" value={Object.keys(usage.sessions_by_training_config).length} />
      </div>
      <div className="admin-usage-breakdowns">
        <UsageBreakdown title="По статусам" values={usage.sessions_by_status} labelFormatter={entityStatusLabel} />
        <UsageBreakdown title="По сценариям" values={usage.sessions_by_scenario} labelFormatter={scenarioLabel} />
      </div>
    </section>
  );
}

function UsageBreakdown({ title, values, labelFormatter }: { title: string; values: Record<string, number>; labelFormatter: (key: string) => string }) {
  /** Render aggregate usage values as readable rows instead of raw JSON maps. */
  const entries = Object.entries(values);
  if (entries.length === 0) {
    return null;
  }
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <caption>{title}</caption>
        <thead><tr><th>Группа</th><th>Тренировки</th></tr></thead>
        <tbody>
          {entries.map(([key, value]) => (
            <tr key={key}>
              <td>{labelFormatter(key)}</td>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditSection({ audit }: { audit: AuditLogDTO[] }) {
  /** Render organization-scoped audit events with readable payload summaries. */
  if (audit.length === 0) {
    return <EmptyState title="Событий аудита нет" />;
  }
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Аудит</h2></div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr><th>Время</th><th>Действие</th><th>Сущность</th><th>Автор</th><th>Детали</th></tr></thead>
          <tbody>
            {audit.map((event) => (
              <tr key={event.id}>
                <td>{formatDate(event.created_at)}</td>
                <td>{auditActionLabel(event.action)}</td>
                <td>{auditEntityLabel(event.entity_type)}</td>
                <td>{event.actor_user_id ? "Администратор" : "Система"}</td>
                <td>{auditPayloadSummary(event.payload)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
