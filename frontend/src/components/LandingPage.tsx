import { FormEvent, useEffect, useMemo, useState } from "react";
import { submitLead } from "../api";

type LeadStatus = "idle" | "submitting" | "success" | "error";

type LandingPageProps = {
  authenticated: boolean;
};

const navItems = [
  ["Как работает", "how-it-works"],
  ["Возможности", "features"],
  ["Для кого", "audience"],
  ["Пилот", "pilot"],
  ["FAQ", "faq"],
] as const;

const problemCards = [
  "Менеджер знает продукт, но не удерживает логику разговора",
  "Руководитель замечает ошибку после потерянного лида",
  "Новички тренируются на реальных клиентах",
  "Скрипт есть, но стандарт разговора у всех разный",
];

const trainerCards = [
  ["Диалог с ЛПР", "Менеджер ведёт разговор с ролью, характером и ограничениями, а не отвечает на тест."],
  ["Сценарии под вашу воронку", "Берём этап, продукт, тип клиента и частые возражения. Один сценарий можно запустить на старте."],
  ["Оценка по критериям", "После диалога видно, где была квалификация, аргументация, работа с сомнением и следующий шаг."],
  ["Карта готовности менеджера", "Руководитель видит не только факт тренировки, а повторяющиеся места провала."],
] as const;

const bentoCards = [
  ["Персональный конфиг клиента", "Сценарии, критерии оценки и роли ЛПР собираются вокруг вашего продукта и процесса.", "wide"],
  ["ЛПР в каждом сценарии", "Собственник, директор, закупщик или пользователь ведут разговор по-разному.", ""],
  ["История попыток", "Видно, как менеджер проходит один и тот же сценарий после разбора.", ""],
  ["Оценка диалога", "Разбор по структуре разговора, а не только итоговый балл.", "accent"],
  ["Личный кабинет", "Доступ для команды остаётся через защищённый вход.", ""],
  ["Материал для разбора с РОПом", "После тренировки остаются конкретные фрагменты для обратной связи.", ""],
  ["Пилот с одного сценария", "Можно начать с узкого участка: например, входящая встреча или возражение по цене.", "wide"],
] as const;

const audienceCards = [
  ["Собственник", "Хочет, чтобы обучение не держалось на памяти одного сильного РОПа."],
  ["РОП", "Хочет видеть не просто факт тренировки, а место, где менеджер теряет разговор."],
  ["HR / L&D", "Хочет сделать онбординг проверяемым, а не формальным."],
  ["Менеджер", "Получает место, где можно ошибиться до разговора с настоящим клиентом."],
] as const;

const useCases = [
  ["Онбординг новичка", "Стартовый сложный разговор проходит в тренажёре, а не на живом лиде."],
  ["Отработка возражений", "Команда повторяет типовые сопротивления и видит, где ответ уходит в шаблон."],
  ["Запуск нового продукта", "Перед стартом продаж менеджеры проходят сценарии с новым контекстом."],
  ["Аттестация", "Руководитель получает одинаковую рамку оценки для разных менеджеров."],
  ["Просадки в воронке", "Можно взять этап, где чаще всего теряется следующий шаг."],
  ["Единый стандарт коммуникации", "Скрипт превращается в проверяемый стандарт разговора."],
] as const;

const securityCards = [
  "Данные клиента отделены конфигом",
  "Доступ через личный кабинет",
  "Сценарии настраиваются вручную",
  "Результат зависит от внедрения и дисциплины",
  "Юридические документы и согласия в формах",
];

const pilotSteps = [
  "Разбираем вводные",
  "Собираем стартовый сценарий",
  "Подключаем доступы",
  "Проводим стартовые тренировки",
  "Смотрим карту готовности",
];

const launchFormats = [
  ["Демо", "Показываем механику диалога, оценку и кабинет на демонстрационном сценарии."],
  ["Пилот", "Собираем один рабочий сценарий под ваш продукт и проверяем формат на небольшой группе."],
  ["Команда", "Расширяем набор сценариев для онбординга, аттестации или регулярной практики."],
] as const;

const faqItems = [
  ["Это заменяет обучение менеджеров?", "Нет. Тренажёр даёт практику и материал для разбора, а руководитель остаётся владельцем стандарта и обратной связи."],
  ["Можно ли настроить сценарии под наш продукт?", "Да. Для пилота обычно фиксируются продукт, этап воронки, роли ЛПР, типовые сомнения и критерии оценки."],
  ["Можно ли использовать для новичков?", "Да. Новичок получает безопасное место для ошибок до разговора с настоящим клиентом."],
  ["Подходит ли для опытных менеджеров?", "Да, если нужно отработать сложные ситуации: новый продукт, другой сегмент, просадку по этапу или нестандартные возражения."],
  ["Есть ли личный кабинет?", "Да. Все CTA личного кабинета ведут на существующую страницу входа /login."],
  ["Можно ли гарантировать рост продаж?", "Нет. Мы не обещаем магический рост. Итог зависит от внедрения, регулярности практики, качества сценариев и работы руководителя."],
  ["Что нужно для старта?", "Для стартового сценария нужны вводные по продукту, этапу воронки, типовым клиентам, возражениям и желаемому стандарту разговора."],
] as const;

function track(event: string, payload: Record<string, unknown> = {}) {
  const data = { event, ...payload };
  window.dispatchEvent(new CustomEvent("landing_analytics", { detail: data }));
  const maybeWindow = window as Window & { dataLayer?: Record<string, unknown>[] };
  maybeWindow.dataLayer?.push(data);
}

function collectQueryParams() {
  return Object.fromEntries(new URLSearchParams(window.location.search).entries());
}

function scrollToBlock(id: string, eventName: "hero_demo_click" | "lead_form_open" | "pilot_cta_click") {
  track(eventName);
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function LandingPage({ authenticated }: LandingPageProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [leadStatus, setLeadStatus] = useState<LeadStatus>("idle");
  const [leadConsent, setLeadConsent] = useState(false);
  const [leadFormOpened, setLeadFormOpened] = useState(false);
  const [faqOpen, setFaqOpen] = useState<number | null>(0);
  const [cookiesAccepted, setCookiesAccepted] = useState(() => localStorage.getItem("salestrainer.cookiesAccepted") === "true");
  const queryParams = useMemo(collectQueryParams, []);

  useEffect(() => {
    track("landing_view", { authenticated });
    let seen50 = false;
    let seen90 = false;
    const onScroll = () => {
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (maxScroll <= 0) {
        return;
      }
      const progress = window.scrollY / maxScroll;
      if (!seen50 && progress >= 0.5) {
        seen50 = true;
        track("scroll_50");
      }
      if (!seen90 && progress >= 0.9) {
        seen90 = true;
        track("scroll_90");
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [authenticated]);

  const handleLoginClick = () => {
    track("login_click");
    window.location.href = "/login";
  };

  const handleCookieAccept = () => {
    localStorage.setItem("salestrainer.cookiesAccepted", "true");
    setCookiesAccepted(true);
    track("cookie_accept");
  };

  const closeMobileMenu = () => setMobileOpen(false);

  const handleMobileDemoClick = () => {
    closeMobileMenu();
    scrollToBlock("lead", "hero_demo_click");
  };

  const handleLeadSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!leadConsent || leadStatus === "submitting") {
      setLeadStatus("error");
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = {
      name: String(formData.get("name") ?? "").trim(),
      email: String(formData.get("email") ?? "").trim(),
      phone: String(formData.get("phone") ?? "").trim(),
      company: String(formData.get("company") ?? "").trim(),
      role: String(formData.get("role") ?? "").trim(),
      sales_team_size: String(formData.get("sales_team_size") ?? "").trim(),
      comment: String(formData.get("comment") ?? "").trim() || null,
      consent_personal_data: true,
      consent_marketing: formData.get("consent_marketing") === "on",
      query_params: queryParams,
      page: "landing",
      form_id: "main_lead_form",
    };

    setLeadStatus("submitting");
    track("lead_form_submit");
    try {
      await submitLead(payload);
      setLeadStatus("success");
      track("lead_form_success");
      form.reset();
      setLeadConsent(false);
    } catch {
      setLeadStatus("error");
      track("lead_form_error");
    }
  };

  const handleLeadFormFocus = () => {
    if (!leadFormOpened) {
      setLeadFormOpened(true);
      track("lead_form_open");
    }
  };

  return (
    <div className="landing-page">
      <header className="landing-header">
        <a className="landing-logo" href="/" aria-label="Sales Trainer">
          <span className="landing-logo__mark">ST</span>
          <span>Sales Trainer</span>
        </a>

        <nav className="landing-nav" aria-label="Основная навигация">
          {navItems.map(([label, id]) => (
            <a key={id} href={`#${id}`}>
              {label}
            </a>
          ))}
        </nav>

        <div className="landing-header__actions">
          <button type="button" className="landing-button" onClick={() => scrollToBlock("lead", "hero_demo_click")}>
            Получить демонстрацию
          </button>
          <button type="button" className="landing-button landing-button--ghost" onClick={handleLoginClick}>
            Личный кабинет
          </button>
        </div>

        <button
          type="button"
          className="mobile-menu-button"
          aria-label="Открыть меню"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen((value) => !value)}
        >
          <span />
          <span />
          <span />
        </button>
        {mobileOpen ? (
          <div className="mobile-menu">
            {navItems.map(([label, id]) => (
              <a key={id} href={`#${id}`} onClick={closeMobileMenu}>
                {label}
              </a>
            ))}
            <button type="button" onClick={handleMobileDemoClick}>
              Получить демонстрацию
            </button>
            <button type="button" onClick={handleLoginClick}>
              Личный кабинет
            </button>
          </div>
        ) : null}
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-container landing-hero__grid">
            <div className="landing-hero__copy fade-up">
              <p className="landing-eyebrow">AI-тренажёр отдела продаж</p>
              <h1>Менеджер может знать скрипт — и всё равно потеряться в разговоре</h1>
              <p className="landing-hero__lead">
                AI-тренажёр создаёт безопасную среду для сложных диалогов: с ЛПР, возражениями, контекстом продукта и
                оценкой по структуре разговора. Руководитель видит готовность менеджера до выхода к реальному клиенту.
              </p>
              <div className="landing-hero__actions">
                <button type="button" className="landing-button landing-button--large" onClick={() => scrollToBlock("lead", "hero_demo_click")}>
                  Получить демонстрацию
                </button>
                <button type="button" className="landing-button landing-button--secondary landing-button--large" onClick={() => scrollToBlock("pilot", "pilot_cta_click")}>
                  Обсудить пилот
                </button>
                <button type="button" className="landing-button landing-button--ghost landing-button--large" onClick={handleLoginClick}>
                  Личный кабинет
                </button>
              </div>
              <p className="landing-microcopy">
                Без обещаний магического роста. Покажем, как тренажёр встраивается в ваш онбординг, аттестацию и регулярную практику.
              </p>
            </div>

            <div className="hero-dashboard fade-up" aria-label="Макет интерфейса тренажёра">
              <div className="scenario-card">
                <span>Сценарий</span>
                <strong>Входящая встреча после заявки</strong>
                <p>Персона: собственник, осторожный, считает деньги</p>
              </div>
              <div className="chat-card">
                <div className="chat-line chat-line--client">Мне важно понять, чем это отличается от обычного обучения.</div>
                <div className="chat-line chat-line--manager">Расскажу через ваш процесс: как сейчас проверяете готовность менеджера?</div>
                <div className="chat-line chat-line--client">Слушаем звонки, но часто уже после ошибки.</div>
              </div>
              <div className="scorecard">
                <div className="scorecard__top">
                  <span>Готовность</span>
                  <strong>72/100</strong>
                </div>
                <ScoreBar label="Квалификация" value={78} />
                <ScoreBar label="Возражения" value={64} />
                <ScoreBar label="Следующий шаг" value={58} />
              </div>
              <div className="manager-hint">
                <strong>Подсказка руководителю</strong>
                <p>Сильная зона: выяснил текущий процесс. Просадка: не уточнил критерии выбора. Следующий шаг: зафиксирован частично.</p>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section diagnostic-section fade-up" id="how-it-works">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Диагностика</span>
              <h2>Проблема появляется не в тесте. Она появляется в диалоге.</h2>
            </div>
            <div className="problem-grid">
              {problemCards.map((text) => (
                <article className="problem-card" key={text}>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section fade-up">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Что делает тренажёр</span>
              <h2>Он заставляет не читать про продажи, а проходить разговор</h2>
            </div>
            <div className="trainer-grid">
              {trainerCards.map(([title, text]) => (
                <article className="trainer-card" key={title}>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section dashboard-section fade-up">
          <div className="landing-container landing-two-col">
            <div>
              <span className="section-kicker">Что видит руководитель</span>
              <h2>После тренировки остаётся разбор, а не ощущение</h2>
              <p>
                После тренировки остаётся не ощущение “нормально поговорил”, а разбор: где менеджер уточнил ситуацию,
                где ушёл в шаблон, где потерял следующий шаг.
              </p>
            </div>
            <div className="leader-dashboard" aria-label="Макет кабинета руководителя">
              <aside className="leader-list">
                {["Анна", "Илья", "Мария"].map((name, index) => (
                  <div className={index === 1 ? "leader-person leader-person--active" : "leader-person"} key={name}>
                    <span>{name}</span>
                    <strong>{[82, 67, 74][index]}</strong>
                  </div>
                ))}
              </aside>
              <div className="leader-detail">
                <div className="leader-detail__head">
                  <span>Выбранный менеджер</span>
                  <strong>Илья, 67/100</strong>
                </div>
                <p>Последние тренировки: входящая встреча, возражение по бюджету, повторный контакт.</p>
                <ScoreBar label="Квалификация" value={76} />
                <ScoreBar label="Аргументация" value={69} />
                <ScoreBar label="Работа с возражениями" value={54} />
                <ScoreBar label="Следующий шаг" value={61} />
                <div className="recommendation">
                  <strong>Рекомендация к разбору</strong>
                  <p>Проверить, как менеджер фиксирует критерии выбора и следующий шаг после сомнения по бюджету.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section fade-up" id="features">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Возможности</span>
              <h2>Не набор карточек, а рабочий контур тренировки</h2>
            </div>
            <div className="bento-grid">
              {bentoCards.map(([title, text, tone]) => (
                <article className={`bento-card ${tone === "wide" ? "bento-card--wide" : ""} ${tone === "accent" ? "bento-card--accent" : ""}`} key={title}>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section fade-up" id="audience">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Для кого</span>
              <h2>Разные роли смотрят на тренажёр с разных задач</h2>
            </div>
            <div className="roles-grid">
              {audienceCards.map(([title, text]) => (
                <article className="role-card" key={title}>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section fade-up">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Сценарии использования</span>
              <h2>Начать можно с узкого места, которое уже видно в команде</h2>
            </div>
            <div className="usecase-grid">
              {useCases.map(([title, text]) => (
                <article className="usecase-card" key={title}>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section maturity-section fade-up">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Безопасность и операционная зрелость</span>
              <h2>Лендинг не обещает чудо. Продукт должен встраиваться в процесс.</h2>
            </div>
            <div className="maturity-grid">
              {securityCards.map((text) => (
                <article className="maturity-card" key={text}>
                  <span />
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section pilot-section fade-up" id="pilot">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Пилот</span>
              <h2>Пилот можно начать с одного сценария</h2>
            </div>
            <div className="timeline">
              {pilotSteps.map((step, index) => (
                <article className="timeline-step" key={step}>
                  <span>{index + 1}</span>
                  <p>{step}</p>
                </article>
              ))}
            </div>
            <button type="button" className="landing-button landing-button--large" onClick={() => scrollToBlock("lead", "pilot_cta_click")}>
              Обсудить пилот
            </button>
          </div>
        </section>

        <section className="landing-section fade-up">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Форматы запуска</span>
              <h2>Без цен на лендинге: сначала нужно понять сценарий</h2>
            </div>
            <div className="launch-grid">
              {launchFormats.map(([title, text]) => (
                <article className="launch-card" key={title}>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  <button type="button" className="landing-link-button" onClick={() => scrollToBlock("lead", "pilot_cta_click")}>
                    Обсудить формат
                  </button>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section lead-section fade-up" id="lead">
          <div className="landing-container landing-two-col">
            <div>
              <span className="section-kicker">Заявка</span>
              <h2>Обсудим демонстрацию или пилот</h2>
              <p>Опишите команду и текущую задачу. Мы вернёмся с вопросами по сценарию, материалам и формату запуска.</p>
            </div>
            <form className="landing-form" onFocusCapture={handleLeadFormFocus} onSubmit={handleLeadSubmit}>
              <div className="landing-form__grid">
                <label className="landing-field"><span>Имя</span><input name="name" autoComplete="name" required /></label>
                <label className="landing-field"><span>Рабочий email</span><input name="email" type="email" autoComplete="email" required /></label>
                <label className="landing-field"><span>Телефон</span><input name="phone" type="tel" autoComplete="tel" required /></label>
                <label className="landing-field"><span>Компания</span><input name="company" autoComplete="organization" required /></label>
                <label className="landing-field"><span>Роль</span><input name="role" required /></label>
                <label className="landing-field">
                  <span>Размер отдела продаж</span>
                  <select name="sales_team_size" required>
                    <option value="">Выберите</option>
                    <option>1-5</option>
                    <option>6-15</option>
                    <option>16-50</option>
                    <option>Больше 50</option>
                  </select>
                </label>
              </div>
              <label className="landing-field">
                <span>Комментарий</span>
                <textarea name="comment" rows={4} placeholder="Например: хотим пилот для входящей встречи после заявки" />
              </label>
              <label className="landing-checkbox">
                <input type="checkbox" checked={leadConsent} onChange={(event) => setLeadConsent(event.target.checked)} />
                <span>
                  Я соглашаюсь на обработку персональных данных для связи по моей заявке. Подробности — в Политике обработки персональных данных.
                </span>
              </label>
              <label className="landing-checkbox">
                <input type="checkbox" name="consent_marketing" />
                <span>Я согласен получать информационные и рекламные материалы о продукте. Согласие можно отозвать.</span>
              </label>
              <button type="submit" className="landing-button landing-button--large" disabled={!leadConsent || leadStatus === "submitting"}>
                {leadStatus === "submitting" ? "Отправляем..." : "Оставить заявку"}
              </button>
              {leadStatus === "success" ? <p className="form-status form-status--success">Заявка принята. Мы свяжемся, чтобы уточнить вводные для демонстрации.</p> : null}
              {leadStatus === "error" ? <p className="form-status form-status--error">Не удалось отправить заявку. Проверьте обязательные поля и согласие.</p> : null}
            </form>
          </div>
        </section>

        <section className="landing-section fade-up" id="faq">
          <div className="landing-container faq-list">
            <div className="section-heading">
              <span className="section-kicker">FAQ</span>
              <h2>Коротко о внедрении</h2>
            </div>
            {faqItems.map(([question, answer], index) => (
              <article className="faq-item" key={question}>
                <button
                  type="button"
                  aria-expanded={faqOpen === index}
                  onClick={() => {
                    setFaqOpen(faqOpen === index ? null : index);
                    track("faq_open", { question });
                  }}
                >
                  <span>{question}</span>
                  <strong>{faqOpen === index ? "-" : "+"}</strong>
                </button>
                {faqOpen === index ? <p>{answer}</p> : null}
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section final-cta fade-up">
          <div className="landing-container final-cta__inner">
            <h2>Покажите менеджеру сложный диалог до того, как его покажет клиент</h2>
            <p>Оставьте заявку — обсудим, какой сценарий лучше взять для стартового пилота.</p>
            <div className="landing-hero__actions">
              <button type="button" className="landing-button landing-button--large" onClick={() => scrollToBlock("lead", "hero_demo_click")}>
                Получить демонстрацию
              </button>
              <button type="button" className="landing-button landing-button--ghost landing-button--large" onClick={handleLoginClick}>
                Личный кабинет
              </button>
            </div>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-container landing-footer__grid">
          <div>
            <strong>Sales Trainer</strong>
            <p>AI-тренажёр для практики сложных диалогов в отделе продаж.</p>
            <p>Реквизиты будут добавлены перед публикацией.</p>
          </div>
          <div>
            <a href="/login" onClick={() => track("login_click")}>Личный кабинет</a>
            <a href="#lead">Получить демонстрацию</a>
            <a href="#pilot">Обсудить пилот</a>
          </div>
          <div className="legal-note">
            <p>Политика обработки персональных данных</p>
            <p>Согласие на обработку персональных данных</p>
            <p>Пользовательское соглашение</p>
            <p>Политика cookies</p>
            <p>Правовая информация</p>
            <p>email для обращений по ПД: TODO</p>
          </div>
        </div>
      </footer>

      {!cookiesAccepted ? (
        <div className="cookie-banner" role="region" aria-label="Уведомление о cookies">
          <p>
            Мы используем cookies и аналитические инструменты, чтобы понимать, как работает сайт. Продолжая пользоваться
            сайтом или нажимая «Принять», вы соглашаетесь с использованием cookies.
          </p>
          <button type="button" className="landing-button" onClick={handleCookieAccept}>
            Принять
          </button>
        </div>
      ) : null}
    </div>
  );
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-row">
      <div className="score-row__label">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="score-track">
        <span style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
