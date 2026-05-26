import { AdminDashboard } from "./AdminDashboard";
import { AdminLayout } from "./AdminLayout";
import { AuditLogPage } from "./AuditLogPage";
import { BlogPostsPage } from "./BlogPostsPage";
import { HistoryPage } from "./HistoryPage";
import { AdminUserAnalyticsPage } from "./UserAnalyticsPage";
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
          <p>Внутренний кабинет доступен только администратору платформы.</p>
          <div className="admin-actions">
            <a href="/app" className="admin-button admin-button--primary" onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate("/app", true); }}>
              Перейти в тренажер
            </a>
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
        <OrganizationDetailPage organizationId={route.organizationId} initialTab={route.tab} onNavigate={onNavigate} />
      ) : null}
      {route.route === "organization-user-analytics" && route.organizationId && route.userId ? (
        <AdminUserAnalyticsPage organizationId={route.organizationId} userId={route.userId} onNavigate={onNavigate} />
      ) : null}
      {route.route === "history" ? <HistoryPage onNavigate={onNavigate} /> : null}
      {route.route === "history-detail" ? <HistoryPage sessionId={route.sessionId} onNavigate={onNavigate} /> : null}
      {route.route === "audit-log" ? <AuditLogPage /> : null}
      {route.route === "blog" ? <BlogPostsPage onNavigate={onNavigate} /> : null}
    </AdminLayout>
  );
}
