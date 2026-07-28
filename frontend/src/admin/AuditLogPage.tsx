import { FormEvent, useEffect, useState } from "react";
import { auditActionLabel, auditEntityLabel } from "../labels";
import { buildAuditLogViewModel } from "../viewModels";
import { listAuditLog, listOrganizations } from "./api";
import { EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import type { AuditLogDTO, OrganizationDTO } from "./types";
import { getErrorMessage } from "../errorMessage";

type AuditFilters = {
  organization_id: string;
  actor_user_id: string;
  action: string;
  entity_type: string;
  limit: number;
  offset: number;
};

const ACTION_FILTERS = [
  "organization_created",
  "organization_updated",
  "organization_disabled",
  "organization_enabled",
  "user_created",
  "user_updated",
  "user_disabled",
  "user_enabled",
  "password_reset",
  "password_changed",
  "training_config_created",
  "training_config_updated",
  "training_config_disabled",
  "training_config_enabled",
  "training_config_assigned",
  "training_config_unassigned",
  "default_training_config_changed",
  "config_created",
  "config_updated",
  "config_assigned",
  "llm_provider_config_created",
  "llm_provider_config_updated",
  "llm_provider_config_enabled",
  "llm_provider_config_disabled",
  "login_success",
  "login_failed",
  "logout",
];

const ENTITY_FILTERS = ["organization", "user", "training_config", "client_training_config", "user_training_config", "llm_provider_config", "login_session"];

export function AuditLogPage() {
  /** Render audit log with backend-supported filters and limit/offset pagination. */
  const [organizations, setOrganizations] = useState<OrganizationDTO[]>([]);
  const [events, setEvents] = useState<AuditLogDTO[]>([]);
  const [filters, setFilters] = useState<AuditFilters>({ organization_id: "", actor_user_id: "", action: "", entity_type: "", limit: 100, offset: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async (nextFilters = filters) => {
    /** Fetch audit rows using current filter state. */
    setLoading(true);
    setError(null);
    try {
      setEvents(await listAuditLog(nextFilters));
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    /** Bootstrap organizations for the filter dropdown and initial audit rows. */
    const bootstrap = async () => {
      try {
        setOrganizations(await listOrganizations());
      } catch {
        setOrganizations([]);
      }
      await load();
    };
    void bootstrap();
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    /** Apply filter form values without navigating away. */
    event.preventDefault();
    void load(filters);
  };

  if (loading) {
    return <LoadingState title="Загрузка журнала аудита" />;
  }

  if (error) {
    return <ErrorState title="Журнал аудита недоступен" detail={error} />;
  }

  const eventVms = events.map(buildAuditLogViewModel);

  return (
    <div className="admin-page">
      <div className="admin-page__header"><div><span className="admin-kicker">Внутренний след</span><h1>Журнал аудита</h1></div></div>
      <section className="admin-panel">
        <form className="admin-form admin-form--inline" onSubmit={handleSubmit}>
          <label><span>Организация</span><select value={filters.organization_id} onChange={(event) => setFilters({ ...filters, organization_id: event.target.value, offset: 0 })}><option value="">Все</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label>
          <label><span>Действие</span><select value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value, offset: 0 })}><option value="">Все</option>{ACTION_FILTERS.map((action) => <option key={action} value={action}>{auditActionLabel(action)}</option>)}</select></label>
          <label><span>Сущность</span><select value={filters.entity_type} onChange={(event) => setFilters({ ...filters, entity_type: event.target.value, offset: 0 })}><option value="">Все</option>{ENTITY_FILTERS.map((entityType) => <option key={entityType} value={entityType}>{auditEntityLabel(entityType)}</option>)}</select></label>
          <label><span>Лимит</span><input type="number" min={1} max={500} value={filters.limit} onChange={(event) => setFilters({ ...filters, limit: Number(event.target.value), offset: 0 })} /></label>
          <button type="submit" className="admin-button admin-button--primary">Применить</button>
        </form>
      </section>
      <section className="admin-panel">
        {events.length === 0 ? <EmptyState title="Событий аудита нет" /> : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Создано</th><th>Действие</th><th>Сущность</th><th>Автор</th><th>Детали</th></tr></thead>
              <tbody>
                {eventVms.map((vm) => (
                  <tr key={vm.id}>
                    <td>{vm.createdAtLabel}</td>
                    <td>{vm.actionLabel}</td>
                    <td>{vm.entityLabel}</td>
                    <td>{vm.actorLabel}</td>
                    <td>{vm.payloadSummary}</td>
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
