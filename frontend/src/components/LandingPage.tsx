import { FormEvent, useEffect, useMemo, useState } from "react";
import { submitLead, submitQuizLead } from "../api";

type LeadStatus = "idle" | "submitting" | "success" | "error";

type LandingPageProps = {
  authenticated: boolean;
};

const weakPointOptions = [
  "Первый контакт",
  "Квалификация",
  "Презентация",
  "Возражения",
  "Фиксация следующего шага",
  "Повторные касания",
  "Работа по скрипту",
];

const faqItems = [
  {
    question: "Можно ли настроить сценарии под наш продукт?",
    answer:
      "Да. В пилоте обычно фиксируются роли клиентов, этапы воронки, типовые возражения и критерии оценки диалога.",
  },
  {
    question: "Это заменяет обучение руководителя?",
    answer:
      "Нет. Тренажер дает регулярную практику и структурированную картину по диалогам, а руководитель использует ее для точечной обратной связи.",
  },
  {
    question: "Нужны ли записи звонков и база знаний?",
    answer:
      "Они помогают быстрее собрать контекст, но пилот можно начать с описания продукта, воронки, скрипта и нескольких типовых ситуаций.",
  },
  {
    question: "Что получает руководитель после тренировок?",
    answer:
      "Карточку с ходом диалога, оценкой по ключевым критериям и подсказками, где менеджеру стоит потренироваться дополнительно.",
  },
];

function track(event: string, payload: Record<string, unknown> = {}) {
  const data = { event, ...payload };
  window.dispatchEvent(new CustomEvent("landing_analytics", { detail: data }));
  const maybeWindow = window as Window & { dataLayer?: Record<string, unknown>[] };
  maybeWindow.dataLayer?.push(data);
}

function collectQueryParams() {
  return Object.fromEntries(new URLSearchParams(window.location.search).entries());
}

function scrollToBlock(id: string, eventName: string) {
  track(eventName);
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function LandingPage({ authenticated }: LandingPageProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [leadStatus, setLeadStatus] = useState<LeadStatus>("idle");
  const [quizStatus, setQuizStatus] = useState<LeadStatus>("idle");
  const [leadConsent, setLeadConsent] = useState(false);
  const [quizConsent, setQuizConsent] = useState(false);
  const [quizStep, setQuizStep] = useState(0);
  const [faqOpen, setFaqOpen] = useState<number | null>(0);
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

  const handleLeadSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!leadConsent || leadStatus === "submitting") {
      setLeadStatus("error");
      return;
    }
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    setLeadStatus("submitting");
    track("lead_form_submit");
    try {
      await submitLead({ ...payload, query_params: queryParams });
      setLeadStatus("success");
      track("lead_form_success");
      form.reset();
      setLeadConsent(false);
    } catch {
      setLeadStatus("error");
      track("lead_form_error");
    }
  };

  const handleQuizSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!quizConsent || quizStatus === "submitting") {
      setQuizStatus("error");
      return;
    }
    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload = {
      team_size: formData.get("team_size"),
      onboarding_time: formData.get("onboarding_time"),
      weak_points: formData.getAll("weak_points"),
      materials: formData.get("materials"),
      format: formData.get("format"),
      name: formData.get("quiz_name"),
      email: formData.get("quiz_email"),
      phone: formData.get("quiz_phone"),
      company: formData.get("quiz_company"),
      query_params: queryParams,
    };
    setQuizStatus("submitting");
    track("quiz_submit");
    try {
      await submitQuizLead(payload);
      setQuizStatus("success");
      track("lead_form_success", { source: "quiz" });
    } catch {
      setQuizStatus("error");
      track("lead_form_error", { source: "quiz" });
    }
  };

  const nextQuizStep = () => {
    const next = Math.min(quizStep + 1, 2);
    setQuizStep(next);
    track(quizStep === 0 ? "quiz_start" : "quiz_step_complete", { step: quizStep + 1 });
  };

  return (
    <div className="landing-page">
      <header className="landing-header">
        <a className="landing-logo" href="/" aria-label="Sales Trainer">
          <span className="landing-logo__mark">ST</span>
          <span>Sales Trainer</span>
        </a>
        <nav className="landing-nav" aria-label="Основная навигация">
          <a href="#product">Продукт</a>
          <a href="#workflow">Как работает</a>
          <a href="#quiz">Квиз</a>
          <a href="#pilot">Пилот</a>
        </nav>
        <div className="landing-header__actions">
          <button type="button" className="landing-link-button" onClick={() => scrollToBlock("quiz", "hero_quiz_click")}>
            Квиз
          </button>
          <button type="button" className="landing-button landing-button--ghost" onClick={handleLoginClick}>
            Личный кабинет
          </button>
          <button type="button" className="landing-button" onClick={() => scrollToBlock("lead", "lead_form_open")}>
            Оставить заявку
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
            <a href="#product" onClick={() => setMobileOpen(false)}>Продукт</a>
            <a href="#workflow" onClick={() => setMobileOpen(false)}>Как работает</a>
            <a href="#quiz" onClick={() => setMobileOpen(false)}>Квиз</a>
            <button type="button" onClick={handleLoginClick}>Личный кабинет</button>
          </div>
        ) : null}
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-container landing-hero__grid">
            <div className="landing-hero__copy">
              <p className="landing-eyebrow">AI-тренажер отдела продаж</p>
              <h1>Тренажер отдела продаж, где менеджеры проходят сложные диалоги до встречи с реальными клиентами</h1>
              <p className="landing-hero__lead">
                Сценарии настраиваются под продукт, этапы воронки и типовых ЛПР. Руководитель видит, как менеджер
                квалифицирует клиента, работает с возражениями и фиксирует следующий шаг.
              </p>
              <div className="landing-hero__actions">
                <button type="button" className="landing-button landing-button--large" onClick={() => scrollToBlock("lead", "hero_demo_click")}>
                  Получить демонстрацию
                </button>
                <button type="button" className="landing-button landing-button--secondary landing-button--large" onClick={() => scrollToBlock("quiz", "hero_quiz_click")}>
                  Пройти короткий квиз
                </button>
                <button type="button" className="landing-button landing-button--ghost landing-button--large" onClick={handleLoginClick}>
                  Личный кабинет
                </button>
              </div>
              <div className="landing-audience" aria-label="Кому подходит">
                <span>РОП</span>
                <span>HR / L&D</span>
                <span>Коммерческий директор</span>
                <span>Контакт-центр</span>
              </div>
            </div>

            <div className="trainer-mockup" aria-label="Макет интерфейса тренажера">
              <div className="mockup-topbar">
                <span>Сценарий: квалификация</span>
                <strong>Активная тренировка</strong>
              </div>
              <div className="mockup-chat">
                <div className="mock-message mock-message--client">Нам важно понять окупаемость, а не просто купить еще один инструмент.</div>
                <div className="mock-message mock-message--manager">Уточню текущий процесс: как сейчас проверяете готовность менеджера к разговору?</div>
                <div className="mock-score">
                  <span>Оценка диалога</span>
                  <strong>74/100</strong>
                </div>
              </div>
              <div className="mockup-insights">
                <div><span />Квалификация: есть контекст</div>
                <div><span />Возражение: нужен следующий вопрос</div>
                <div><span />Следующий шаг: зафиксирован частично</div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-section trust-strip">
          <div className="landing-container trust-strip__grid">
            <div>
              <span className="section-kicker">Для команд, где обучение должно быть проверяемым</span>
              <h2>Подходит, когда скрипта уже недостаточно</h2>
            </div>
            <p>
              Тренажер помогает перевести онбординг, аттестацию и регулярную практику в серию диалогов с понятной
              оценкой, без экспериментов на реальных сделках.
            </p>
          </div>
        </section>

        <section className="landing-section" id="product">
          <div className="landing-container landing-two-col">
            <div>
              <span className="section-kicker">Проблема</span>
              <h2>Скрипт не показывает, готов ли менеджер к разговору</h2>
            </div>
            <div className="problem-list">
              <article>
                <h3>Сложно увидеть слабое место</h3>
                <p>Менеджер может знать текст, но теряться при уточняющих вопросах, сопротивлении или смене роли ЛПР.</p>
              </article>
              <article>
                <h3>Обратная связь разрознена</h3>
                <p>Руководитель слушает выборочные звонки и держит часть критериев в голове, поэтому развитие идет неровно.</p>
              </article>
              <article>
                <h3>Онбординг зависит от занятости команды</h3>
                <p>Новичку нужна практика до реальных клиентов, но у наставников не всегда есть окно на повторяемые тренировки.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Что делает продукт</span>
              <h2>Онбординг становится серией проверяемых диалогов</h2>
            </div>
            <div className="bento-grid">
              <article className="bento-card bento-card--wide">
                <h3>Персональный контекст клиента</h3>
                <p>Сценарии собираются вокруг вашего продукта, воронки, типовых ролей, ограничений и частых возражений.</p>
              </article>
              <article className="bento-card">
                <h3>Персонажи ЛПР</h3>
                <p>Диалог ведется с ролью, логикой принятия решения и стилем общения, близкими к реальным ситуациям.</p>
              </article>
              <article className="bento-card">
                <h3>Оценка по структуре</h3>
                <p>Система смотрит на квалификацию, работу с возражением, точность следующего шага и динамику диалога.</p>
              </article>
              <article className="bento-card">
                <h3>Карта готовности</h3>
                <p>Руководитель видит, какие темы стоит отработать с конкретным менеджером или всей командой.</p>
              </article>
              <article className="bento-card bento-card--accent">
                <h3>Без риска для сделки</h3>
                <p>Менеджер тренируется на сложных ситуациях до контакта с клиентом, а не после спорного разговора.</p>
              </article>
            </div>
          </div>
        </section>

        <section className="landing-section" id="workflow">
          <div className="landing-container">
            <div className="section-heading">
              <span className="section-kicker">Как работает</span>
              <h2>От настройки контекста до динамики по команде</h2>
            </div>
            <div className="steps-grid">
              {["Контекст", "Сценарии", "Тренировка", "Оценка", "Динамика"].map((step, index) => (
                <article className="step-card" key={step}>
                  <span>{index + 1}</span>
                  <h3>{step}</h3>
                  <p>
                    {[
                      "Фиксируются продукт, сегменты клиентов и критерии хорошего разговора.",
                      "Подбираются роли ЛПР, этапы воронки и ситуации для пилота.",
                      "Менеджер ведет диалог с клиентом в личном кабинете.",
                      "После сессии формируется разбор по структуре разговора.",
                      "Руководитель видит повторяющиеся просадки и план практики.",
                    ][index]}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-container roles-grid">
            {[
              ["Собственник", "Понять, где обучение влияет на управляемость отдела, без ручного разбора каждого диалога."],
              ["РОП", "Быстрее находить конкретные навыки, которые мешают менеджеру пройти этап воронки."],
              ["HR / L&D", "Собрать повторяемую программу адаптации и аттестации для коммерческой команды."],
              ["Менеджер", "Тренироваться на сложных разговорах и получать понятную обратную связь после сессии."],
            ].map(([title, text]) => (
              <article className="role-card" key={title}>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section dashboard-section">
          <div className="landing-container landing-two-col">
            <div>
              <span className="section-kicker">Личный кабинет</span>
              <h2>Клиентский доступ остается через существующую страницу входа</h2>
              <p>
                Действующие пользователи переходят в кабинет через `/login`. Лендинг не заменяет авторизацию и не меняет
                логику тренировочных сессий.
              </p>
              <button type="button" className="landing-button landing-button--ghost" onClick={handleLoginClick}>
                Личный кабинет
              </button>
            </div>
            <div className="cabinet-mockup">
              <div className="cabinet-row cabinet-row--head"><span>Команда</span><strong>Готовность</strong></div>
              <div className="cabinet-row"><span>Новые менеджеры</span><meter min="0" max="100" value="62" /></div>
              <div className="cabinet-row"><span>Возражения</span><meter min="0" max="100" value="48" /></div>
              <div className="cabinet-row"><span>Следующий шаг</span><meter min="0" max="100" value="76" /></div>
            </div>
          </div>
        </section>

        <section className="landing-section quiz-section" id="quiz">
          <div className="landing-container landing-two-col">
            <div>
              <span className="section-kicker">Диагностический квиз</span>
              <h2>Подберите формат пилота по текущей ситуации в отделе</h2>
              <p>Квиз не считает экономический эффект автоматически. Он помогает собрать вводные для демонстрации или пилота.</p>
            </div>
            <form className="landing-form" onSubmit={handleQuizSubmit}>
              <div className={quizStep === 0 ? "quiz-step quiz-step--active" : "quiz-step"}>
                <label className="landing-field">
                  <span>Сколько менеджеров в отделе продаж?</span>
                  <select name="team_size" required>
                    <option value="">Выберите диапазон</option>
                    <option>1-5</option>
                    <option>6-15</option>
                    <option>16-50</option>
                    <option>Больше 50</option>
                  </select>
                </label>
                <label className="landing-field">
                  <span>Сколько занимает адаптация нового менеджера?</span>
                  <select name="onboarding_time" required>
                    <option value="">Выберите срок</option>
                    <option>До 2 недель</option>
                    <option>2-4 недели</option>
                    <option>1-2 месяца</option>
                    <option>Больше 2 месяцев</option>
                  </select>
                </label>
                <button type="button" className="landing-button" onClick={nextQuizStep}>Дальше</button>
              </div>

              <div className={quizStep === 1 ? "quiz-step quiz-step--active" : "quiz-step"}>
                <fieldset className="landing-fieldset">
                  <legend>Где чаще всего проседают менеджеры?</legend>
                  {weakPointOptions.map((option) => (
                    <label key={option} className="landing-checkbox">
                      <input type="checkbox" name="weak_points" value={option} />
                      <span>{option}</span>
                    </label>
                  ))}
                </fieldset>
                <label className="landing-field">
                  <span>Есть ли скрипты, база знаний или записи звонков?</span>
                  <select name="materials" required>
                    <option value="">Выберите вариант</option>
                    <option>Да, есть структурированные материалы</option>
                    <option>Есть частично</option>
                    <option>Пока нет</option>
                  </select>
                </label>
                <button type="button" className="landing-button" onClick={nextQuizStep}>К контактам</button>
              </div>

              <div className={quizStep === 2 ? "quiz-step quiz-step--active" : "quiz-step"}>
                <label className="landing-field">
                  <span>Интересный формат</span>
                  <select name="format" required>
                    <option value="">Выберите формат</option>
                    <option>Демо</option>
                    <option>Пилот на 1 сценарий</option>
                    <option>Тренажер для онбординга</option>
                    <option>Регулярная тренировка команды</option>
                    <option>Пока хочу понять возможности</option>
                  </select>
                </label>
                <div className="landing-form__grid">
                  <label className="landing-field"><span>Имя</span><input name="quiz_name" required /></label>
                  <label className="landing-field"><span>Email</span><input name="quiz_email" type="email" required /></label>
                  <label className="landing-field"><span>Телефон</span><input name="quiz_phone" type="tel" required /></label>
                  <label className="landing-field"><span>Компания</span><input name="quiz_company" required /></label>
                </div>
                <label className="landing-checkbox">
                  <input type="checkbox" checked={quizConsent} onChange={(event) => setQuizConsent(event.target.checked)} />
                  <span>Согласен на обработку персональных данных</span>
                </label>
                <button type="submit" className="landing-button" disabled={!quizConsent || quizStatus === "submitting"}>
                  {quizStatus === "submitting" ? "Отправляем..." : "Получить результат"}
                </button>
              </div>
              {quizStatus === "success" ? <p className="form-status form-status--success">Похоже, вам подойдет пилот с 1-2 сценариями и картой оценки менеджеров. Мы свяжемся, чтобы уточнить вводные.</p> : null}
              {quizStatus === "error" ? <p className="form-status form-status--error">Проверьте обязательные поля и согласие на обработку данных.</p> : null}
            </form>
          </div>
        </section>

        <section className="landing-section" id="pilot">
          <div className="landing-container launch-grid">
            {["Демо", "Пилот", "Регулярная практика"].map((title, index) => (
              <article className="launch-card" key={title}>
                <h3>{title}</h3>
                <p>
                  {[
                    "Показываем механику тренировки, кабинет и структуру оценки на демонстрационном сценарии.",
                    "Собираем один рабочий сценарий под ваш продукт и проверяем формат на небольшой группе.",
                    "Расширяем набор сценариев и используем тренажер для онбординга, аттестации или регулярной практики.",
                  ][index]}
                </p>
                <button type="button" className="landing-link-button" onClick={() => scrollToBlock("lead", "pilot_cta_click")}>
                  Обсудить
                </button>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section lead-section" id="lead">
          <div className="landing-container landing-two-col">
            <div>
              <span className="section-kicker">Заявка</span>
              <h2>Обсудим демонстрацию или пилот</h2>
              <p>Опишите команду и текущую задачу. Мы вернемся с вопросами по сценарию, материалам и формату запуска.</p>
            </div>
            <form className="landing-form" onSubmit={handleLeadSubmit}>
              <div className="landing-form__grid">
                <label className="landing-field"><span>Имя</span><input name="name" required /></label>
                <label className="landing-field"><span>Рабочий email</span><input name="email" type="email" required /></label>
                <label className="landing-field"><span>Телефон</span><input name="phone" type="tel" required /></label>
                <label className="landing-field"><span>Компания</span><input name="company" required /></label>
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
                <textarea name="comment" rows={4} placeholder="Например: хотим пилот для онбординга новых менеджеров" />
              </label>
              <label className="landing-checkbox">
                <input type="checkbox" checked={leadConsent} onChange={(event) => setLeadConsent(event.target.checked)} />
                <span>Согласен на обработку персональных данных</span>
              </label>
              <label className="landing-checkbox">
                <input type="checkbox" name="marketing_consent" />
                <span>Согласен получать информационные материалы</span>
              </label>
              <p className="legal-note">
                Нажимая кнопку, вы соглашаетесь с обработкой данных. Ссылки на политику и пользовательское соглашение
                будут заменены перед публикацией.
              </p>
              <button type="submit" className="landing-button landing-button--large" disabled={!leadConsent || leadStatus === "submitting"}>
                {leadStatus === "submitting" ? "Отправляем..." : "Оставить заявку"}
              </button>
              {leadStatus === "success" ? <p className="form-status form-status--success">Заявка принята. Мы свяжемся, чтобы уточнить вводные для демонстрации.</p> : null}
              {leadStatus === "error" ? <p className="form-status form-status--error">Не удалось отправить заявку. Проверьте поля или попробуйте позже.</p> : null}
            </form>
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-container faq-list">
            <div className="section-heading">
              <span className="section-kicker">FAQ</span>
              <h2>Коротко о внедрении</h2>
            </div>
            {faqItems.map((item, index) => (
              <article className="faq-item" key={item.question}>
                <button
                  type="button"
                  aria-expanded={faqOpen === index}
                  onClick={() => {
                    setFaqOpen(faqOpen === index ? null : index);
                    track("faq_open", { question: item.question });
                  }}
                >
                  <span>{item.question}</span>
                  <strong>{faqOpen === index ? "-" : "+"}</strong>
                </button>
                {faqOpen === index ? <p>{item.answer}</p> : null}
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="landing-container landing-footer__grid">
          <div>
            <strong>Sales Trainer</strong>
            <p>AI-тренажер для онбординга, аттестации и регулярной практики отдела продаж.</p>
          </div>
          <div>
            <a href="/login" onClick={() => track("login_click")}>Личный кабинет</a>
            <a href="#lead">Оставить заявку</a>
            <a href="#quiz">Пройти квиз</a>
          </div>
          <div className="legal-note">
            <p>Реквизиты юрлица / ИП: placeholder.</p>
            <p>Политика обработки персональных данных: placeholder.</p>
            <p>Cookie и аналитика: placeholder без ID счетчика.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
