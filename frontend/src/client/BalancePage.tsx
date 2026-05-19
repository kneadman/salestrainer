import type { AuthUser } from "../types";
import { ClientState } from "./components/ClientPrimitives";

export function BalancePage({ user: _user, onNavigate }: { user: AuthUser; onNavigate?: (path: string, replace?: boolean) => void }) {
  /** Keep the future usage section route in code while the product surface is hidden. */
  return (
    <div className="client-page">
      <section className="client-panel">
        <ClientState title="Раздел использования временно скрыт." detail="Вернитесь в обзор кабинета." />
        <a href="/app" className="client-button client-button--primary" onClick={(event) => { event.preventDefault(); onNavigate?.("/app", true); }}>
          Перейти в обзор
        </a>
      </section>
    </div>
  );
}
