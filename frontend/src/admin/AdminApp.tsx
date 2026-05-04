import { AdminDashboard } from "./AdminDashboard";
import { AdminLayout } from "./AdminLayout";
import { AuditLogPage } from "./AuditLogPage";
import { HistoryPage } from "./HistoryPage";
import { OrganizationDetailPage } from "./OrganizationDetailPage";
import { OrganizationsPage } from "./OrganizationsPage";
import type { AdminAppProps } from "./types";
import { parseAdminPath } from "./utils";

export function AdminApp({ user, path, onNavigate, onLogout }: AdminAppProps) {
  /** Gate and route the internal admin UI for platform owners only. */
  const route = parseAdminPath(path);

  if (user.role !== "internal_admin") {
    return (
      <div className="admin-denied">
        <section className="admin-panel admin-denied__card">
          <span className="admin-kicker">Нет доступа</span>
          <h1>Нет доступа</h1>
          <p>Внутренний кабинет доступен только владельцу платформы с ролью internal_admin.</p>
          <div className="admin-actions">
            <button type="button" className="admin-button admin-button--primary" onClick={() => onNavigate("/app", true)}>
              Перейти в тренажер
            </button>
            <button type="button" className="admin-button" onClick={() => void onLogout()}>
              Выйти
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <AdminLayout user={user} activePath={path} onNavigate={onNavigate} onLogout={onLogout}>
      {route.route === "dashboard" ? <AdminDashboard onNavigate={onNavigate} /> : null}
      {route.route === "organizations" ? <OrganizationsPage onNavigate={onNavigate} /> : null}
      {route.route === "organization-detail" && route.organizationId ? (
        <OrganizationDetailPage organizationId={route.organizationId} onNavigate={onNavigate} />
      ) : null}
      {route.route === "history" ? <HistoryPage onNavigate={onNavigate} /> : null}
      {route.route === "history-detail" ? <HistoryPage sessionId={route.sessionId} onNavigate={onNavigate} /> : null}
      {route.route === "audit-log" ? <AuditLogPage /> : null}
    </AdminLayout>
  );
}
