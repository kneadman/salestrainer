import { EmptyState, StatCard } from "../components/AdminPrimitives";
import { buildTokenUsageViewModel, buildUsageSummaryViewModel } from "../../viewModels";
import type { TokenUsageSummaryDTO, UsageSummaryDTO } from "../types";

export function OrganizationUsageTab({
  usage,
  tokenUsage,
}: {
  usage: UsageSummaryDTO | null;
  tokenUsage: TokenUsageSummaryDTO | null;
}) {
  /** Render basic usage analytics and token usage from the persistent history summary endpoint. */
  if (!usage) {
    return (
      <EmptyState
        title="Сводка использования недоступна"
        detail="Сервис не вернул сводку использования для этой организации."
      />
    );
  }
  const vm = buildUsageSummaryViewModel(usage);
  const tokenVm = tokenUsage ? buildTokenUsageViewModel(tokenUsage) : null;
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
      {tokenVm && (
        <div className="admin-panel__section">
          <div className="admin-panel__header">
            <h3>Использование токенов (приближённые)</h3>
          </div>
          <div className="admin-stats-grid">
            <StatCard label="Всего токенов" value={tokenVm.totalTokens} />
            <StatCard label="Input" value={tokenVm.totalInput} />
            <StatCard label="Output" value={tokenVm.totalOutput} />
          </div>
          {tokenVm.perUser.length > 0 && (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <caption>По пользователям</caption>
                <thead>
                  <tr>
                    <th>Пользователь</th>
                    <th>Input (K)</th>
                    <th>Output (K)</th>
                    <th>Всего (K)</th>
                  </tr>
                </thead>
                <tbody>
                  {tokenVm.perUser.map((row) => (
                    <tr key={row.userId}>
                      <td>{row.email}</td>
                      <td>{row.totalInput}</td>
                      <td>{row.totalOutput}</td>
                      <td>{row.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
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
