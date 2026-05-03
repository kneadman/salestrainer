import type { AuthUser } from "../types";
import { ClientState, ClientStat } from "./components/ClientPrimitives";

export function BalancePage({ user }: { user: AuthUser }) {
  /** Render honest usage/balance placeholder without fake billing data. */
  return (
    <div className="client-page">
      <div className="client-page__header"><div><span className="client-kicker">Использование</span><h1>Баланс / использование</h1></div></div>
      <section className="client-stats-grid">
        <ClientStat label="Организация" value={user.client_account.name} />
        <ClientStat label="Тариф" value="Не настроен" />
        <ClientStat label="Лимиты" value="Не настроены" />
      </section>
      <section className="client-panel">
        <ClientState title="Биллинг пока не подключен." detail="Здесь будет отображаться использование, лимиты организации и предупреждения по тарифу. Реальные платежи и invoices не реализованы в этом этапе." />
      </section>
    </div>
  );
}
