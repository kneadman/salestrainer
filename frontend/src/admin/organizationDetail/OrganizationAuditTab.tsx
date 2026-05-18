import { EmptyState } from "../components/AdminPrimitives";
import { buildAuditLogViewModel } from "../../viewModels";
import type { AuditLogDTO } from "../types";

export function OrganizationAuditTab({ audit }: { audit: AuditLogDTO[] }) {
  /** Render organization-scoped audit events with readable payload summaries. */
  if (audit.length === 0) {
    return <EmptyState title="Событий аудита нет" />;
  }
  const vms = audit.map(buildAuditLogViewModel);
  return (
    <section className="admin-panel">
      <div className="admin-panel__header">
        <h2>Аудит</h2>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Время</th>
              <th>Действие</th>
              <th>Сущность</th>
              <th>Автор</th>
              <th>Детали</th>
            </tr>
          </thead>
          <tbody>
            {vms.map((vm) => (
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
    </section>
  );
}
