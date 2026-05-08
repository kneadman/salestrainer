import { FormEvent, useEffect, useState } from "react";
import { auditActionLabel, auditEntityLabel } from "../labels";
import { listAuditLog, listOrganizations } from "./api";
import { EmptyState, ErrorState, LoadingState } from "./components/AdminPrimitives";
import type { AuditLogDTO, OrganizationDTO } from "./types";
import { compactJson, formatDate, getErrorMessage } from "./utils";

type AuditFilters = {
  organization_id: string;
  actor_user_id: string;
  action: string;
  entity_type: string;
  limit: number;
  offset: number;
};

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

  return (
    <div className="admin-page">
      <div className="admin-page__header"><div><span className="admin-kicker">Внутренний след</span><h1>Журнал аудита</h1></div></div>
      <section className="admin-panel">
        <form className="admin-form admin-form--inline" onSubmit={handleSubmit}>
          <label><span>Организация</span><select value={filters.organization_id} onChange={(event) => setFilters({ ...filters, organization_id: event.target.value, offset: 0 })}><option value="">Все</option>{organizations.map((org) => <option key={org.id} value={org.id}>{org.name}</option>)}</select></label>
          <label><span>ID пользователя</span><input value={filters.actor_user_id} onChange={(event) => setFilters({ ...filters, actor_user_id: event.target.value, offset: 0 })} /></label>
          <label><span>Действие</span><input value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value, offset: 0 })} /></label>
          <label><span>Тип сущности</span><input value={filters.entity_type} onChange={(event) => setFilters({ ...filters, entity_type: event.target.value, offset: 0 })} /></label>
          <label><span>Лимит</span><input type="number" min={1} max={500} value={filters.limit} onChange={(event) => setFilters({ ...filters, limit: Number(event.target.value), offset: 0 })} /></label>
          <button type="submit" className="admin-button admin-button--primary">Применить</button>
        </form>
      </section>
      <section className="admin-panel">
        {events.length === 0 ? <EmptyState title="Событий аудита нет" /> : (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead><tr><th>Создано</th><th>Действие</th><th>Сущность</th><th>Автор</th><th>Данные</th></tr></thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td>{formatDate(event.created_at)}</td>
                    <td>{auditActionLabel(event.action)}</td>
                    <td>{auditEntityLabel(event.entity_type)}</td>
                    <td>{event.actor_user_id ? "Администратор" : "Система"}</td>
                    <td>
                      <details className="admin-technical-details">
                        <summary>Показать технические данные</summary>
                        <pre className="admin-json-cell">{compactJson({
                          entity_id: event.entity_id,
                          actor_user_id: event.actor_user_id,
                          payload: event.payload,
                        })}</pre>
                      </details>
                    </td>
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
