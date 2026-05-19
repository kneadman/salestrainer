import type { AuthUser } from "../types";
import { PRODUCT_NAME } from "../branding";
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
  { label: "Настройки", path: "/app/settings" },
];

const LEAD_EXTRA_NAV = [
  { label: "Команда", path: "/app/team" },
  { label: "Аналитика команды", path: "/app/team-analytics" },
];

export function ClientLayout({ user, path, children, onNavigate, onLogout }: ClientLayoutProps) {
  /** Render the client cabinet shell with role-aware navigation. */
  // Balance section is temporarily hidden from navigation until billing/usage limits are product-ready.
  const nav = user.role === "client_lead"
    ? [...MANAGER_NAV.slice(0, 4), ...LEAD_EXTRA_NAV, ...MANAGER_NAV.slice(4)]
    : MANAGER_NAV;
  const isTrainerRoute = path.startsWith("/app/trainer");
  const shellClassName = isTrainerRoute ? "client-shell client-shell--trainer" : "client-shell";
  const contentClassName = isTrainerRoute ? "client-content client-content--trainer" : "client-content";
  return (
    <div className={shellClassName}>
      <aside className="client-sidebar">
        <BrandLogo className="client-brand" imageClassName="client-brand__mark" textClassName="client-brand__text" title={PRODUCT_NAME} subtitle={user.client_account.name} />
        <nav className="client-nav" aria-label="Навигация клиентского кабинета">
          {nav.map((item) => (
            <a
              key={item.path}
              href={item.path}
              className={path === item.path ? "client-nav__item client-nav__item--active" : "client-nav__item"}
              onClick={(event) => {
                if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return;
                event.preventDefault();
                onNavigate(item.path);
              }}
            >
              {item.label}
            </a>
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
