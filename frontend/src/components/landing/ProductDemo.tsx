import { useEffect, useMemo, useRef, useState } from "react";

type DemoStep = "chat" | "scoring" | "report";
type DemoVariant = "hero" | "presentation" | "interactive";

type DemoMessage = {
  speaker: "client" | "manager" | "signal";
  text: string;
};

type ProductDemoProps = {
  variant?: DemoVariant;
};

const demoMessages: DemoMessage[] = [
  { speaker: "client", text: "Сейчас у нас всё держится на менеджерах. Чем вы отличаетесь от обычного обучения?" },
  { speaker: "manager", text: "Менеджер проходит живой разговор с тренажёром и получает разбор по конкретным моментам диалога." },
  { speaker: "client", text: "Если он знает скрипт, этого разве мало?" },
  { speaker: "signal", text: "Выявлена проблема: нет контроля качества разговора в момент сопротивления клиента." },
  { speaker: "manager", text: "Скрипт не показывает, как менеджер ведёт себя под давлением. Здесь видно, где он теряет вопрос, боль или следующий шаг." },
];

const scoringRows = [
  ["Понял задачу клиента", 78],
  ["Удержал возражение", 64],
  ["Выяснил, кто принимает решение", 71],
  ["Зафиксировал проблему", 82],
  ["Договорился о продолжении", 58],
] as const;

const reportCards = [
  ["Сильная сторона", "Менеджер связал предложение с текущим процессом клиента и не ушёл сразу в презентацию.", "positive"],
  ["Риск потери", "После сомнения про обучение не уточнил критерии выбора и почти ушёл в общий рассказ.", "risk"],
  ["Что не выяснено", "Кто ещё участвует в выборе и как компания оценивает качество разговора сейчас.", "neutral"],
  ["Сигнал для руководителя", "Похожее сопротивление команда может проходить одинаково слабо и не вскрывать процесс клиента.", "risk"],
  ["Что тренировать дальше", "Уточнение критериев выбора и фиксация следующего шага после сопротивления.", "positive"],
] as const;

function useReducedMotionPreference(): boolean {
  /** Mirror the OS reduced-motion preference so the demo can fall back to a static view. */
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    /** Subscribe once to motion-preference changes for accessibility-safe animation behavior. */
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncPreference = () => setReducedMotion(mediaQuery.matches);
    syncPreference();
    mediaQuery.addEventListener("change", syncPreference);
    return () => mediaQuery.removeEventListener("change", syncPreference);
  }, []);

  return reducedMotion;
}

export function ProductDemo({ variant = "interactive" }: ProductDemoProps) {
  /** Animate the public product story from dialogue to analysis without any API dependency. */
  const reducedMotion = useReducedMotionPreference();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const isHero = variant === "hero";
  const isPresentation = variant === "presentation";
  const [activeStep, setActiveStep] = useState<DemoStep>(reducedMotion ? "report" : "chat");
  const [enteredViewport, setEnteredViewport] = useState(reducedMotion || isPresentation || isHero);
  const [visibleMessageCount, setVisibleMessageCount] = useState(reducedMotion ? demoMessages.length : 1);
  const [cycleKey, setCycleKey] = useState(0);

  useEffect(() => {
    /** Keep reduced-motion mode static and fully readable from the first paint. */
    if (!reducedMotion) {
      return;
    }

    setEnteredViewport(true);
    setActiveStep("report");
    setVisibleMessageCount(demoMessages.length);
  }, [reducedMotion]);

  useEffect(() => {
    /** Start the interactive demo only after the block has entered the viewport. */
    if (reducedMotion || isPresentation) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setEnteredViewport(true);
        }
      },
      { threshold: 0.35 },
    );

    if (rootRef.current) {
      observer.observe(rootRef.current);
    }

    return () => observer.disconnect();
  }, [isPresentation, reducedMotion]);

  useEffect(() => {
    /** Drive either the hero loop or the viewport-triggered walkthrough sequence. */
    if (reducedMotion || !enteredViewport) {
      return;
    }

    const messageInterval = isPresentation ? 380 : isHero ? 440 : 480;
    const scoringDelay = isPresentation ? 220 : isHero ? 420 : 240;
    const reportDelay = isPresentation ? 1240 : isHero ? 3200 : 1760;
    const loopDelay = isPresentation || isHero ? 2100 : 0;

    setActiveStep("chat");
    setVisibleMessageCount(1);

    const revealTimers = demoMessages.slice(1).map((_, index) =>
      window.setTimeout(() => {
        setVisibleMessageCount(index + 2);
      }, messageInterval * (index + 1)),
    );
    const scoringTimer = isHero
      ? null
      : window.setTimeout(
          () => setActiveStep("scoring"),
          messageInterval * demoMessages.length + scoringDelay,
        );
    const reportTimer = isHero
      ? null
      : window.setTimeout(
          () => setActiveStep("report"),
          messageInterval * demoMessages.length + reportDelay,
        );
    const loopTimer = isPresentation || isHero
      ? window.setTimeout(
          () => setCycleKey((current) => current + 1),
          messageInterval * demoMessages.length + reportDelay + loopDelay,
        )
      : null;

    return () => {
      revealTimers.forEach((timer) => window.clearTimeout(timer));
      if (scoringTimer !== null) {
        window.clearTimeout(scoringTimer);
      }
      if (reportTimer !== null) {
        window.clearTimeout(reportTimer);
      }
      if (loopTimer !== null) {
        window.clearTimeout(loopTimer);
      }
    };
  }, [cycleKey, enteredViewport, isHero, isPresentation, reducedMotion]);

  const visibleMessages = useMemo(() => {
    /** Reveal more of the conversation as the viewer moves through the demo phases. */
    if (reducedMotion || activeStep !== "chat") {
      return demoMessages;
    }
    return demoMessages.slice(0, visibleMessageCount);
  }, [activeStep, reducedMotion, visibleMessageCount]);

  return (
    <div
      ref={rootRef}
      className={[
        "lp-demo",
        reducedMotion ? "lp-demo--static" : "",
        isHero ? "lp-demo--hero" : "",
        isPresentation ? "lp-demo--presentation" : "lp-demo--interactive",
      ].filter(Boolean).join(" ")}
      data-variant={variant}
      data-step={activeStep}
      data-testid="landing-demo"
    >
      {isPresentation ? (
        <div className="lp-demo__stage-strip" aria-label="Этапы демонстрации продукта">
          {(["chat", "scoring", "report"] as const).map((step) => (
            <span
              key={step}
              className={activeStep === step ? "lp-demo__stage lp-demo__stage--active" : "lp-demo__stage"}
            >
              {step === "chat" ? "Разговор" : step === "scoring" ? "Оценка" : "Выводы"}
            </span>
          ))}
        </div>
      ) : null}

      {!isPresentation && !isHero ? (
        <div className="lp-demo__nav" aria-label="Фазы демонстрации">
          {(["chat", "scoring", "report"] as const).map((step) => (
            <button
              key={step}
              type="button"
              className={activeStep === step ? "lp-demo__phase lp-demo__phase--active" : "lp-demo__phase"}
              aria-pressed={activeStep === step}
              onClick={() => setActiveStep(step)}
            >
              {step === "chat" ? "Разговор" : step === "scoring" ? "Оценка" : "Выводы"}
            </button>
          ))}
        </div>
      ) : null}

      <div className="lp-demo__grid">
        <section className={activeStep === "chat" ? "lp-demo-card lp-demo-card--active" : "lp-demo-card"} aria-label="Демо-чат">
          <header className="lp-demo-card__header">
            <span>{isHero ? "Тренировка" : "Диалог"}</span>
            <strong>Живой разговор</strong>
          </header>
          <div className="lp-demo-chat">
            {visibleMessages.map((message, index) => (
              <article
                key={message.text}
                className={`lp-demo-message lp-demo-message--${message.speaker} ${reducedMotion ? "lp-demo-message--visible" : ""}`}
                style={reducedMotion ? undefined : { animationDelay: `${index * 100}ms` }}
              >
                {message.text}
              </article>
            ))}
          </div>
        </section>

        {!isHero ? (
          <section className={activeStep === "scoring" ? "lp-demo-card lp-demo-card--active" : "lp-demo-card"} aria-label="Демо-оценка">
            <header className="lp-demo-card__header">
              <span>После разговора</span>
              <strong>Оценка разговора</strong>
            </header>
            <div className="lp-demo-scores">
              {scoringRows.map(([label, value]) => (
                <div key={label} className="lp-demo-score">
                  <div className="lp-demo-score__meta">
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                  <div className="lp-demo-score__track">
                    <span
                      style={{
                        width: activeStep === "chat" && !reducedMotion ? "12%" : `${value}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {!isHero ? (
          <section className={activeStep === "report" ? "lp-demo-card lp-demo-card--active" : "lp-demo-card"} aria-label="Демо-отчёт">
            <header className="lp-demo-card__header">
              <span>Для руководителя</span>
              <strong>Выводы по разговору</strong>
            </header>
            <div className="lp-demo-report">
              {reportCards.map(([title, text, tone], index) => (
                <article
                  key={title}
                  className={`lp-demo-report__tile lp-demo-report__tile--${tone}`}
                  style={activeStep === "report" && !reducedMotion ? { transitionDelay: `${index * 70}ms` } : undefined}
                >
                  <strong>{title}</strong>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
