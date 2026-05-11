type TrainerStartScreenProps = {
  kicker?: string;
  title: string;
  description: string;
  hint?: string;
  buttonLabel: string;
  onStart: () => void;
  disabled?: boolean;
  variant?: "runtime" | "demo";
  error?: string | null;
};

export function TrainerStartScreen({
  kicker,
  title,
  description,
  hint,
  buttonLabel,
  onStart,
  disabled = false,
  variant = "runtime",
  error,
}: TrainerStartScreenProps) {
  /** Render a full-bleed, product-like start screen for training sessions. */
  return (
    <section className="trainer-start">
      <div className="trainer-start__shell">
        <div className="trainer-start__content">
          {kicker ? <span className="client-kicker">{kicker}</span> : null}
          <h1>{title}</h1>
          <p className="trainer-start__description">{description}</p>

          <div className="trainer-start__features">
            <span className="trainer-start__feature">Discovery-first</span>
            <span className="trainer-start__feature">Метрики интереса</span>
            <span className="trainer-start__feature">Факты и боли</span>
            <span className="trainer-start__feature">Итоговый отчёт</span>
          </div>

          {error ? (
            <div className="client-alert client-alert--error trainer-start__error">
              {error}
            </div>
          ) : null}

          <div className="trainer-start__actions">
            <button
              type="button"
              className={`client-button client-button--primary ${variant === "demo" ? "primary-button--large" : ""}`}
              onClick={onStart}
              disabled={disabled}
            >
              {buttonLabel}
            </button>
            {hint ? <p className="trainer-start__hint">{hint}</p> : null}
          </div>
        </div>

        <aside className="trainer-start__preview">
          <div className="trainer-start__preview-header">Что будет в тренировке</div>
          <ul className="trainer-start__steps">
            <li>Начните диалог с клиентом</li>
            <li>Выявите роль и полномочия</li>
            <li>Найдите боли и критерии</li>
            <li>Завершите следующим шагом</li>
          </ul>
        </aside>
      </div>
    </section>
  );
}
