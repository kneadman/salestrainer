import type { AuthUser } from "../types";
import { PRODUCT_NAME } from "../branding";
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
  { label: "История тренировок", path: "/admin/history" },
  { label: "Аудит", path: "/admin/audit-log" },
];

function isActiveNavItem(activePath: string, itemPath: string): boolean {
  /** Keep parent admin sections highlighted on detail routes. */
  return itemPath === "/admin" ? activePath === itemPath : activePath === itemPath || activePath.startsWith(`${itemPath}/`);
}

export function AdminLayout({ user, activePath, children, onNavigate, onLogout }: AdminLayoutProps) {
  /** Render the protected internal admin shell with sidebar and topbar. */
  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <BrandLogo className="admin-sidebar__brand" imageClassName="admin-sidebar__brand-mark" textClassName="admin-sidebar__brand-text" title={PRODUCT_NAME} subtitle="Администрирование" />
        <nav className="admin-nav" aria-label="Навигация администратора">
          {NAV_ITEMS.map((item) => (
            <a
              key={`${item.label}-${item.path}`}
              href={item.path}
              className={isActiveNavItem(activePath, item.path) ? "admin-nav__item admin-nav__item--active" : "admin-nav__item"}
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
