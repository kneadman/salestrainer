import type { FormEventHandler } from "react";
import { Tile, SectionHeading, SectionShell } from "./Primitives";
import { ProductDemo } from "./ProductDemo";
import { evaluationTiles, faqItems, managementTiles, pilotSteps, problemTiles, scenarioTiles } from "./content";

type HeaderProps = {
  authenticated: boolean;
  mobileOpen: boolean;
  onLoginClick: () => void;
  onMobileToggle: () => void;
  onCloseMobileMenu: () => void;
  onDemoClick: () => void;
  navItems: ReadonlyArray<readonly [string, string]>;
};

type HeroSectionProps = {
  onDemoClick: () => void;
  onMechanicsClick: () => void;
};

type FinalCTAProps = {
  leadStatus: "idle" | "submitting" | "success" | "error";
  leadConsent: boolean;
  onConsentChange: (value: boolean) => void;
  onLeadSubmit: FormEventHandler<HTMLFormElement>;
  onLeadFormFocus: () => void;
};

type FAQSectionProps = {
  openIndex: number | null;
  onToggle: (index: number) => void;
};

export function LandingHeader({
  authenticated,
  mobileOpen,
  onLoginClick,
  onMobileToggle,
  onCloseMobileMenu,
  onDemoClick,
  navItems,
}: HeaderProps) {
  /** Render the public landing navigation with a compact mobile menu. */
  return (
    <header className="lp-header">
      <a className="lp-brand" href="/" aria-label="Replikor">
        <span className="lp-brand__mark">R</span>
        <span className="lp-brand__text">
          <strong>Replikor</strong>
          <small>AI-тренажёр продаж</small>
        </span>
      </a>

      <nav className="lp-nav" aria-label="Основная навигация">
        {navItems.map(([label, id]) => (
          <a key={id} href={`#${id}`}>
            {label}
          </a>
        ))}
      </nav>

      <div className="lp-header__actions">
        <button type="button" className="lp-button lp-button--primary" onClick={onDemoClick}>
          Попробовать демо
        </button>
        <button type="button" className="lp-button lp-button--ghost" onClick={onLoginClick}>
          {authenticated ? "Открыть кабинет" : "Войти в кабинет"}
        </button>
      </div>

      <button
        type="button"
        className="lp-mobile-toggle"
        aria-label="Открыть меню"
        aria-expanded={mobileOpen}
        onClick={onMobileToggle}
      >
        <span />
        <span />
        <span />
      </button>

      {mobileOpen ? (
        <div className="lp-mobile-menu">
          {navItems.map(([label, id]) => (
            <a key={id} href={`#${id}`} onClick={onCloseMobileMenu}>
              {label}
            </a>
          ))}
          <button type="button" className="lp-button lp-button--primary" onClick={onDemoClick}>
            Попробовать демо
          </button>
          <button type="button" className="lp-button lp-button--ghost" onClick={onLoginClick}>
            {authenticated ? "Открыть кабинет" : "Войти в кабинет"}
          </button>
        </div>
      ) : null}
    </header>
  );
}

export function HeroSection({ onDemoClick, onMechanicsClick }: HeroSectionProps) {
  /** Lead the page with one message and one visual: a live training dialogue. */
  return (
    <section className="lp-hero">
      <div className="lp-shell lp-hero__grid lp-hero__grid--tile">
        <Tile as="div" tone="accent" className="lp-hero__copy lp-hero__copy--tile">
          <p className="lp-eyebrow">AI-тренажёр продаж</p>
          <h1>Тренируйте сложные разговоры до встречи и заранее видьте, где менеджер теряет клиента.</h1>
          <p className="lp-lead">
            Replikor имитирует живой B2B-диалог, чтобы менеджер отрабатывал сопротивление, вопросы и следующий шаг без риска для реальной сделки.
          </p>
          <div className="lp-hero__actions">
            <button type="button" className="lp-button lp-button--primary lp-button--large" onClick={onDemoClick}>
              Попробовать демо
            </button>
            <button type="button" className="lp-button lp-button--secondary lp-button--large" onClick={onMechanicsClick}>
              Посмотреть механику
            </button>
          </div>
          <span className="lp-link-action lp-link-action--spacer" aria-hidden="true" />
        </Tile>

        <div className="lp-hero__visual lp-hero__visual--tile">
          <ProductDemo variant="hero" />
        </div>
      </div>
    </section>
  );
}

export function ProblemTilesSection() {
  /** Frame the landing around management pain through lighter, shorter issue tiles. */
  return (
    <SectionShell id="problems" className="lp-section--problem">
      <div className="lp-group lp-problem-group">
        <Tile tone="accent" className="lp-problem-intro">
          <span className="lp-kicker">Проблема</span>
          <h2>Обычный контроль показывает итог, но не даёт увидеть момент, где разговор начинает терять клиента.</h2>
          <p>Скрипт, CRM и прослушка звонков собирают следы, но не показывают саму механику провала. Из-за этого обучение часто запаздывает.</p>
        </Tile>

        <div className="lp-problem-stack">
          {problemTiles.map((item, index) => (
            <Tile key={item} className={`lp-problem-tile lp-problem-tile--${index + 1}`}>
              <span className="lp-tile__index">{String(index + 1).padStart(2, "0")}</span>
              <p>{item}</p>
            </Tile>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export function DemoSection() {
  /** Show the full product walkthrough in a stable scene below the hero. */
  return (
    <SectionShell id="demo" className="lp-section--showcase">
      <div className="lp-group lp-showcase-group">
        <Tile tone="accent" className="lp-showcase-intro">
          <SectionHeading
            kicker="Как работает"
            title="Сначала разговор, затем оценка и выводы для руководителя."
            description="На одном экране видно, как менеджер ведёт диалог, где теряет качество разговора и что стоит разбирать дальше."
          />
        </Tile>

        <div className="lp-showcase-scene">
          <ProductDemo variant="interactive" />
        </div>
      </div>
    </SectionShell>
  );
}

export function EvaluationTilesSection() {
  /** Present evaluation as a metric tile system instead of a large heavy band. */
  return (
    <SectionShell id="evaluation" className="lp-section--evaluation">
      <div className="lp-group lp-evaluation-group">
        <Tile tone="accent" className="lp-evaluation-intro">
          <SectionHeading
            kicker="Что видно в отчёте"
            title="Не один итоговый балл, а карта разговора по ключевым навыкам."
            description="Каждая метрика показывает отдельный управляемый навык и подсказывает, что разбирать дальше."
          />
        </Tile>

        <div className="lp-evaluation-grid">
          {evaluationTiles.map(([title, text, score], index) => (
            <Tile key={title} className={`lp-metric-tile lp-metric-tile--${index + 1}`}>
              <div className="lp-metric__header">
                <h3>{title}</h3>
                <strong>{score}</strong>
              </div>
              <div className="lp-metric__track" aria-hidden="true">
                <span style={{ width: `${score}%` }} />
              </div>
              <p>{text}</p>
            </Tile>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export function ManagementUseCasesSection() {
  /** Present management work as a bento group with a strong lead tile and use cases. */
  return (
    <SectionShell id="management" className="lp-section--management">
      <div className="lp-group lp-management-group">
        <Tile tone="accent" className="lp-management-intro">
          <SectionHeading
            kicker="Для руководителя"
            title="Тренажёр нужен не для красивой симуляции, а для решений по качеству разговора."
            description="Он помогает понять, кого выпускать на лиды, где команда теряет сделку и какие темы нужно тренировать в первую очередь."
          />
        </Tile>

        <div className="lp-management-grid">
          {managementTiles.map((item, index) => (
            <Tile key={item} className={`lp-management-tile lp-management-tile--${index + 1}`}>
              <p>{item}</p>
            </Tile>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export function ScenarioTilesSection() {
  /** Keep scenarios as a readable split between business context and scenario tiles. */
  return (
    <SectionShell id="scenarios" className="lp-section--scenarios">
      <div className="lp-group lp-scenarios-group">
        <Tile tone="accent" className="lp-scenarios-intro">
          <SectionHeading
            kicker="Сценарии"
            title="Тренировки собираются под нишу, этап воронки и тип сопротивления клиента."
            description="Не один общий шаблон, а отдельные сценарии под конкретный продукт, сегмент и цель тренировки."
          />
        </Tile>

        <div className="lp-scenarios-cloud">
          {scenarioTiles.map((item, index) => (
            <Tile key={item} tone={index % 3 === 0 ? "accent" : "subtle"} className={`lp-scenario-tile lp-scenario-tile--${index + 1}`}>
              <h3>{item}</h3>
            </Tile>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export function PilotStepperSection({ onDemoClick }: { onDemoClick: () => void }) {
  /** Reduce adoption anxiety through a compact tile-based onboarding chain. */
  return (
    <SectionShell id="pilot" className="lp-section--pilot">
      <div className="lp-group lp-pilot-group">
        <Tile tone="accent" className="lp-pilot-intro">
          <SectionHeading
            kicker="Пилот"
            title="Запуск можно собрать вокруг одного сценария без долгого внедрения."
            description="Достаточно выбрать важный разговор, собрать тренировочного клиента и получить материал для первого разбора."
          />
        </Tile>

        <div className="lp-pilot-grid">
          {pilotSteps.map((step, index) => (
            <Tile key={step} className={`lp-step lp-step--tile lp-step--${index + 1}`}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </Tile>
          ))}
        </div>

        <Tile tone="subtle" className="lp-pilot-cta-tile">
          <h3>Один цикл, чтобы увидеть слабое место</h3>
          <p>Не нужна большая программа обучения. Достаточно одного приоритетного разговора, чтобы увидеть, как менеджер ведёт сопротивление и фиксирует следующий шаг.</p>
          <button type="button" className="lp-button lp-button--primary" onClick={onDemoClick}>
            Запустить демо-тренировку
          </button>
        </Tile>
      </div>
    </SectionShell>
  );
}

export function FinalCTASection({
  leadStatus,
  leadConsent,
  onConsentChange,
  onLeadSubmit,
  onLeadFormFocus,
}: FinalCTAProps) {
  /** End the page with a brighter conversion surface rather than one more dark block. */
  return (
    <section className="lp-section lp-section--cta" id="lead">
      <div className="lp-shell">
        <div className="lp-group lp-final lp-final--tile">
          <Tile tone="accent" className="lp-final__copy lp-final__copy--tile">
            <span className="lp-kicker">Демо</span>
            <h2>Проверьте одного менеджера на одном сценарии и получите картину слабого места до реального клиента.</h2>
            <p>Без длинного внедрения. Достаточно демо-тренировки, чтобы увидеть, как менеджер держит разговор, реагирует на сопротивление и фиксирует продолжение.</p>
          </Tile>

          <form className="lp-form lp-form--tile" onSubmit={onLeadSubmit} onFocus={onLeadFormFocus}>
            <div className="lp-form__grid">
              <label className="lp-field">
                <span>Имя</span>
                <input name="name" type="text" autoComplete="name" required />
              </label>
              <label className="lp-field">
                <span>Email</span>
                <input name="email" type="email" autoComplete="email" required />
              </label>
              <label className="lp-field">
                <span>Телефон</span>
                <input name="phone" type="tel" autoComplete="tel" required />
              </label>
              <label className="lp-field">
                <span>Компания</span>
                <input name="company" type="text" autoComplete="organization" required />
              </label>
              <label className="lp-field">
                <span>Роль</span>
                <select name="role" defaultValue="" required>
                  <option value="" disabled>
                    Выберите роль
                  </option>
                  <option value="owner">Собственник</option>
                  <option value="head_of_sales">РОП</option>
                  <option value="lnd">L&D / HR</option>
                  <option value="manager">Менеджер</option>
                </select>
              </label>
              <label className="lp-field">
                <span>Размер команды</span>
                <select name="sales_team_size" defaultValue="" required>
                  <option value="" disabled>
                    Выберите диапазон
                  </option>
                  <option value="1-5">1-5</option>
                  <option value="6-20">6-20</option>
                  <option value="21-50">21-50</option>
                  <option value="50+">50+</option>
                </select>
              </label>
              <label className="lp-field lp-field--full">
                <span>Что хотите проверить в пилоте</span>
                <textarea
                  name="comment"
                  rows={4}
                  placeholder="Например: входящая встреча, возражение по цене, квалификация ЛПР."
                />
              </label>
            </div>

            <label className="lp-checkbox">
              <input type="checkbox" checked={leadConsent} onChange={(event) => onConsentChange(event.target.checked)} />
              <span>Согласен на обработку персональных данных для связи по демо.</span>
            </label>

            <label className="lp-checkbox">
              <input type="checkbox" name="consent_marketing" />
              <span>Можно прислать материалы по пилоту и продукту.</span>
            </label>

            <button type="submit" className="lp-button lp-button--primary lp-button--large" disabled={leadStatus === "submitting"}>
              {leadStatus === "submitting" ? "Отправляем..." : "Попробовать демо"}
            </button>

            {leadStatus === "success" ? <p className="lp-form__message lp-form__message--success">Заявка отправлена. Вернёмся с демо-сценарием.</p> : null}
            {leadStatus === "error" ? <p className="lp-form__message lp-form__message--error">Проверьте форму и согласие на обработку данных.</p> : null}
          </form>
        </div>
      </div>
    </section>
  );
}

export function FAQSection({ openIndex, onToggle }: FAQSectionProps) {
  /** Keep the closing objections in a quieter block below the main CTA surface. */
  return (
    <SectionShell id="faq" className="lp-section--faq">
      <div className="lp-group lp-faq-group">
        <Tile tone="subtle" className="lp-faq-shell">
          <SectionHeading
            kicker="FAQ"
            title="Коротко о запуске, кабинетах и границах продукта."
          />

          <div className="lp-faq">
            {faqItems.map(([question, answer], index) => {
              const isOpen = openIndex === index;
              return (
                <article key={question} className="lp-faq__item">
                  <button
                    type="button"
                    className="lp-faq__trigger"
                    aria-expanded={isOpen}
                    aria-controls={`faq-panel-${index}`}
                    onClick={() => onToggle(index)}
                  >
                    <span>{question}</span>
                    <strong>{isOpen ? "−" : "+"}</strong>
                  </button>
                  {isOpen ? (
                    <p id={`faq-panel-${index}`} className="lp-faq__answer">
                      {answer}
                    </p>
                  ) : null}
                </article>
              );
            })}
          </div>
        </Tile>
      </div>
    </SectionShell>
  );
}

export function LandingFooter() {
  /** Close the public page with lightweight product and policy links. */
  return (
    <footer className="lp-footer">
      <div className="lp-shell lp-footer__grid">
        <div>
          <strong>Replikor</strong>
          <p>Тренажёр продаж для пилота, онбординга и разбора качества разговора.</p>
        </div>
        <div>
          <a href="#demo">Как работает</a>
          <a href="#scenarios">Сценарии</a>
          <a href="#lead">Демо</a>
        </div>
      </div>
    </footer>
  );
}
