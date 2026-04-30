type SessionHeaderProps = {
  busy: boolean;
  canFinish: boolean;
  onNewSession: () => void;
  onFinish: () => void;
};

export function SessionHeader({ busy, canFinish, onNewSession, onFinish }: SessionHeaderProps) {
  return (
    <header className="session-header">
      <div className="session-header__actions">
        <button type="button" className="secondary-button" onClick={onNewSession} disabled={busy}>
          Новая сессия
        </button>
        <button type="button" className="primary-button" onClick={onFinish} disabled={busy || !canFinish}>
          Завершить
        </button>
      </div>
    </header>
  );
}
