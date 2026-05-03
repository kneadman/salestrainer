import type { AuthUser } from "../types";

type AdminLayoutProps = {
  user: AuthUser;
  activePath: string;
  children: React.ReactNode;
  onNavigate: (path: string, replace?: boolean) => void;
  onLogout: () => Promise<void>;
};

const NAV_ITEMS = [
  { label: "Dashboard", path: "/admin" },
  { label: "Organizations", path: "/admin/organizations" },
  { label: "Users / Team", path: "/admin/organizations" },
  { label: "Training Configs", path: "/admin/organizations" },
  { label: "LLM Settings", path: "/admin/organizations" },
  { label: "Training History", path: "/admin/history" },
  { label: "Usage Analytics", path: "/admin/organizations" },
  { label: "Audit Log", path: "/admin/audit-log" },
];

export function AdminLayout({ user, activePath, children, onNavigate, onLogout }: AdminLayoutProps) {
  /** Render the protected internal admin shell with sidebar and topbar. */
  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-sidebar__brand">
          <span>ST</span>
          <div>
            <strong>Platform Admin</strong>
            <small>Internal workspace</small>
          </div>
        </div>
        <nav className="admin-nav" aria-label="Admin navigation">
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
            <span>{user.role}</span>
          </div>
          <div className="admin-topbar__actions">
            <button type="button" className="admin-button admin-button--ghost" onClick={() => onNavigate("/app")}>
              Back to app
            </button>
            <button type="button" className="admin-button admin-button--ghost" onClick={() => onNavigate("/")}>
              Landing
            </button>
            <button type="button" className="admin-button" onClick={() => void onLogout()}>
              Logout
            </button>
          </div>
        </header>
        <main className="admin-content">{children}</main>
      </div>
    </div>
  );
}
