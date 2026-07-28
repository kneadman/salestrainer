import { useEffect, useMemo, useState } from "react";
import { listAuditLog, listOrganizations, getUsageSummary } from "./api";
import { Badge, EmptyState, ErrorState, LoadingState, StatCard } from "./components/AdminPrimitives";
import type { AuditLogDTO, OrganizationDTO, UsageSummaryDTO } from "./types";
import { buildAuditLogViewModel } from "../viewModels";
import { getErrorMessage } from "../errorMessage";

type AdminDashboardProps = {
  onNavigate: (path: string) => void;
};

export function AdminDashboard({ onNavigate }: AdminDashboardProps) {
  /** Load and render platform-level admin overview from available internal APIs. */
  const [organizations, setOrganizations] = useState<OrganizationDTO[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLogDTO[]>([]);
  const [usageSummaries, setUsageSummaries] = useState<UsageSummaryDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    /** Bootstrap dashboard metrics from organization, usage, and audit endpoints. */
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const orgs = await listOrganizations();
        setOrganizations(orgs);
        const [audit, usageGroups] = await Promise.all([
          listAuditLog({ limit: 5, offset: 0 }),
          Promise.all(orgs.map((org) => getUsageSummary(org.id).catch(() => null))),
        ]);
        setAuditLog(audit);
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
    return <LoadingState title="Загрузка панели" detail="Получаем организации, аудит и сводки использования." />;
  }

  if (error) {
    return <ErrorState title="Панель недоступна" detail={error} />;
  }

  const auditVms = auditLog.map(buildAuditLogViewModel);

  return (
    <div className="admin-page">
      <div className="admin-page__header">
        <div>
          <span className="admin-kicker">Внутреннее администрирование</span>
          <h1>Панель управления</h1>
        </div>
        <div className="admin-actions">
          <a href="/admin/organizations" className="admin-button admin-button--primary" onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate("/admin/organizations"); }}>
            Создать организацию
          </a>
          <a href="/admin/audit-log" className="admin-button" onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate("/admin/audit-log"); }}>
            Журнал аудита
          </a>
        </div>
      </div>
      <section className="admin-stats-grid admin-stats-grid--balanced">
        <StatCard label="Организации" value={totals.organizations} detail={`${totals.activeOrganizations} активны`} />
        <StatCard label="Пользователи" value={totals.users} detail="По всем организациям" />
        <StatCard label="Тренировочные конфиги" value={totals.trainingConfigs} />
        <StatCard label="Всего сессий" value={totals.totalSessions} detail={`${totals.finishedSessions} завершены`} />
        <StatCard label="Всего сообщений" value={totals.totalTurns} />
        <StatCard label="Средний итоговый интерес" value={totals.avgInterest ?? <span className="admin-muted">Нет данных</span>} detail="По организациям с данными" />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header">
          <h2>Последние события аудита</h2>
          <a href="/admin/audit-log" className="admin-link-button" onClick={(event) => { if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey) return; event.preventDefault(); onNavigate("/admin/audit-log"); }}>
            Открыть все
          </a>
        </div>
        {auditLog.length === 0 ? (
          <EmptyState title="Событий аудита нет" detail="Записи появятся после действий администратора." />
        ) : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Действие</th>
                  <th>Сущность</th>
                  <th>Автор</th>
                </tr>
              </thead>
              <tbody>
                {auditVms.map((vm) => (
                  <tr key={vm.id}>
                    <td>{vm.createdAtLabel}</td>
                    <td><Badge>{vm.actionLabel}</Badge></td>
                    <td>{vm.entityLabel}</td>
                    <td>{vm.actorLabel}</td>
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
