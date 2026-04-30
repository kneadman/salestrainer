import { useEffect, useMemo, useState } from "react";
import { ApiError, createSession, finishSession, getReport, getSession, sendMessage } from "./api";
import { ChatWindow } from "./components/ChatWindow";
import { Composer } from "./components/Composer";
import { FactsPanel } from "./components/FactsPanel";
import { MetricsPanel } from "./components/MetricsPanel";
import { PhoneShell } from "./components/PhoneShell";
import { SessionHeader } from "./components/SessionHeader";
import type { SessionPublicDTO, TurnPublicDTO } from "./types";

const STORAGE_KEY = "salestrainer.currentSessionId";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Произошла непредвиденная ошибка.";
}

export default function App() {
  const [session, setSession] = useState<SessionPublicDTO | null>(null);
  const [turns, setTurns] = useState<TurnPublicDTO[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [busyAction, setBusyAction] = useState<"boot" | "create" | "send" | "finish" | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);

  useEffect(() => {
    const restore = async () => {
      const sessionId = localStorage.getItem(STORAGE_KEY);
      if (!sessionId) {
        setBootstrapping(false);
        return;
      }

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
        setBootstrapping(false);
      }
    };

    void restore();
  }, []);

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

  if (bootstrapping) {
    return <div className="app-shell">Загрузка сессии...</div>;
  }

  if (!session) {
    return (
      <div className="app-shell">
        <div className="welcome-card">
          <span className="welcome-card__eyebrow">Sales Trainer</span>
          <h1>Начните тренировку.</h1>
          <p>Клиент скрыт — выясните роль, боль и критерии через вопросы.</p>
          {error ? <div className="error-banner">{error}</div> : null}
          <button
            type="button"
            className="primary-button primary-button--large"
            onClick={startNewSession}
            disabled={loading}
          >
            Начать тренировку
          </button>
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
                <h2>Итоговый отчёт</h2>
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
