import { StatCard } from "../components/AdminPrimitives";
import { buildOrganizationViewModel } from "../../viewModels";
import type { OrganizationDTO, UsageSummaryDTO } from "../types";

export function OrganizationOverviewTab({
  organization,
  usage,
}: {
  organization: OrganizationDTO;
  usage: UsageSummaryDTO | null;
}) {
  /** Render organization summary cards and a product-level training architecture note. */
  const vm = buildOrganizationViewModel(organization);
  return (
    <>
      <section className="admin-stats-grid">
        <StatCard label="Пользователи" value={vm.usersCount} detail={`${vm.activeUsersCount} активны`} />
        <StatCard label="Настройки тренировок" value={vm.trainingConfigsCount} />
        <StatCard label="Всего сессий" value={usage?.total_sessions ?? "—"} />
        <StatCard label="Завершено сессий" value={usage?.finished_sessions ?? "—"} />
        <StatCard label="Всего сообщений" value={usage?.total_turns ?? "—"} />
      </section>
      <section className="admin-panel">
        <div className="admin-panel__header">
          <h2>Как устроена тренировка</h2>
        </div>
        <p className="admin-muted">
          Организация задаёт бизнес-контекст и сценарий. Диалог, оценка и история работают через защищённые серверные
          контракты, поэтому скрытая персона и служебные данные не попадают в клиентский кабинет.
        </p>
      </section>
    </>
  );
}
