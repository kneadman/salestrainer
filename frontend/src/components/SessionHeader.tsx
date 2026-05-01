type SessionHeaderProps = {
  busy: boolean;
  canFinish: boolean;
  onNewSession: () => void;
  onFinish: () => void;
  onLogout: () => void;
};

export function SessionHeader({ busy, canFinish, onNewSession, onFinish, onLogout }: SessionHeaderProps) {
  return (
    <header className="session-header">
      <div className="session-header__actions">
        <button type="button" className="secondary-button" onClick={onNewSession} disabled={busy}>
          New session
        </button>
        <button type="button" className="primary-button" onClick={onFinish} disabled={busy || !canFinish}>
          Finish
        </button>
        <button type="button" className="secondary-button" onClick={onLogout} disabled={busy}>
          Logout
        </button>
      </div>
    </header>
  );
}
