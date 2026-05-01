import { useEffect, useMemo, useState } from "react";
import { ApiError, createSession, finishSession, getMe, getReport, getSession, logout as logoutRequest, sendMessage } from "./api";
import { ChatWindow } from "./components/ChatWindow";
import { Composer } from "./components/Composer";
import { FactsPanel } from "./components/FactsPanel";
import { LoginPage } from "./components/LoginPage";
import { MetricsPanel } from "./components/MetricsPanel";
import { PhoneShell } from "./components/PhoneShell";
import { SessionHeader } from "./components/SessionHeader";
import type { AuthUser, SessionPublicDTO, TurnPublicDTO } from "./types";

const STORAGE_KEY = "salestrainer.currentSessionId";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error.";
}

function getCurrentPath(): string {
  return window.location.pathname;
}

export default function App() {
  const [path, setPath] = useState(getCurrentPath);
  const [authBootstrapping, setAuthBootstrapping] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [session, setSession] = useState<SessionPublicDTO | null>(null);
  const [turns, setTurns] = useState<TurnPublicDTO[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [busyAction, setBusyAction] = useState<"boot" | "create" | "send" | "finish" | "logout" | null>(null);
  const [sessionBootstrapping, setSessionBootstrapping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);

  const navigate = (nextPath: string, replace = false) => {
    if (window.location.pathname === nextPath) {
      setPath(nextPath);
      return;
    }
    if (replace) {
      window.history.replaceState({}, "", nextPath);
    } else {
      window.history.pushState({}, "", nextPath);
    }
    setPath(nextPath);
  };

  useEffect(() => {
    const handlePopState = () => setPath(getCurrentPath());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    const bootstrapAuth = async () => {
      try {
        const response = await getMe();
        setUser(response.user);
        setAuthError(null);
      } catch (meError) {
        if (meError instanceof ApiError && meError.status === 401) {
          setUser(null);
          setAuthError(null);
        } else {
          setUser(null);
          setAuthError(getErrorMessage(meError));
        }
      } finally {
        setAuthBootstrapping(false);
      }
    };

    void bootstrapAuth();
  }, []);

  useEffect(() => {
    if (authBootstrapping) {
      return;
    }
    if (path === "/") {
      navigate(user ? "/app" : "/login", true);
      return;
    }
    if (path === "/login" && user) {
      navigate("/app", true);
      return;
    }
    if (path === "/app" && !user) {
      navigate("/login", true);
      return;
    }
    if (path !== "/login" && path !== "/app") {
      navigate(user ? "/app" : "/login", true);
    }
  }, [authBootstrapping, path, user]);

  useEffect(() => {
    if (!user || path !== "/app") {
      return;
    }

    const restore = async () => {
      const sessionId = localStorage.getItem(STORAGE_KEY);
      if (!sessionId) {
        setSessionBootstrapping(false);
        return;
      }

      setSessionBootstrapping(true);
      setBusyAction("boot");
      try {
        const detail = await getSession(sessionId);
        setSession(detail.session);
        setTurns(detail.turns);
        setError(null);

        if (detail.session.status === "finished") {
          try {
            const reportResponse = await getReport(sessionId);
            setReport(reportResponse.report);
          } catch {
            setReport(null);
          }
        }
      } catch (restoreError) {
        const message = getErrorMessage(restoreError);
        if (restoreError instanceof ApiError && restoreError.code === "not_found") {
          localStorage.removeItem(STORAGE_KEY);
        } else {
          setError(message);
        }
      } finally {
        setBusyAction(null);
        setSessionBootstrapping(false);
      }
    };

    void restore();
  }, [path, user]);

  const loading = busyAction !== null;
  const isSending = busyAction === "send";
  const canSend = session?.status === "active" && !loading;
  const factsState = useMemo(() => session?.client_state_public ?? {}, [session]);

  const startNewSession = async () => {
    setBusyAction("create");
    setError(null);
    setReport(null);
    setTurns([]);
    setInputValue("");

    try {
      const response = await createSession();
      setSession(response.session);
      localStorage.setItem(STORAGE_KEY, response.session.session_id);
    } catch (startError) {
      setError(getErrorMessage(startError));
      setSession(null);
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setBusyAction(null);
    }
  };

  const handleSend = async () => {
    if (!session || !inputValue.trim() || loading || session.status !== "active") {
      return;
    }

    const message = inputValue.trim();
    setInputValue("");
    setBusyAction("send");
    setError(null);

    try {
      const response = await sendMessage(session.session_id, message);
      setSession(response.session);
      setTurns(response.turns);
    } catch (sendError) {
      setInputValue(message);
      setError(getErrorMessage(sendError));
    } finally {
      setBusyAction(null);
    }
  };

  const handleFinish = async () => {
    if (!session || loading || session.status !== "active") {
      return;
    }

    setBusyAction("finish");
    setError(null);

    try {
      const response = await finishSession(session.session_id);
      setSession(response.session);
      setReport(response.report);
    } catch (finishError) {
      setError(getErrorMessage(finishError));
    } finally {
      setBusyAction(null);
    }
  };

  const handleAuthenticated = (authenticatedUser: AuthUser) => {
    setUser(authenticatedUser);
    setAuthError(null);
    navigate("/app", true);
  };

  const handleLogout = async () => {
    setBusyAction("logout");
    setError(null);
    try {
      await logoutRequest();
    } catch {
      // A failed logout request should not keep stale authenticated UI around.
    } finally {
      setUser(null);
      setSession(null);
      setTurns([]);
      setInputValue("");
      setReport(null);
      setBusyAction(null);
      navigate("/login", true);
    }
  };

  if (authBootstrapping || path === "/") {
    return <div className="app-shell">Loading...</div>;
  }

  if (path === "/login" || !user) {
    return (
      <>
        {authError ? (
          <div className="auth-error-strip">
            <div className="error-banner">{authError}</div>
          </div>
        ) : null}
        <LoginPage onAuthenticated={handleAuthenticated} />
      </>
    );
  }

  if (sessionBootstrapping) {
    return <div className="app-shell">Loading session...</div>;
  }

  if (!session) {
    return (
      <div className="app-shell">
        <div className="welcome-card">
          <span className="welcome-card__eyebrow">Sales Trainer</span>
          <h1>Start a training session.</h1>
          <p>Ask questions, qualify the client, and uncover the role, pain, constraints, and buying criteria.</p>
          <p className="account-line">
            {user.email} · {user.client_account.name}
          </p>
          {error ? <div className="error-banner">{error}</div> : null}
          <div className="welcome-card__actions">
            <button
              type="button"
              className="primary-button primary-button--large"
              onClick={startNewSession}
              disabled={loading}
            >
              Start training
            </button>
            <button type="button" className="secondary-button secondary-button--large" onClick={handleLogout} disabled={loading}>
              Logout
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <main className="layout">
        <div className="side-panels">
          <MetricsPanel session={session} />
          <FactsPanel state={factsState} />
          {report ? (
            <section className="panel-card">
              <div className="panel-card__header">
                <h2>Final report</h2>
              </div>
              <pre className="report-block">{report}</pre>
            </section>
          ) : null}
        </div>

        <PhoneShell>
          <SessionHeader
            busy={loading}
            canFinish={session.status === "active"}
            onNewSession={startNewSession}
            onFinish={handleFinish}
            onLogout={handleLogout}
          />
          {error ? <div className="error-banner error-banner--inline">{error}</div> : null}
          <ChatWindow turns={turns} loading={isSending} publicBrief={session.public_brief} />
          <Composer
            value={inputValue}
            onChange={setInputValue}
            onSend={handleSend}
            disabled={!canSend}
            loading={isSending}
          />
        </PhoneShell>
      </main>
    </div>
  );
}
