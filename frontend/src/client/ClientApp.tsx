import type { AuthUser } from "../types";
import { AnalyticsPage } from "./AnalyticsPage";
import { BalancePage } from "./BalancePage";
import { ClientLayout } from "./ClientLayout";
import { DashboardPage } from "./DashboardPage";
import { HistoryPage } from "./HistoryPage";
import { SettingsPage } from "./SettingsPage";
import { TeamAnalyticsPage } from "./TeamAnalyticsPage";
import { TeamPage } from "./TeamPage";
import { TrainerPage } from "./TrainerPage";
import { ClientState } from "./components/ClientPrimitives";
import { parseClientPath } from "./utils";

type ClientAppProps = {
  user: AuthUser;
  path: string;
  onNavigate: (path: string, replace?: boolean) => void;
  onLogout: () => Promise<void>;
  onUserUpdated: (user: AuthUser) => void;
};

export function ClientApp({ user, path, onNavigate, onLogout, onUserUpdated }: ClientAppProps) {
  /** Route the client cabinet and enforce client role visibility. */
  const route = parseClientPath(path);
  const isLeadOnlyRoute = route.route === "team" || route.route === "team-detail" || route.route === "team-analytics";
  if (isLeadOnlyRoute && user.role !== "client_lead") {
    return (
      <ClientLayout user={user} path={path} onNavigate={onNavigate} onLogout={onLogout}>
        <ClientState title="Нет доступа" detail="Командные разделы доступны только роли client_lead." tone="error" />
      </ClientLayout>
    );
  }
  return (
    <ClientLayout user={user} path={path} onNavigate={onNavigate} onLogout={onLogout}>
      {route.route === "dashboard" ? <DashboardPage user={user} onNavigate={onNavigate} /> : null}
      {route.route === "trainer" ? <TrainerPage onLogout={onLogout} /> : null}
      {route.route === "history" ? <HistoryPage onNavigate={onNavigate} /> : null}
      {route.route === "history-detail" ? <HistoryPage sessionId={route.sessionId} onNavigate={onNavigate} /> : null}
      {route.route === "analytics" ? <AnalyticsPage /> : null}
      {route.route === "team" ? <TeamPage onNavigate={onNavigate} /> : null}
      {route.route === "team-detail" ? <TeamPage userId={route.userId} onNavigate={onNavigate} /> : null}
      {route.route === "team-analytics" ? <TeamAnalyticsPage /> : null}
      {route.route === "balance" ? <BalancePage user={user} /> : null}
      {route.route === "settings" ? <SettingsPage user={user} onUserUpdated={onUserUpdated} /> : null}
    </ClientLayout>
  );
}
