type SessionHeaderProps = {
  busy: boolean;
  canFinish: boolean;
  onNewSession: () => void;
  onFinish: () => void;
  onLogout: () => void;
  canShowReport?: boolean;
  onOpenReport?: () => void;
};

export function SessionHeader({
  busy,
  canFinish,
  onNewSession,
  onFinish,
  onLogout,
  canShowReport = false,
  onOpenReport,
}: SessionHeaderProps) {
  /** Render trainer session controls in a stable desktop-friendly order. */
  return (
    <header className="session-header">
      <div className="session-header__actions">
        {canShowReport && onOpenReport ? (
          <button
            type="button"
            className="secondary-button session-header__report-button"
            onClick={onOpenReport}
            disabled={busy}
            aria-label="Открыть итоговый отчёт"
            title="Открыть итоговый отчёт"
          >
            Отчёт
          </button>
        ) : null}
        <button type="button" className="secondary-button" onClick={onNewSession} disabled={busy}>
          Новая тренировка
        </button>
        <button type="button" className="primary-button" onClick={onFinish} disabled={busy || !canFinish}>
          Завершить
        </button>
        <button type="button" className="secondary-button" onClick={onLogout} disabled={busy}>
          Выйти
        </button>
      </div>
    </header>
  );
}
