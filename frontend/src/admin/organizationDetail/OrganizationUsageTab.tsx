import { EmptyState, StatCard } from "../components/AdminPrimitives";
import { buildUsageSummaryViewModel } from "../../viewModels";
import type { UsageSummaryDTO } from "../types";

export function OrganizationUsageTab({ usage }: { usage: UsageSummaryDTO | null }) {
  /** Render basic usage analytics from the persistent history summary endpoint. */
  if (!usage) {
    return (
      <EmptyState
        title="Сводка использования недоступна"
        detail="Сервис не вернул сводку использования для этой организации."
      />
    );
  }
  const vm = buildUsageSummaryViewModel(usage);
  return (
    <section className="admin-panel">
      <div className="admin-panel__header">
        <h2>Аналитика использования</h2>
      </div>
      <div className="admin-stats-grid">
        <StatCard label="Всего сессий" value={vm.totalSessions} />
        <StatCard label="Завершено" value={vm.finishedSessions} />
        <StatCard label="Активно" value={vm.activeSessions} />
        <StatCard label="Уникальные пользователи" value={vm.uniqueUsers} />
        <StatCard label="Всего сообщений" value={vm.totalTurns} />
        <StatCard label="Средний интерес" value={vm.avgFinalInterestScore} />
        <StatCard label="Среднее число ходов" value={vm.avgTurnCount} />
        <StatCard label="События использования" value={vm.usageEventsCount} />
        <StatCard label="Настроек с тренировками" value={vm.trainingConfigsWithSessions} />
      </div>
      <div className="admin-usage-breakdowns">
        <UsageBreakdown vm={vm.statusBreakdown} />
        <UsageBreakdown vm={vm.scenarioBreakdown} />
      </div>
    </section>
  );
}

function UsageBreakdown({ vm }: { vm: { title: string; rows: { key: string; label: string; value: number }[] } }) {
  /** Render aggregate usage values as readable rows instead of raw JSON maps. */
  if (vm.rows.length === 0) {
    return null;
  }
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <caption>{vm.title}</caption>
        <thead>
          <tr>
            <th>Группа</th>
            <th>Тренировки</th>
          </tr>
        </thead>
        <tbody>
          {vm.rows.map((row) => (
            <tr key={row.key}>
              <td>{row.label}</td>
              <td>{row.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
