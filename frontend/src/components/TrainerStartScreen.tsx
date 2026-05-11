type TrainerStartScreenProps = {
  kicker?: string;
  title: string;
  description: string;
  hint?: string;
  buttonLabel: string;
  onStart: () => void;
  disabled?: boolean;
  error?: string | null;
  variant?: "runtime" | "demo";
};

export function TrainerStartScreen({
  kicker = "Тренажёр",
  title,
  description,
  hint,
  buttonLabel,
  onStart,
  disabled = false,
  error = null,
  variant = "runtime",
}: TrainerStartScreenProps) {
  /** Render a full-bleed, product-like start screen for training sessions. */
  return (
    <section className={`trainer-start trainer-start--${variant}`}>
      <div className="trainer-start__shell">
        <div className="trainer-start__content">
          <span className="client-kicker">{kicker}</span>
          <h1>{title}</h1>
          <p>{description}</p>

          <div className="trainer-start__features" aria-label="Возможности тренировки">
            <span className="trainer-start__feature">Discovery-first</span>
            <span className="trainer-start__feature">Метрики интереса</span>
            <span className="trainer-start__feature">Факты и боли</span>
            <span className="trainer-start__feature">Итоговый отчёт</span>
          </div>

          {error ? <div className="client-alert client-alert--error">{error}</div> : null}

          <div className="trainer-start__actions">
            <button
              type="button"
              className="client-button client-button--primary trainer-start__button"
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
          <ol className="trainer-start__steps">
            <li>Начните диалог</li>
            <li>Выявите роль и полномочия</li>
            <li>Найдите боли и критерии</li>
            <li>Завершите следующим шагом</li>
          </ol>
        </aside>
      </div>
    </section>
  );
}
