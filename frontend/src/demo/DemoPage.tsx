import { useState } from "react";
import { BrandLogo } from "../components/BrandLogo";
import { ClientStat } from "../client/components/ClientPrimitives";
import { PRODUCT_NAME } from "../branding";
import { DemoTrainer } from "./DemoTrainer";

const DEMO_NAV = [
  { label: "Обзор", tab: "overview" },
  { label: "Тренажёр", tab: "trainer" },
  { label: "История", tab: "history" },
  { label: "Моя аналитика", tab: "analytics" },
  { label: "Настройки", tab: "settings" },
];

type DemoTab = (typeof DEMO_NAV)[number]["tab"];

type DemoClientLayoutProps = {
  activeTab: DemoTab;
  children: React.ReactNode;
  onTabChange: (tab: DemoTab) => void;
};

function DemoClientLayout({ activeTab, children, onTabChange }: DemoClientLayoutProps) {
  /** Render the demo cabinet shell mimicking ClientLayout without real auth data. */
  const shellClass = activeTab === "trainer" ? "client-shell client-shell--trainer" : "client-shell";
  const contentClass = activeTab === "trainer" ? "client-content client-content--trainer" : "client-content";

  return (
    <div className={shellClass}>
      <aside className="client-sidebar">
        <BrandLogo
          className="client-brand"
          imageClassName="client-brand__mark"
          textClassName="client-brand__text"
          title={PRODUCT_NAME}
          subtitle="Demo team"
        />
        <nav className="client-nav" aria-label="Навигация демо-кабинета">
          {DEMO_NAV.map((item) => (
            <button
              key={item.tab}
              type="button"
              className={
                activeTab === item.tab
                  ? "client-nav__item client-nav__item--active"
                  : "client-nav__item"
              }
              onClick={() => onTabChange(item.tab)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>
      <div className="client-main-shell">
        <header className="client-topbar">
          <div>
            <strong>demo@replikor.ai</strong>
            <span>Demo team</span>
          </div>
          <div className="client-topbar__actions">
            <span className="client-badge">Менеджер</span>
          </div>
        </header>
        <main className={contentClass}>{children}</main>
      </div>
    </div>
  );
}

function DemoOverview({ onStartTrainer }: { onStartTrainer: () => void }) {
  /** Render a static overview page with fake analytics. */
  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <span className="client-kicker">Личный кабинет</span>
          <h1>Обзор</h1>
          <p>Добро пожаловать, demo@replikor.ai</p>
        </div>
        <button type="button" className="client-button client-button--primary" onClick={onStartTrainer}>
          Начать тренировку
        </button>
      </div>
      <section className="client-stats-grid">
        <ClientStat label="Всего тренировок" value={12} />
        <ClientStat label="Завершено" value={8} />
        <ClientStat label="Средний интерес" value="64.5" />
        <ClientStat label="Среднее число ходов" value="14.2" />
        <ClientStat label="Последняя активность" value="сегодня" />
      </section>
      <section className="client-panel">
        <div className="client-panel__header">
          <h2>Последние тренировки</h2>
        </div>
        <div className="client-table-wrap">
          <table className="client-table">
            <thead>
              <tr>
                <th>Дата</th>
                <th>Статус</th>
                <th>Сценарий</th>
                <th>Ходы</th>
                <th>Интерес</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>сегодня</td>
                <td>Завершена</td>
                <td>Первичный контакт и разведка</td>
                <td>15</td>
                <td>82</td>
              </tr>
              <tr>
                <td>вчера</td>
                <td>Завершена</td>
                <td>Первичный контакт и разведка</td>
                <td>12</td>
                <td>71</td>
              </tr>
              <tr>
                <td>2 дня назад</td>
                <td>Завершена</td>
                <td>Диагностика потребностей</td>
                <td>14</td>
                <td>68</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function DemoPlaceholder({ title }: { title: string }) {
  /** Render a placeholder for tabs that are not part of the demo. */
  return (
    <div className="client-page">
      <div className="client-page__header">
        <div>
          <h1>{title}</h1>
          <p>Демо-режим: этот раздел доступен в полной версии.</p>
        </div>
      </div>
    </div>
  );
}

type DemoPageProps = {
  onNavigate: (path: string, replace?: boolean) => void;
};

export function DemoPage({ onNavigate: _onNavigate }: DemoPageProps) {
  /** Render the public demo cabinet with local tab switching. */
  const [activeTab, setActiveTab] = useState<DemoTab>("overview");

  return (
    <DemoClientLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === "overview" ? <DemoOverview onStartTrainer={() => setActiveTab("trainer")} /> : null}
      {activeTab === "trainer" ? <DemoTrainer /> : null}
      {activeTab === "history" ? <DemoPlaceholder title="История" /> : null}
      {activeTab === "analytics" ? <DemoPlaceholder title="Моя аналитика" /> : null}
      {activeTab === "settings" ? <DemoPlaceholder title="Настройки" /> : null}
    </DemoClientLayout>
  );
}
