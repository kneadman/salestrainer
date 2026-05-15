import { FormEvent } from "react";
import { buildUserViewModel } from "../../viewModels";
import { Badge, EmptyState } from "../components/AdminPrimitives";
import type { TrainingConfigDTO, UserDTO } from "../types";

export type UserForm = {
  email: string;
  password: string;
  role: "client_lead" | "client_manager";
  default_training_config_id: string | null;
};

export function OrganizationUsersTab(props: {
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
  const userVms = props.users.map((u) => buildUserViewModel(u, props.configs));
  return (
    <section className="admin-panel">
      <div className="admin-panel__header">
        <h2>Пользователи</h2>
      </div>
      <form className="admin-form admin-form--stacked" onSubmit={props.onSubmit}>
        <div className="admin-form-grid">
          <label>
            <span>Email</span>
            <input
              type="email"
              value={props.userForm.email}
              onChange={(event) => props.setUserForm({ ...props.userForm, email: event.target.value })}
              required
            />
          </label>
          <label>
            <span>Пароль</span>
            <input
              type="password"
              minLength={8}
              value={props.userForm.password}
              onChange={(event) => props.setUserForm({ ...props.userForm, password: event.target.value })}
              required={!props.editingUserId}
            />
          </label>
          <label>
            <span>Роль</span>
            <select
              value={props.userForm.role}
              onChange={(event) => props.setUserForm({ ...props.userForm, role: event.target.value as UserForm["role"] })}
            >
              <option value="client_manager">Менеджер</option>
              <option value="client_lead">Руководитель</option>
            </select>
          </label>
          {props.editingUserId ? (
            <label>
              <span>Конфиг по умолчанию</span>
              <select
                value={props.userForm.default_training_config_id ?? ""}
                onChange={(event) =>
                  props.setUserForm({ ...props.userForm, default_training_config_id: event.target.value || null })
                }
              >
                <option value="">— Не выбран —</option>
                {activeConfigs.map((config) => (
                  <option key={config.id} value={config.id}>
                    {config.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        <button type="submit" className="admin-button admin-button--primary" disabled={props.busy}>
          {props.editingUserId ? "Обновить пользователя" : "Создать пользователя"}
        </button>
      </form>
      {props.users.length === 0 ? (
        <EmptyState title="Пользователей нет" />
      ) : (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Роль</th>
                <th>Статус</th>
                <th>Конфиг по умолчанию</th>
                <th>Пароль</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {userVms.map((vm, index) => {
                const user = props.users[index];
                return (
                  <tr key={vm.id}>
                    <td>{vm.email}</td>
                    <td>{vm.roleLabel}</td>
                    <td>
                      <Badge tone={vm.statusTone}>{vm.statusLabel}</Badge>
                    </td>
                    <td>{vm.defaultTrainingConfigName ?? "—"}</td>
                    <td>
                      <div className="admin-password-reset">
                        <input
                          type="password"
                          placeholder="Новый временный пароль"
                          minLength={8}
                          value={props.resetPasswordByUser[user.id] ?? ""}
                          onChange={(event) =>
                            props.setResetPasswordByUser({ ...props.resetPasswordByUser, [user.id]: event.target.value })
                          }
                        />
                        <button type="button" className="admin-link-button" onClick={() => props.onReset(user)}>
                          Сбросить
                        </button>
                      </div>
                    </td>
                    <td>
                      <div className="admin-row-actions">
                        <button
                          type="button"
                          className="admin-link-button"
                          onClick={() => props.onOpenAnalytics(user.id)}
                        >
                          Аналитика
                        </button>
                        <button
                          type="button"
                          className="admin-link-button"
                          onClick={() => {
                            props.setEditingUserId(user.id);
                            props.setUserForm({
                              email: user.email,
                              password: "",
                              role: user.role === "client_lead" ? "client_lead" : "client_manager",
                              default_training_config_id: user.default_training_config_id ?? null,
                            });
                          }}
                        >
                          Изменить
                        </button>
                        <button
                          type="button"
                          className="admin-link-button"
                          onClick={() => props.onToggle(user)}
                        >
                          {user.is_active ? "Отключить" : "Включить"}
                        </button>
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
