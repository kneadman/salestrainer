import { FormEvent, useEffect, useState } from "react";
import { buildOrganizationViewModel } from "../viewModels";
import {
  createTrainingConfig,
  createUser,
  disableTrainingConfig,
  disableUser,
  enableTrainingConfig,
  enableUser,
  resetUserPassword,
  updateTrainingConfig,
  updateUser,
} from "./api";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import {
  DEFAULT_CONFIG_FORM,
  OrganizationAuditTab,
  OrganizationHistoryTab,
  OrganizationOverviewTab,
  OrganizationTrainingConfigsTab,
  OrganizationUsageTab,
  OrganizationUsersTab,
  useOrganizationDetail,
} from "./organizationDetail";
import type { OrganizationDetailTab, TrainingConfigDTO, UserDTO } from "./types";
import { getErrorMessage } from "./utils";

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
  seed_config: import("./types").SeedConfig | null;
  use_seed: boolean;
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
  const { organization, users, configs, history, usage, audit, loading, error, reload } =
    useOrganizationDetail(organizationId);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [userForm, setUserForm] = useState<UserForm>({
    email: "",
    password: "",
    role: "client_manager",
    default_training_config_id: null,
  });
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [resetPasswordByUser, setResetPasswordByUser] = useState<Record<string, string>>({});
  const [configForm, setConfigForm] = useState<ConfigForm>(DEFAULT_CONFIG_FORM);

  useEffect(() => {
    /** Sync requested tab from the route when organization detail opens or changes. */
    setActiveTab(initialTab ?? "overview");
  }, [organizationId, initialTab]);

  const withBusy = async <T,>(operation: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setActionError(null);
    setSuccess(null);
    try {
      const result = await operation();
      return result;
    } catch (err) {
      setActionError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const submitUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await withBusy(async () => {
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
      await reload();
    });
  };

  const toggleUser = async (user: UserDTO) => {
    if (user.is_active && !window.confirm(`Отключить пользователя ${user.email}?`)) {
      return;
    }
    await withBusy(async () => {
      if (user.is_active) {
        await disableUser(user.id);
      } else {
        await enableUser(user.id);
      }
      setSuccess(user.is_active ? "Пользователь отключён." : "Пользователь включён.");
      await reload();
    });
  };

  const resetPassword = async (user: UserDTO) => {
    const password = resetPasswordByUser[user.id] ?? "";
    if (!password || !window.confirm(`Сбросить пароль для ${user.email}?`)) {
      return;
    }
    await withBusy(async () => {
      await resetUserPassword(user.id, password);
      setResetPasswordByUser({ ...resetPasswordByUser, [user.id]: "" });
      setSuccess("Пароль сброшен.");
      await reload();
    });
  };

  const submitConfig = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await withBusy(async () => {
      const payload = configForm.use_seed
        ? {
            name: configForm.name,
            persona_generation_context: "",
            seed_config: configForm.seed_config,
          }
        : {
            name: configForm.name,
            persona_generation_context: configForm.persona_generation_context,
            seed_config: null,
          };
      if (configForm.id) {
        await updateTrainingConfig(configForm.id, payload);
        setSuccess("Настройка тренировки обновлена.");
      } else {
        await createTrainingConfig(organizationId, payload);
        setSuccess("Настройка тренировки создана.");
      }
      setConfigForm(DEFAULT_CONFIG_FORM);
      await reload();
    });
  };

  const toggleConfig = async (config: TrainingConfigDTO) => {
    if (config.is_active && !window.confirm(`Отключить настройку тренировки ${config.name}?`)) {
      return;
    }
    await withBusy(async () => {
      if (config.is_active) {
        await disableTrainingConfig(config.id);
      } else {
        await enableTrainingConfig(config.id);
      }
      setSuccess(config.is_active ? "Настройка тренировки отключена." : "Настройка тренировки включена.");
      await reload();
    });
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

  const vm = buildOrganizationViewModel(organization);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <a href="/admin/organizations" className="admin-link-button" onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate("/admin/organizations"); }}>
            ← Организации
          </a>
          <h1>{organization.name}</h1>
          <p className="admin-muted">
            {vm.slug} · создана {vm.createdAtLabel} · обновлена {vm.updatedAtLabel}
          </p>
        </div>
        <Badge tone={vm.statusTone}>{vm.statusLabel}</Badge>
      </div>
      {actionError ? <div className="admin-alert admin-alert--error">{actionError}</div> : null}
      {success ? <div className="admin-alert">{success}</div> : null}
      <div className="admin-tabs">
        {(["overview", "users", "configs", "history", "usage", "audit"] as OrganizationDetailTab[]).map((tab) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? "admin-tab admin-tab--active" : "admin-tab"}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>
      {activeTab === "overview" ? <OrganizationOverviewTab organization={organization} usage={usage} /> : null}
      {activeTab === "users" ? (
        <OrganizationUsersTab
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
        <OrganizationTrainingConfigsTab
          configs={configs}
          form={configForm}
          setForm={setConfigForm}
          busy={busy}
          onSubmit={submitConfig}
          onToggle={toggleConfig}
        />
      ) : null}
      {activeTab === "history" ? <OrganizationHistoryTab history={history} onNavigate={onNavigate} /> : null}
      {activeTab === "usage" ? <OrganizationUsageTab usage={usage} /> : null}
      {activeTab === "audit" ? <OrganizationAuditTab audit={audit} /> : null}
    </div>
  );
}
