import { useEffect, useMemo, useState } from "react";
import { listAuditLog, listLLMProviderConfigs, listOrganizations, getUsageSummary } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState, StatCard } from "./components/AdminPrimitives";
import type { AuditLogDTO, OrganizationDTO, UsageSummaryDTO } from "./types";
import { formatDate, getErrorMessage } from "./utils";

type AdminDashboardProps = {
  onNavigate: (path: string) => void;
};

export function AdminDashboard({ onNavigate }: AdminDashboardProps) {
  /** Load and render platform-level admin overview from available internal APIs. */
  const [organizations, setOrganizations] = useState<OrganizationDTO[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLogDTO[]>([]);
  const [usageSummaries, setUsageSummaries] = useState<UsageSummaryDTO[]>([]);
  const [llmCount, setLlmCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Bootstrap dashboard metrics from organization, usage, LLM, and audit endpoints. */
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const orgs = await listOrganizations();
        setOrganizations(orgs);
        const [audit, llmGroups, usageGroups] = await Promise.all([
          listAuditLog({ limit: 5, offset: 0 }),
          Promise.all(orgs.map((org) => listLLMProviderConfigs(org.id).catch(() => []))),
          Promise.all(orgs.map((org) => getUsageSummary(org.id).catch(() => null))),
        ]);
        setAuditLog(audit);
        setLlmCount(llmGroups.reduce((count, group) => count + group.length, 0));
        setUsageSummaries(usageGroups.filter((summary): summary is UsageSummaryDTO => summary !== null));
      } catch (loadError) {
        setError(getErrorMessage(loadError));
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const totals = useMemo(() => {
    /** Aggregate organization and usage totals for dashboard cards. */
    const totalSessions = usageSummaries.reduce((sum, item) => sum + item.total_sessions, 0);
    const finishedSessions = usageSummaries.reduce((sum, item) => sum + item.finished_sessions, 0);
    const totalTurns = usageSummaries.reduce((sum, item) => sum + item.total_turns, 0);
    const interestValues = usageSummaries
      .map((item) => item.avg_final_interest_score)
      .filter((value): value is number => value !== null);
    const avgInterest =
      interestValues.length > 0
        ? Math.round(interestValues.reduce((sum, value) => sum + value, 0) / interestValues.length)
        : null;
    return {
      organizations: organizations.length,
      activeOrganizations: organizations.filter((org) => org.is_active).length,
      users: organizations.reduce((sum, org) => sum + org.users_count, 0),
      trainingConfigs: organizations.reduce((sum, org) => sum + org.training_configs_count, 0),
      totalSessions,
      finishedSessions,
      totalTurns,
      avgInterest,
    };
  }, [organizations, usageSummaries]);

  if (loading) {
    return <LoadingState title="Loading dashboard" detail="Fetching organizations, audit log, and usage summaries." />;
  }

  if (error) {
    return <ErrorState title="Dashboard unavailable" detail={error} />;
  }

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <span className="admin-kicker">Internal admin</span>
          <h1>Dashboard</h1>
        </div>
        <div className="admin-actions">
          <button type="button" className="admin-button admin-button--primary" onClick={() => onNavigate("/admin/organizations")}>
            Create organization
          </button>
          <button type="button" className="admin-button" onClick={() => onNavigate("/admin/audit-log")}>
            Audit log
          </button>
        </div>
      </div>
      <section className="admin-stats-grid">
        <StatCard label="Organizations" value={totals.organizations} detail={`${totals.activeOrganizations} active`} />
        <StatCard label="Users" value={totals.users} detail="Across all organizations" />
        <StatCard label="Training configs" value={totals.trainingConfigs} />
        <StatCard label="LLM provider configs" value={llmCount} />
        <StatCard label="Total sessions" value={totals.totalSessions} detail={`${totals.finishedSessions} finished`} />
        <StatCard label="Total turns" value={totals.totalTurns} />
        <StatCard label="Avg final interest" value={totals.avgInterest ?? "—"} detail="Across organizations with data" />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header">
          <h2>Latest audit events</h2>
          <button type="button" className="admin-link-button" onClick={() => onNavigate("/admin/audit-log")}>
            Open all
          </button>
        </div>
        {auditLog.length === 0 ? (
          <EmptyState title="No audit events" detail="Audit records will appear after internal admin mutations." />
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Actor</th>
                </tr>
              </thead>
              <tbody>
                {auditLog.map((event) => (
                  <tr key={event.id}>
                    <td>{formatDate(event.created_at)}</td>
                    <td><Badge>{event.action}</Badge></td>
                    <td>{event.entity_type}</td>
                    <td>{event.actor_user_id ?? "system"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
