import { FormEvent, useState } from "react";
import { ApiError, login } from "../api";
import { PRODUCT_NAME } from "../branding";
import { BrandLogo } from "./BrandLogo";
import type { AuthUser } from "../types";

type LoginPageProps = {
  onAuthenticated: (user: AuthUser) => void;
};

function getLoginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Неверный email или пароль.";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неожиданная ошибка входа.";
}

export function LoginPage({ onAuthenticated }: LoginPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (loading) {
      return;
    }

    const submittedEmail = email.trim();
    const submittedPassword = password;
    setEmail("");
    setPassword("");
    setLoading(true);
    setError(null);

    try {
      const response = await login(submittedEmail, submittedPassword);
      onAuthenticated(response.user);
    } catch (loginError) {
      setError(getLoginErrorMessage(loginError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <BrandLogo title={PRODUCT_NAME} className="welcome-card__eyebrow" />
        <h1>Вход</h1>
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={loading}
            required
          />
        </label>
        <label className="field">
          <span>Пароль</span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={loading}
            required
          />
        </label>
        {error ? <div className="error-banner">{error}</div> : null}
        <button type="submit" className="primary-button primary-button--large" disabled={loading}>
          {loading ? "Входим..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
