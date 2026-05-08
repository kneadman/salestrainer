import type { AuthUser } from "../types";
import { roleLabel } from "../labels";
import { BrandLogo } from "../components/BrandLogo";
import { ClientBadge } from "./components/ClientPrimitives";

type ClientLayoutProps = {
  user: AuthUser;
  path: string;
  children: React.ReactNode;
  onNavigate: (path: string, replace?: boolean) => void;
  onLogout: () => Promise<void>;
};

const MANAGER_NAV = [
  { label: "Обзор", path: "/app" },
  { label: "Тренажер", path: "/app/trainer" },
  { label: "История", path: "/app/history" },
  { label: "Моя аналитика", path: "/app/analytics" },
  { label: "Баланс", path: "/app/balance" },
  { label: "Настройки", path: "/app/settings" },
];

const LEAD_EXTRA_NAV = [
  { label: "Команда", path: "/app/team" },
  { label: "Аналитика команды", path: "/app/team-analytics" },
];

export function ClientLayout({ user, path, children, onNavigate, onLogout }: ClientLayoutProps) {
  /** Render the client cabinet shell with role-aware navigation. */
  const nav = user.role === "client_lead"
    ? [...MANAGER_NAV.slice(0, 4), ...LEAD_EXTRA_NAV, ...MANAGER_NAV.slice(4)]
    : MANAGER_NAV;
  const contentClassName = path.startsWith("/app/trainer") ? "client-content client-content--trainer" : "client-content";
  return (
    <div className="client-shell">
      <aside className="client-sidebar">
        <BrandLogo className="client-brand" imageClassName="client-brand__mark" textClassName="client-brand__text" title="Replikor" subtitle={user.client_account.name} />
        <nav className="client-nav" aria-label="Навигация клиентского кабинета">
          {nav.map((item) => (
            <button
              key={item.path}
              type="button"
              className={path === item.path ? "client-nav__item client-nav__item--active" : "client-nav__item"}
              onClick={() => onNavigate(item.path)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="client-main-shell">
        <header className="client-topbar">
          <div>
            <strong>{user.email}</strong>
            <span>{user.client_account.name}</span>
          </div>
          <div className="client-topbar__actions">
            <ClientBadge tone={user.role === "client_lead" ? "good" : "neutral"}>{roleLabel(user.role)}</ClientBadge>
            {user.must_change_password ? <ClientBadge tone="warning">Нужно сменить пароль</ClientBadge> : null}
            <button type="button" className="client-button" onClick={() => void onLogout()}>Выйти</button>
          </div>
        </header>
        <main className={contentClassName}>{children}</main>
      </div>
    </div>
  );
}
