import { FormEvent, useState } from "react";
import type { AuthUser } from "../types";
import { changePassword } from "./api";
import { ClientBadge, ClientState } from "./components/ClientPrimitives";
import { getClientErrorMessage } from "./utils";

type SettingsPageProps = {
  user: AuthUser;
  onUserUpdated: (user: AuthUser) => void;
};

export function SettingsPage({ user, onUserUpdated }: SettingsPageProps) {
  /** Render profile data and a safe password change form. */
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    /** Validate and submit password change without persisting password fields. */
    event.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword !== confirmPassword) {
      setError("Новый пароль и подтверждение не совпадают.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Новый пароль должен быть не короче 8 символов.");
      return;
    }
    if (!/^[a-zA-Z0-9]+$/.test(newPassword)) {
      setError("Новый пароль должен содержать только латинские буквы и цифры.");
      return;
    }
    if (newPassword === currentPassword) {
      setError("Новый пароль должен отличаться от текущего.");
      return;
    }
    setLoading(true);
    try {
      const response = await changePassword(currentPassword, newPassword);
      onUserUpdated(response.user);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess("Пароль изменен.");
    } catch (changeError) {
      setError(getClientErrorMessage(changeError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="client-page">
      <div className="client-page__header"><div><span className="client-kicker">Профиль</span><h1>Настройки</h1></div></div>
      <section className="client-panel">
        <dl className="client-profile-list">
          <div><dt>Email</dt><dd>{user.email}</dd></div>
          <div><dt>Role</dt><dd><ClientBadge>{user.role}</ClientBadge></dd></div>
          <div><dt>Organization</dt><dd>{user.client_account.name}</dd></div>
          <div><dt>Password status</dt><dd>{user.must_change_password ? <ClientBadge tone="warning">must change</ClientBadge> : <ClientBadge tone="good">ok</ClientBadge>}</dd></div>
        </dl>
      </section>
      <section className="client-panel">
        <h2>Сменить пароль</h2>
        {error ? <ClientState title="Ошибка" detail={error} tone="error" /> : null}
        {success ? <ClientState title={success} /> : null}
        <form className="client-form" onSubmit={submit}>
          <label><span>Текущий пароль</span><input type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required /></label>
          <label><span>Новый пароль</span><input type="password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
          <label><span>Подтверждение</span><input type="password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required /></label>
          <button type="submit" className="client-button client-button--primary" disabled={loading}>{loading ? "Сохраняю..." : "Изменить пароль"}</button>
        </form>
      </section>
    </div>
  );
}
