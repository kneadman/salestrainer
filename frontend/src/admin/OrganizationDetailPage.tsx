import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  productLineLabel,
  providerLabel,
  roleLabel,
  scenarioLabel,
  statusLabel as entityStatusLabel,
} from "../labels";
import {
  assignTrainingConfig,
  createLLMProviderConfig,
  createTrainingConfig,
  createUser,
  disableLLMProviderConfig,
  disableTrainingConfig,
  disableUser,
  enableLLMProviderConfig,
  enableTrainingConfig,
  enableUser,
  getUsageSummary,
  listAuditLog,
  listLLMProviderConfigs,
  listOrganizationHistory,
  listOrganizations,
  listScenarios,
  listTrainingConfigs,
  listUserTrainingConfigs,
  listUsers,
  makeDefaultTrainingConfig,
  resetUserPassword,
  unassignTrainingConfig,
  updateLLMProviderConfig,
  updateTrainingConfig,
  updateUser,
} from "./api";
import { Badge, EmptyState, ErrorState, LoadingState, StatCard } from "./components/AdminPrimitives";
import type {
  AuditLogDTO,
  HistorySessionSummaryDTO,
  LLMProviderConfigDTO,
  LLMProviderConfigPayload,
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

type DetailTab = "overview" | "users" | "configs" | "llm" | "history" | "usage" | "audit";

type UserForm = {
  email: string;
  password: string;
  role: "client_lead" | "client_manager";
};

type ConfigForm = {
  id?: string;
  name: string;
  default_scenario_id: string;
  product_line: string;
  persona_policy: string;
  ui_config: string;
  limits: string;
  llm_provider_config_id: string;
};

type LLMForm = {
  id?: string;
  name: string;
  provider: "yandex_compatible" | "openai_compatible" | "fake";
  persona_api_key: string;
  persona_folder_id: string;
  persona_agent_id: string;
  persona_master_prompt: string;
  persona_json_template: string;
  dialogue_api_key: string;
  dialogue_folder_id: string;
  dialogue_agent_id: string;
  dialogue_master_prompt: string;
  dialogue_json_template: string;
};

const DEFAULT_CONFIG_FORM: ConfigForm = {
  name: "",
  default_scenario_id: "generic_b2b_first_contact",
  product_line: "accounting_outsourcing",
  persona_policy: "{}",
  ui_config: "{}",
  limits: "{}",
  llm_provider_config_id: "",
};

const DEFAULT_LLM_FORM: LLMForm = {
  name: "",
  provider: "yandex_compatible",
  persona_api_key: "",
  persona_folder_id: "",
  persona_agent_id: "",
  persona_master_prompt: "",
  persona_json_template: "",
  dialogue_api_key: "",
  dialogue_folder_id: "",
  dialogue_agent_id: "",
  dialogue_master_prompt: "",
  dialogue_json_template: "",
};

const TAB_LABELS: Record<DetailTab, string> = {
  overview: "Обзор",
  users: "Пользователи",
  configs: "Конфиги",
  llm: "LLM",
  history: "История",
  usage: "Использование",
  audit: "Аудит",
};

export function OrganizationDetailPage({ organizationId, onNavigate }: OrganizationDetailPageProps) {
  /** Render one organization workspace with users, configs, LLM, history, usage, and audit sections. */
  const [activeTab, setActiveTab] = useState<DetailTab>("overview");
  const [organization, setOrganization] = useState<OrganizationDTO | null>(null);
  const [users, setUsers] = useState<UserDTO[]>([]);
  const [configs, setConfigs] = useState<TrainingConfigDTO[]>([]);
  const [llmConfigs, setLlmConfigs] = useState<LLMProviderConfigDTO[]>([]);
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
  const [llmForm, setLlmForm] = useState<LLMForm>(DEFAULT_LLM_FORM);

  const scenarioIds = useMemo(() => {
    /** Prefer backend scenario options but keep known ids when the list endpoint is unavailable. */
    return scenarios.length > 0 ? scenarios.map((scenario) => scenario.scenario_id) : FALLBACK_SCENARIOS;
  }, [scenarios]);

  const loadAll = async () => {
    /** Load all organization detail data from available internal endpoints. */
    setLoading(true);
    setError(null);
    try {
      const orgs = await listOrganizations();
      const selectedOrg = orgs.find((item) => item.id === organizationId) ?? null;
      setOrganization(selectedOrg);
      if (!selectedOrg) {
        throw new Error("Организация не найдена.");
      }
      const [loadedUsers, loadedConfigs, loadedLlm, loadedHistory, loadedUsage, loadedAudit, loadedScenarios] = await Promise.all([
        listUsers(organizationId),
        listTrainingConfigs(organizationId),
        listLLMProviderConfigs(organizationId),
        listOrganizationHistory(organizationId, { limit: 50, offset: 0 }).catch(() => []),
        getUsageSummary(organizationId).catch(() => null),
        listAuditLog({ organization_id: organizationId, limit: 50, offset: 0 }).catch(() => []),
        listScenarios().catch(() => []),
      ]);
      setUsers(loadedUsers);
      setConfigs(loadedConfigs);
      setLlmConfigs(loadedLlm);
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
      product_line: configForm.product_line,
      persona_policy: parseJsonObject(configForm.persona_policy, "persona_policy"),
      ui_config: parseJsonObject(configForm.ui_config, "ui_config"),
      limits: parseJsonObject(configForm.limits, "limits"),
      llm_provider_config_id: configForm.llm_provider_config_id || null,
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

  const submitLlm = async (event: FormEvent<HTMLFormElement>) => {
    /** Create or update an LLM config without sending blank API keys on update. */
    event.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);
    const payload: LLMProviderConfigPayload = {
      name: llmForm.name,
      provider: llmForm.provider,
      persona_folder_id: llmForm.persona_folder_id || null,
      persona_agent_id: llmForm.persona_agent_id || null,
      persona_master_prompt: llmForm.persona_master_prompt || null,
      persona_json_template: llmForm.persona_json_template || null,
      dialogue_folder_id: llmForm.dialogue_folder_id || null,
      dialogue_agent_id: llmForm.dialogue_agent_id || null,
      dialogue_master_prompt: llmForm.dialogue_master_prompt || null,
      dialogue_json_template: llmForm.dialogue_json_template || null,
    };
    if (llmForm.persona_api_key.trim()) {
      payload.persona_api_key = llmForm.persona_api_key;
    }
    if (llmForm.dialogue_api_key.trim()) {
      payload.dialogue_api_key = llmForm.dialogue_api_key;
    }
    try {
      if (llmForm.id) {
        await updateLLMProviderConfig(llmForm.id, payload);
        setSuccess("LLM-настройки обновлены.");
      } else {
        await createLLMProviderConfig(organizationId, payload);
        setSuccess("LLM-настройки созданы.");
      }
      setLlmForm(DEFAULT_LLM_FORM);
      await loadAll();
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setBusy(false);
    }
  };

  const toggleLlm = async (config: LLMProviderConfigDTO) => {
    /** Enable or disable one LLM config after confirmation for disable. */
    if (config.is_active && !window.confirm(`Отключить LLM-настройки ${config.name}?`)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (config.is_active) {
        await disableLLMProviderConfig(config.id);
      } else {
        await enableLLMProviderConfig(config.id);
      }
      setSuccess(config.is_active ? "LLM-настройки отключены." : "LLM-настройки включены.");
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
        {(["overview", "users", "configs", "llm", "history", "usage", "audit"] as DetailTab[]).map((tab) => (
          <button key={tab} type="button" className={activeTab === tab ? "admin-tab admin-tab--active" : "admin-tab"} onClick={() => setActiveTab(tab)}>
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      {activeTab === "overview" ? (
        <OverviewSection organization={organization} llmCount={llmConfigs.length} usage={usage} />
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
          llmConfigs={llmConfigs}
          scenarioIds={scenarioIds}
          form={configForm}
          setForm={setConfigForm}
          busy={busy}
          onSubmit={submitConfig}
          onToggle={toggleConfig}
        />
      ) : null}
      {activeTab === "llm" ? (
        <LLMSection configs={llmConfigs} form={llmForm} setForm={setLlmForm} busy={busy} onSubmit={submitLlm} onToggle={toggleLlm} />
      ) : null}
      {activeTab === "history" ? <HistorySection history={history} onNavigate={onNavigate} /> : null}
      {activeTab === "usage" ? <UsageSection usage={usage} /> : null}
      {activeTab === "audit" ? <AuditSection audit={audit} /> : null}
    </div>
  );
}

function OverviewSection({ organization, llmCount, usage }: { organization: OrganizationDTO; llmCount: number; usage: UsageSummaryDTO | null }) {
  /** Render organization summary cards and usage teaser. */
  return (
    <section className="admin-stats-grid">
      <StatCard label="Пользователи" value={organization.users_count} detail={`${organization.active_users_count} активны`} />
      <StatCard label="Тренировочные конфиги" value={organization.training_configs_count} />
      <StatCard label="LLM-настройки" value={llmCount} />
      <StatCard label="Всего сессий" value={usage?.total_sessions ?? "—"} />
      <StatCard label="Завершено сессий" value={usage?.finished_sessions ?? "—"} />
      <StatCard label="Всего сообщений" value={usage?.total_turns ?? "—"} />
    </section>
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
  /** Render user management and per-user training config assignment controls. */
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Пользователи</h2></div>
      <form className="admin-form admin-form--inline" onSubmit={props.onSubmit}>
        <label>
          <span>Email</span>
          <input type="email" value={props.userForm.email} onChange={(event) => props.setUserForm({ ...props.userForm, email: event.target.value })} required />
        </label>
        {!props.editingUserId ? (
          <label>
            <span>Временный пароль</span>
            <input type="password" minLength={8} value={props.userForm.password} onChange={(event) => props.setUserForm({ ...props.userForm, password: event.target.value })} required />
          </label>
        ) : null}
        <label>
          <span>Роль</span>
          <select value={props.userForm.role} onChange={(event) => props.setUserForm({ ...props.userForm, role: event.target.value as UserForm["role"] })}>
            <option value="client_manager">Менеджер</option>
            <option value="client_lead">Руководитель</option>
          </select>
        </label>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.editingUserId ? "Обновить" : "Создать"}</button>
      </form>
      {props.users.length === 0 ? <EmptyState title="Пользователей нет" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Email</th><th>Роль</th><th>Статус</th><th>Пароль</th><th>Назначения</th><th>Действия</th></tr></thead>
            <tbody>
              {props.users.map((user) => {
                const assignments = props.assignmentsByUser[user.id] ?? [];
                return (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td><Badge>{roleLabel(user.role)}</Badge></td>
                    <td>
                      <Badge tone={user.is_active ? "good" : "danger"}>{statusLabel(user.is_active)}</Badge>
                      {user.must_change_password ? <Badge tone="warning">сменить пароль</Badge> : null}
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
  llmConfigs: LLMProviderConfigDTO[];
  scenarioIds: string[];
  form: ConfigForm;
  setForm: (form: ConfigForm) => void;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (config: TrainingConfigDTO) => void;
}) {
  /** Render training config form, JSON fields, and config list. */
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>Тренировочные конфиги</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label><span>Название</span><input value={props.form.name} onChange={(event) => props.setForm({ ...props.form, name: event.target.value })} required /></label>
          <label><span>Сценарий</span><select value={props.form.default_scenario_id} onChange={(event) => props.setForm({ ...props.form, default_scenario_id: event.target.value })}>{props.scenarioIds.map((id) => <option key={id} value={id}>{scenarioLabel(id)}</option>)}</select></label>
          <label><span>Продукт</span><select value={props.form.product_line} onChange={(event) => props.setForm({ ...props.form, product_line: event.target.value })}><option value="accounting_outsourcing">Бухгалтерский аутсорсинг</option><option value="outsourced_cfo">Финансовый директор на аутсорсинге</option></select></label>
          <label><span>LLM-настройки</span><select value={props.form.llm_provider_config_id} onChange={(event) => props.setForm({ ...props.form, llm_provider_config_id: event.target.value })}><option value="">Глобальная runtime-модель / не выбрано</option>{props.llmConfigs.map((config) => <option key={config.id} value={config.id}>{config.name}</option>)}</select></label>
        </div>
        <div className="admin-json-grid">
          <label><span>Политика персоны JSON</span><textarea value={props.form.persona_policy} onChange={(event) => props.setForm({ ...props.form, persona_policy: event.target.value })} /></label>
          <label><span>UI-конфиг JSON</span><textarea value={props.form.ui_config} onChange={(event) => props.setForm({ ...props.form, ui_config: event.target.value })} /></label>
          <label><span>Лимиты JSON</span><textarea value={props.form.limits} onChange={(event) => props.setForm({ ...props.form, limits: event.target.value })} /></label>
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.form.id ? "Обновить конфиг" : "Создать конфиг"}</button>
      </form>
      {props.configs.length === 0 ? <EmptyState title="Тренировочных конфигов нет" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Название</th><th>Сценарий</th><th>Продукт</th><th>Статус</th><th>LLM</th><th>Действия</th></tr></thead>
            <tbody>
              {props.configs.map((config) => (
                <tr key={config.id}>
                  <td>{config.name}</td><td>{scenarioLabel(config.default_scenario_id)}</td><td>{productLineLabel(config.product_line)}</td>
                  <td><Badge tone={config.is_active ? "good" : "danger"}>{statusLabel(config.is_active)}</Badge></td>
                  <td>{props.llmConfigs.find((item) => item.id === config.llm_provider_config_id)?.name ?? "—"}</td>
                  <td><div className="admin-row-actions">
                    <button type="button" className="admin-link-button" onClick={() => props.setForm({ id: config.id, name: config.name, default_scenario_id: config.default_scenario_id, product_line: config.product_line, persona_policy: stringifyJson(config.persona_policy), ui_config: stringifyJson(config.ui_config), limits: stringifyJson(config.limits), llm_provider_config_id: config.llm_provider_config_id ?? "" })}>Изменить</button>
                    <button type="button" className="admin-link-button" onClick={() => props.onToggle(config)}>{config.is_active ? "Отключить" : "Включить"}</button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function LLMSection(props: {
  configs: LLMProviderConfigDTO[];
  form: LLMForm;
  setForm: (form: LLMForm) => void;
  busy: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onToggle: (config: LLMProviderConfigDTO) => void;
}) {
  /** Render LLM provider config form and secret-safe config list. */
  return (
    <section className="admin-panel">
      <div className="admin-panel__header"><h2>LLM-настройки</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <p className="admin-muted">Base URL Yandex задается глобально и одинаков для всех клиентов.</p>
        <p className="admin-muted">Пустое поле API key при сохранении не меняет текущий ключ.</p>
        <p className="admin-muted">Ключ хранится зашифрованно и полностью не отображается.</p>
        <div className="admin-form-grid">
          <label><span>Название</span><input value={props.form.name} onChange={(event) => props.setForm({ ...props.form, name: event.target.value })} required /></label>
          <label><span>Провайдер</span><select value={props.form.provider} onChange={(event) => props.setForm({ ...props.form, provider: event.target.value as LLMForm["provider"] })}><option value="yandex_compatible">Yandex AI Studio</option><option value="openai_compatible">OpenAI-compatible</option><option value="fake">Локальная тестовая модель</option></select></label>
        </div>
        <div className="admin-json-grid">
          <fieldset className="admin-fieldset">
            <legend>Генерация личности</legend>
            <label><span>API key</span><input type="password" value={props.form.persona_api_key} onChange={(event) => props.setForm({ ...props.form, persona_api_key: event.target.value })} /></label>
            <label><span>Agent ID</span><input value={props.form.persona_agent_id} onChange={(event) => props.setForm({ ...props.form, persona_agent_id: event.target.value })} /></label>
            <label><span>Folder ID</span><input value={props.form.persona_folder_id} onChange={(event) => props.setForm({ ...props.form, persona_folder_id: event.target.value })} /></label>
            <label><span>Master prompt</span><textarea value={props.form.persona_master_prompt} onChange={(event) => props.setForm({ ...props.form, persona_master_prompt: event.target.value })} /></label>
            <label><span>JSON template</span><textarea value={props.form.persona_json_template} onChange={(event) => props.setForm({ ...props.form, persona_json_template: event.target.value })} /></label>
          </fieldset>
          <fieldset className="admin-fieldset">
            <legend>Диалоговая модель</legend>
            <label><span>API key</span><input type="password" value={props.form.dialogue_api_key} onChange={(event) => props.setForm({ ...props.form, dialogue_api_key: event.target.value })} /></label>
            <label><span>Agent ID</span><input value={props.form.dialogue_agent_id} onChange={(event) => props.setForm({ ...props.form, dialogue_agent_id: event.target.value })} /></label>
            <label><span>Folder ID</span><input value={props.form.dialogue_folder_id} onChange={(event) => props.setForm({ ...props.form, dialogue_folder_id: event.target.value })} /></label>
            <label><span>Master prompt</span><textarea value={props.form.dialogue_master_prompt} onChange={(event) => props.setForm({ ...props.form, dialogue_master_prompt: event.target.value })} /></label>
            <label><span>JSON template</span><textarea value={props.form.dialogue_json_template} onChange={(event) => props.setForm({ ...props.form, dialogue_json_template: event.target.value })} /></label>
          </fieldset>
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.form.id ? "Сохранить LLM-настройки" : "Создать LLM-настройки"}</button>
      </form>
      {props.configs.length === 0 ? <EmptyState title="LLM-настройки не созданы" /> : (
        <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Название</th><th>Провайдер</th><th>Статус</th><th>Генерация личности</th><th>Диалоговая модель</th><th>Действия</th></tr></thead><tbody>{props.configs.map((config) => (
          <tr key={config.id}><td>{config.name}</td><td>{providerLabel(config.provider)}</td><td><Badge tone={config.is_active ? "good" : "danger"}>{statusLabel(config.is_active)}</Badge></td><td>{config.has_persona_api_key ? config.persona_api_key_preview ?? "ключ скрыт" : "не настроено"}<br />{config.persona_folder_id ?? "Folder ID не настроен"}<br />{config.persona_agent_id ?? "Agent ID не настроен"}</td><td>{config.has_dialogue_api_key ? config.dialogue_api_key_preview ?? "ключ скрыт" : "не настроено"}<br />{config.dialogue_folder_id ?? "Folder ID не настроен"}<br />{config.dialogue_agent_id ?? "Agent ID не настроен"}</td><td><div className="admin-row-actions"><button type="button" className="admin-link-button" onClick={() => props.setForm({ id: config.id, name: config.name, provider: config.provider === "openai_compatible" || config.provider === "fake" ? config.provider : "yandex_compatible", persona_api_key: "", persona_folder_id: config.persona_folder_id ?? "", persona_agent_id: config.persona_agent_id ?? "", persona_master_prompt: config.persona_master_prompt ?? "", persona_json_template: config.persona_json_template ?? "", dialogue_api_key: "", dialogue_folder_id: config.dialogue_folder_id ?? "", dialogue_agent_id: config.dialogue_agent_id ?? "", dialogue_master_prompt: config.dialogue_master_prompt ?? "", dialogue_json_template: config.dialogue_json_template ?? "" })}>Изменить</button><button type="button" className="admin-link-button" onClick={() => props.onToggle(config)}>{config.is_active ? "Отключить" : "Включить"}</button></div></td></tr>
        ))}</tbody></table></div>
      )}
    </section>
  );
}

function HistorySection({ history, onNavigate }: { history: HistorySessionSummaryDTO[]; onNavigate: (path: string) => void }) {
  /** Render persistent training history rows without hidden snapshots. */
  if (history.length === 0) {
    return <EmptyState title="История тренировок пуста" detail="История появится после первых сохраненных тренировок." />;
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
