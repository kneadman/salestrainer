import { Badge, EmptyState } from "../components/AdminPrimitives";
import { buildHistorySessionViewModel } from "../../viewModels";
import type { HistorySessionSummaryDTO } from "../types";

export function OrganizationHistoryTab({
  history,
  onNavigate,
}: {
  history: HistorySessionSummaryDTO[];
  onNavigate: (path: string) => void;
}) {
  /** Render persistent training history rows without hidden snapshots. */
  if (history.length === 0) {
    return (
      <EmptyState
        title="История тренировок пуста"
        detail="История появится после первых сохранённых тренировок."
      />
    );
  }
  const vms = history.map(buildHistorySessionViewModel);
  return (
    <section className="admin-panel">
      <div className="admin-panel__header">
        <h2>История тренировок</h2>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Начало</th>
              <th>Пользователь</th>
              <th>Статус</th>
              <th>Сценарий</th>
              <th>Сообщения</th>
              <th>Интерес</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {vms.map((vm, index) => (
              <tr key={vm.sessionId}>
                <td>{vm.startedAtLabel}</td>
                <td>{history[index].user_email}</td>
                <td>
                  <Badge>{vm.statusLabel}</Badge>
                </td>
                <td>{vm.scenarioLabel}</td>
                <td>{vm.turnCount}</td>
                <td>{vm.finalInterestScore}</td>
                <td>
                  <button
                    type="button"
                    className="admin-link-button"
                    onClick={() => onNavigate(`/admin/history/sessions/${vm.sessionId}`)}
                  >
                    Открыть
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
