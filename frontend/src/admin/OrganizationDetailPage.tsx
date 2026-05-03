import { FormEvent, useEffect, useMemo, useState } from "react";
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
  api_key: string;
  folder_id: string;
  agent_id: string;
  base_url: string;
  model_or_agent_label: string;
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
  api_key: "",
  folder_id: "",
  agent_id: "",
  base_url: "",
  model_or_agent_label: "",
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
        throw new Error("Organization not found.");
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
        setSuccess("User updated.");
      } else {
        await createUser(organizationId, userForm);
        setSuccess("User created.");
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
    if (user.is_active && !window.confirm(`Disable user ${user.email}?`)) {
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
      setSuccess(user.is_active ? "User disabled." : "User enabled.");
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
    if (!password || !window.confirm(`Reset password for ${user.email}?`)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetUserPassword(user.id, password);
      setResetPasswordByUser({ ...resetPasswordByUser, [user.id]: "" });
      setSuccess("Password reset.");
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
        setSuccess("Training config updated.");
      } else {
        await createTrainingConfig(organizationId, configPayload());
        setSuccess("Training config created.");
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
    if (config.is_active && !window.confirm(`Disable training config ${config.name}?`)) {
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
      setSuccess(config.is_active ? "Training config disabled." : "Training config enabled.");
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
      folder_id: llmForm.folder_id || null,
      agent_id: llmForm.agent_id || null,
      base_url: llmForm.base_url || null,
      model_or_agent_label: llmForm.model_or_agent_label || null,
    };
    if (llmForm.api_key.trim()) {
      payload.api_key = llmForm.api_key;
    }
    try {
      if (llmForm.id) {
        await updateLLMProviderConfig(llmForm.id, payload);
        setSuccess("LLM provider config updated.");
      } else {
        await createLLMProviderConfig(organizationId, payload);
        setSuccess("LLM provider config created.");
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
    if (config.is_active && !window.confirm(`Disable LLM config ${config.name}?`)) {
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
      setSuccess(config.is_active ? "LLM config disabled." : "LLM config enabled.");
      await loadAll();
    } catch (toggleError) {
      setError(getErrorMessage(toggleError));
    } finally {
      setBusy(false);
    }
  };

  const handleAssignment = async (userId: string, configId: string, action: "assign" | "default" | "unassign") => {
    /** Run one training config assignment action for a user. */
    if (action === "unassign" && !window.confirm("Unassign this config from the user?")) {
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
      setSuccess("Assignment updated.");
      await loadAll();
    } catch (assignmentError) {
      setError(getErrorMessage(assignmentError));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <LoadingState title="Loading organization" />;
  }

  if (error && !organization) {
    return <ErrorState title="Organization unavailable" detail={error} />;
  }

  if (!organization) {
    return <EmptyState title="Organization not found" />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <button type="button" className="admin-link-button" onClick={() => onNavigate("/admin/organizations")}>
            ← Organizations
          </button>
          <h1>{organization.name}</h1>
          <p className="admin-muted">
            {organization.slug} · created {formatDate(organization.created_at)} · updated {formatDate(organization.updated_at)}
          </p>
        </div>
        <Badge tone={organization.is_active ? "good" : "danger"}>{statusLabel(organization.is_active)}</Badge>
      </div>
      {error ? <div className="admin-alert admin-alert--error">{error}</div> : null}
      {success ? <div className="admin-alert">{success}</div> : null}
      <div className="admin-tabs">
        {(["overview", "users", "configs", "llm", "history", "usage", "audit"] as DetailTab[]).map((tab) => (
          <button key={tab} type="button" className={activeTab === tab ? "admin-tab admin-tab--active" : "admin-tab"} onClick={() => setActiveTab(tab)}>
            {tab}
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
      <StatCard label="Users" value={organization.users_count} detail={`${organization.active_users_count} active`} />
      <StatCard label="Training configs" value={organization.training_configs_count} />
      <StatCard label="LLM configs" value={llmCount} />
      <StatCard label="Total sessions" value={usage?.total_sessions ?? "—"} />
      <StatCard label="Finished sessions" value={usage?.finished_sessions ?? "—"} />
      <StatCard label="Total turns" value={usage?.total_turns ?? "—"} />
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
      <div className="admin-panel__header"><h2>Users</h2></div>
      <form className="admin-form admin-form--inline" onSubmit={props.onSubmit}>
        <label>
          <span>Email</span>
          <input type="email" value={props.userForm.email} onChange={(event) => props.setUserForm({ ...props.userForm, email: event.target.value })} required />
        </label>
        {!props.editingUserId ? (
          <label>
            <span>Temporary password</span>
            <input type="password" minLength={8} value={props.userForm.password} onChange={(event) => props.setUserForm({ ...props.userForm, password: event.target.value })} required />
          </label>
        ) : null}
        <label>
          <span>Role</span>
          <select value={props.userForm.role} onChange={(event) => props.setUserForm({ ...props.userForm, role: event.target.value as UserForm["role"] })}>
            <option value="client_manager">client_manager</option>
            <option value="client_lead">client_lead</option>
          </select>
        </label>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.editingUserId ? "Update" : "Create"}</button>
      </form>
      {props.users.length === 0 ? <EmptyState title="No users" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Password</th><th>Assignments</th><th>Actions</th></tr></thead>
            <tbody>
              {props.users.map((user) => {
                const assignments = props.assignmentsByUser[user.id] ?? [];
                return (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td><Badge>{user.role}</Badge></td>
                    <td>
                      <Badge tone={user.is_active ? "good" : "danger"}>{statusLabel(user.is_active)}</Badge>
                      {user.must_change_password ? <Badge tone="warning">must change</Badge> : null}
                    </td>
                    <td>
                      <div className="admin-password-reset">
                        <input
                          type="password"
                          placeholder="New temporary password"
                          minLength={8}
                          value={props.resetPasswordByUser[user.id] ?? ""}
                          onChange={(event) => props.setResetPasswordByUser({ ...props.resetPasswordByUser, [user.id]: event.target.value })}
                        />
                        <button type="button" className="admin-link-button" onClick={() => props.onReset(user)}>Reset</button>
                      </div>
                    </td>
                    <td>
                      <div className="admin-assignment-list">
                        {props.configs.map((config) => {
                          const assigned = assignments.find((item) => item.training_config_id === config.id);
                          return (
                            <div key={config.id}>
                              <span>{config.name}</span>
                              {assigned?.is_default ? <Badge tone="good">default</Badge> : null}
                              <button type="button" className="admin-link-button" onClick={() => props.onAssignment(user.id, config.id, assigned ? "default" : "assign")}>
                                {assigned ? "Default" : "Assign"}
                              </button>
                              {assigned ? <button type="button" className="admin-link-button" onClick={() => props.onAssignment(user.id, config.id, "unassign")}>Remove</button> : null}
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
                        }}>Edit</button>
                        <button type="button" className="admin-link-button" onClick={() => props.onToggle(user)}>{user.is_active ? "Disable" : "Enable"}</button>
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
      <div className="admin-panel__header"><h2>Training Configs</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label><span>Name</span><input value={props.form.name} onChange={(event) => props.setForm({ ...props.form, name: event.target.value })} required /></label>
          <label><span>Scenario</span><select value={props.form.default_scenario_id} onChange={(event) => props.setForm({ ...props.form, default_scenario_id: event.target.value })}>{props.scenarioIds.map((id) => <option key={id} value={id}>{id}</option>)}</select></label>
          <label><span>Product line</span><select value={props.form.product_line} onChange={(event) => props.setForm({ ...props.form, product_line: event.target.value })}><option value="accounting_outsourcing">accounting_outsourcing</option><option value="outsourced_cfo">outsourced_cfo</option></select></label>
          <label><span>LLM provider</span><select value={props.form.llm_provider_config_id} onChange={(event) => props.setForm({ ...props.form, llm_provider_config_id: event.target.value })}><option value="">Global runtime / none</option>{props.llmConfigs.map((config) => <option key={config.id} value={config.id}>{config.name}</option>)}</select></label>
        </div>
        <div className="admin-json-grid">
          <label><span>persona_policy JSON</span><textarea value={props.form.persona_policy} onChange={(event) => props.setForm({ ...props.form, persona_policy: event.target.value })} /></label>
          <label><span>ui_config JSON</span><textarea value={props.form.ui_config} onChange={(event) => props.setForm({ ...props.form, ui_config: event.target.value })} /></label>
          <label><span>limits JSON</span><textarea value={props.form.limits} onChange={(event) => props.setForm({ ...props.form, limits: event.target.value })} /></label>
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.form.id ? "Update config" : "Create config"}</button>
      </form>
      {props.configs.length === 0 ? <EmptyState title="No training configs" /> : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead><tr><th>Name</th><th>Scenario</th><th>Product</th><th>Status</th><th>LLM</th><th>Actions</th></tr></thead>
            <tbody>
              {props.configs.map((config) => (
                <tr key={config.id}>
                  <td>{config.name}</td><td>{config.default_scenario_id}</td><td>{config.product_line}</td>
                  <td><Badge tone={config.is_active ? "good" : "danger"}>{statusLabel(config.is_active)}</Badge></td>
                  <td>{props.llmConfigs.find((item) => item.id === config.llm_provider_config_id)?.name ?? "—"}</td>
                  <td><div className="admin-row-actions">
                    <button type="button" className="admin-link-button" onClick={() => props.setForm({ id: config.id, name: config.name, default_scenario_id: config.default_scenario_id, product_line: config.product_line, persona_policy: stringifyJson(config.persona_policy), ui_config: stringifyJson(config.ui_config), limits: stringifyJson(config.limits), llm_provider_config_id: config.llm_provider_config_id ?? "" })}>Edit</button>
                    <button type="button" className="admin-link-button" onClick={() => props.onToggle(config)}>{config.is_active ? "Disable" : "Enable"}</button>
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
      <div className="admin-panel__header"><h2>LLM Settings</h2></div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <p className="admin-muted">New API key will be stored encrypted. The current key is never displayed in full.</p>
        <div className="admin-form-grid">
          <label><span>Name</span><input value={props.form.name} onChange={(event) => props.setForm({ ...props.form, name: event.target.value })} required /></label>
          <label><span>Provider</span><select value={props.form.provider} onChange={(event) => props.setForm({ ...props.form, provider: event.target.value as LLMForm["provider"] })}><option value="yandex_compatible">yandex_compatible</option><option value="openai_compatible">openai_compatible</option><option value="fake">fake</option></select></label>
          <label><span>API key</span><input type="password" value={props.form.api_key} onChange={(event) => props.setForm({ ...props.form, api_key: event.target.value })} /></label>
          <label><span>Folder ID</span><input value={props.form.folder_id} onChange={(event) => props.setForm({ ...props.form, folder_id: event.target.value })} /></label>
          <label><span>Agent ID</span><input value={props.form.agent_id} onChange={(event) => props.setForm({ ...props.form, agent_id: event.target.value })} /></label>
          <label><span>Base URL</span><input value={props.form.base_url} onChange={(event) => props.setForm({ ...props.form, base_url: event.target.value })} /></label>
          <label><span>Model/agent label</span><input value={props.form.model_or_agent_label} onChange={(event) => props.setForm({ ...props.form, model_or_agent_label: event.target.value })} /></label>
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>{props.form.id ? "Update LLM config" : "Create LLM config"}</button>
      </form>
      {props.configs.length === 0 ? <EmptyState title="No LLM provider configs" /> : (
        <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Name</th><th>Provider</th><th>Status</th><th>Key</th><th>Folder</th><th>Agent</th><th>Actions</th></tr></thead><tbody>{props.configs.map((config) => (
          <tr key={config.id}><td>{config.name}</td><td>{config.provider}</td><td><Badge tone={config.is_active ? "good" : "danger"}>{statusLabel(config.is_active)}</Badge></td><td>{config.has_api_key ? config.api_key_preview ?? "masked" : "none"}</td><td>{config.folder_id ?? "—"}</td><td>{config.agent_id ?? "—"}</td><td><div className="admin-row-actions"><button type="button" className="admin-link-button" onClick={() => props.setForm({ id: config.id, name: config.name, provider: config.provider === "openai_compatible" || config.provider === "fake" ? config.provider : "yandex_compatible", api_key: "", folder_id: config.folder_id ?? "", agent_id: config.agent_id ?? "", base_url: config.base_url ?? "", model_or_agent_label: config.model_or_agent_label ?? "" })}>Edit</button><button type="button" className="admin-link-button" onClick={() => props.onToggle(config)}>{config.is_active ? "Disable" : "Enable"}</button></div></td></tr>
        ))}</tbody></table></div>
      )}
    </section>
  );
}

function HistorySection({ history, onNavigate }: { history: HistorySessionSummaryDTO[]; onNavigate: (path: string) => void }) {
  /** Render persistent training history rows without hidden snapshots. */
  if (history.length === 0) {
    return <EmptyState title="No training history" detail="History appears for sessions created after Persistent Training History migration." />;
  }
  return <section className="admin-panel"><div className="admin-panel__header"><h2>Training History</h2></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Session</th><th>User</th><th>Status</th><th>Scenario</th><th>Turns</th><th>Interest</th><th>Started</th><th>Actions</th></tr></thead><tbody>{history.map((session) => <tr key={session.session_id}><td>{session.session_id.slice(0, 8)}</td><td>{session.user_email}</td><td><Badge>{session.status}</Badge></td><td>{session.scenario_id}</td><td>{session.turn_count}</td><td>{session.final_interest_score ?? "—"}</td><td>{formatDate(session.started_at)}</td><td><button type="button" className="admin-link-button" onClick={() => onNavigate(`/admin/history/sessions/${session.session_id}`)}>Open</button></td></tr>)}</tbody></table></div></section>;
}

function UsageSection({ usage }: { usage: UsageSummaryDTO | null }) {
  /** Render basic usage analytics from the persistent history summary endpoint. */
  if (!usage) {
    return <EmptyState title="Usage summary unavailable" detail="The backend returned no usage summary for this organization." />;
  }
  return <section className="admin-panel"><div className="admin-panel__header"><h2>Usage Analytics</h2></div><div className="admin-stats-grid"><StatCard label="Total sessions" value={usage.total_sessions} /><StatCard label="Finished" value={usage.finished_sessions} /><StatCard label="Active" value={usage.active_sessions} /><StatCard label="Unique users" value={usage.unique_users} /><StatCard label="Total turns" value={usage.total_turns} /><StatCard label="Avg interest" value={usage.avg_final_interest_score ?? "—"} /><StatCard label="Avg turns" value={usage.avg_turn_count ?? "—"} /><StatCard label="Usage events" value={usage.usage_events_count} /></div><pre className="admin-json-block">{compactJson({ sessions_by_status: usage.sessions_by_status, sessions_by_scenario: usage.sessions_by_scenario, sessions_by_training_config: usage.sessions_by_training_config })}</pre></section>;
}

function AuditSection({ audit }: { audit: AuditLogDTO[] }) {
  /** Render organization-scoped audit events with compact JSON payloads. */
  if (audit.length === 0) {
    return <EmptyState title="No audit events" />;
  }
  return <section className="admin-panel"><div className="admin-panel__header"><h2>Audit</h2></div><div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Time</th><th>Action</th><th>Entity</th><th>Actor</th><th>Payload</th></tr></thead><tbody>{audit.map((event) => <tr key={event.id}><td>{formatDate(event.created_at)}</td><td>{event.action}</td><td>{event.entity_type}</td><td>{event.actor_user_id ?? "system"}</td><td><pre className="admin-json-cell">{compactJson(event.payload)}</pre></td></tr>)}</tbody></table></div></section>;
}
