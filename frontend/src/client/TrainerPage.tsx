import { useEffect, useMemo, useState } from "react";
import { ApiError, createSession, finishSession, getReport, getSession, sendMessage } from "../api";
import { ChatWindow } from "../components/ChatWindow";
import { Composer } from "../components/Composer";
import { FactsPanel } from "../components/FactsPanel";
import { MetricsPanel } from "../components/MetricsPanel";
import { PhoneShell } from "../components/PhoneShell";
import { SessionHeader } from "../components/SessionHeader";
import { StructuredReportSummary } from "../components/StructuredReportSummary";
import type { SessionPublicDTO, TurnPublicDTO } from "../types";
import { getClientErrorMessage } from "./utils";

const STORAGE_KEY = "salestrainer.currentSessionId";

type TrainerPageProps = {
  onLogout: () => Promise<void>;
};

export function TrainerPage({ onLogout }: TrainerPageProps) {
  /** Preserve the existing runtime trainer flow inside the /app/trainer route. */
  const [session, setSession] = useState<SessionPublicDTO | null>(null);
  const [turns, setTurns] = useState<TurnPublicDTO[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [busyAction, setBusyAction] = useState<"boot" | "create" | "send" | "finish" | null>("boot");
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [reportPayload, setReportPayload] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    /** Restore the last runtime session id from localStorage for continuity. */
    const restore = async () => {
      const sessionId = localStorage.getItem(STORAGE_KEY);
      if (!sessionId) {
        setBusyAction(null);
        return;
      }
      try {
        const detail = await getSession(sessionId);
        setSession(detail.session);
        setTurns(detail.turns);
        if (detail.session.status === "finished") {
          try {
            const reportResponse = await getReport(sessionId);
            setReport(reportResponse.report);
            setReportPayload(reportResponse.report_payload ?? null);
          } catch {
            setReport(null);
            setReportPayload(null);
          }
        }
      } catch (restoreError) {
        if (restoreError instanceof ApiError && restoreError.code === "not_found") {
          localStorage.removeItem(STORAGE_KEY);
        } else {
          setError(getClientErrorMessage(restoreError));
        }
      } finally {
        setBusyAction(null);
      }
    };
    void restore();
  }, []);

  const loading = busyAction !== null;
  const isSending = busyAction === "send";
  const canSend = session?.status === "active" && !loading;
  const factsState = useMemo(() => session?.client_state_public ?? {}, [session]);

  const startNewSession = async () => {
    /** Start a new Redis-backed training session through the existing API. */
    setBusyAction("create");
    setError(null);
    setReport(null);
    setReportPayload(null);
    setTurns([]);
    setInputValue("");
    try {
      const response = await createSession();
      setSession(response.session);
      localStorage.setItem(STORAGE_KEY, response.session.session_id);
    } catch (startError) {
      setError(getClientErrorMessage(startError));
      setSession(null);
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setBusyAction(null);
    }
  };

  const handleSend = async () => {
    /** Send one manager message and update the public runtime state. */
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
      setError(getClientErrorMessage(sendError));
    } finally {
      setBusyAction(null);
    }
  };

  const handleFinish = async () => {
    /** Finish the active session and render its report. */
    if (!session || loading || session.status !== "active") {
      return;
    }
    setBusyAction("finish");
    setError(null);
    try {
      const response = await finishSession(session.session_id);
      setSession(response.session);
      setReport(response.report);
      setReportPayload(response.report_payload ?? null);
    } catch (finishError) {
      setError(getClientErrorMessage(finishError));
    } finally {
      setBusyAction(null);
    }
  };

  if (busyAction === "boot") {
    return <div className="client-state"><strong>Загрузка тренажера</strong></div>;
  }

  if (!session) {
    return (
      <section className="client-welcome">
        <span className="client-kicker">Тренажер</span>
        <h1>Начните тренировку</h1>
        <p>Отрабатывайте discovery-first продажи: роль, боль, ограничения, критерии решения и следующий шаг.</p>
        {error ? <div className="client-alert client-alert--error">{error}</div> : null}
        <button type="button" className="client-button client-button--primary" onClick={startNewSession} disabled={loading}>
          Начать тренировку
        </button>
      </section>
    );
  }

  return (
    <main className="layout client-trainer-layout">
      <div className="side-panels">
        <MetricsPanel session={session} />
        <FactsPanel state={factsState} />
        {report ? (
          <section className="panel-card">
            <div className="panel-card__header"><h2>Итоговый отчёт</h2></div>
            <StructuredReportSummary payload={reportPayload} />
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
          onLogout={onLogout}
        />
        {error ? <div className="error-banner error-banner--inline">{error}</div> : null}
        <ChatWindow turns={turns} loading={isSending} publicBrief={session.public_brief} />
        <Composer value={inputValue} onChange={setInputValue} onSend={handleSend} disabled={!canSend} loading={isSending} />
      </PhoneShell>
    </main>
  );
}
