import type { AuthUser } from "../types";
import { roleLabel } from "../labels";
import { BrandLogo } from "../components/BrandLogo";

type AdminLayoutProps = {
  user: AuthUser;
  activePath: string;
  children: React.ReactNode;
  onNavigate: (path: string, replace?: boolean) => void;
  onLogout: () => Promise<void>;
};

const NAV_ITEMS = [
  { label: "Обзор", path: "/admin" },
  { label: "Организации", path: "/admin/organizations" },
  { label: "Пользователи", path: "/admin/organizations" },
  { label: "Тренировочные конфиги", path: "/admin/organizations" },
  { label: "История тренировок", path: "/admin/history" },
  { label: "Аналитика", path: "/admin/organizations" },
  { label: "Аудит", path: "/admin/audit-log" },
];

export function AdminLayout({ user, activePath, children, onNavigate, onLogout }: AdminLayoutProps) {
  /** Render the protected internal admin shell with sidebar and topbar. */
  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <BrandLogo className="admin-sidebar__brand" imageClassName="admin-sidebar__brand-mark" textClassName="admin-sidebar__brand-text" title="Replikor" subtitle="Internal admin" />
        <nav className="admin-nav" aria-label="Навигация администратора">
          {NAV_ITEMS.map((item) => (
            <button
              key={`${item.label}-${item.path}`}
              type="button"
              className={activePath === item.path ? "admin-nav__item admin-nav__item--active" : "admin-nav__item"}
              onClick={() => onNavigate(item.path)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="admin-main-shell">
        <header className="admin-topbar">
          <div>
            <strong>{user.email}</strong>
            <span>{roleLabel(user.role)}</span>
          </div>
          <div className="admin-topbar__actions">
            <button type="button" className="admin-button admin-button--ghost" onClick={() => onNavigate("/app")}>
              В кабинет
            </button>
            <button type="button" className="admin-button admin-button--ghost" onClick={() => onNavigate("/")}>
              Лендинг
            </button>
            <button type="button" className="admin-button" onClick={() => void onLogout()}>
              Выйти
            </button>
          </div>
        </header>
        <main className="admin-content">{children}</main>
      </div>
    </div>
  );
}
