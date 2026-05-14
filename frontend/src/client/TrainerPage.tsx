import { useEffect, useMemo, useState } from "react";
import { ApiError, createSession, finishSession, getReport, getSession, sendMessage, transcribeSpeech } from "../api";
import { ChatWindow } from "../components/ChatWindow";
import { Composer } from "../components/Composer";
import { SessionHeader } from "../components/SessionHeader";
import { TrainerContextPanel } from "../components/TrainerContextPanel";
import { TrainerStartScreen } from "../components/TrainerStartScreen";
import { TrainingReportModal } from "../components/TrainingReportModal";
import type { ReportPayload, SessionPublicDTO, TurnPublicDTO } from "../types";
import type { TrainingConfigOptionDTO } from "./types";
import { getTrainingConfigs } from "./api";
import {
  clearStoredTrainerSessionId,
  getStoredTrainerSessionId,
  storeTrainerSessionId,
} from "./trainerSessionStorage";
import { getClientErrorMessage } from "./utils";

type PendingMessageSubmission = {
  idempotencyKey: string;
  managerMessage: string;
};

type TrainerPageProps = {
  userId: string;
};

export function TrainerPage({ userId }: TrainerPageProps) {
  /** Keep the runtime trainer flow inside the client cabinet and restore the last session when possible. */
  const [session, setSession] = useState<SessionPublicDTO | null>(null);
  const [turns, setTurns] = useState<TurnPublicDTO[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [busyAction, setBusyAction] = useState<"boot" | "create" | "send" | "finish" | null>("boot");
  const [error, setError] = useState<string | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [reportPayload, setReportPayload] = useState<ReportPayload | null>(null);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [pendingMessageSubmission, setPendingMessageSubmission] = useState<PendingMessageSubmission | null>(null);
  const [trainingConfigs, setTrainingConfigs] = useState<TrainingConfigOptionDTO[]>([]);
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);

  useEffect(() => {
    /** Restore the last runtime session id from localStorage for continuity across page reloads. */
    const restore = async () => {
      const sessionId = getStoredTrainerSessionId(userId);
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
          clearStoredTrainerSessionId(userId);
        } else {
          setError(getClientErrorMessage(restoreError));
        }
      } finally {
        setBusyAction(null);
      }
    };

    void restore();
  }, [userId]);

  useEffect(() => {
    /** Load available training configs for pre-training selection. */
    const loadConfigs = async () => {
      try {
        const configs = await getTrainingConfigs();
        setTrainingConfigs(configs);
        const defaultConfig = configs.find((c) => c.is_default);
        if (defaultConfig) {
          setSelectedConfigId(defaultConfig.id);
        } else if (configs.length > 0) {
          setSelectedConfigId(configs[0].id);
        }
      } catch {
        setError("Настройки тренировки недоступны. Обновите страницу или обратитесь к администратору.");
        setTrainingConfigs([]);
      }
    };
    void loadConfigs();
  }, []);

  const loading = busyAction !== null;
  const isSending = busyAction === "send";
  const canSend = session?.status === "active" && !loading;
  const voiceDisabled = !session || session.status !== "active" || loading;
  const factsState = useMemo(() => session?.client_state_public ?? {}, [session]);
  const canShowReportButton = session?.status === "finished" && (report !== null || reportPayload !== null);
  const activeConfigName = useMemo(() => {
    if (!session?.training_config_id) return undefined;
    return trainingConfigs.find((c) => c.id === session.training_config_id)?.name;
  }, [session?.training_config_id, trainingConfigs]);

  const startNewSession = async () => {
    /** Start a new runtime session and clear finished-session UI state before the request. */
    if (!selectedConfigId) {
      setError("Выберите сценарий перед началом тренировки.");
      return;
    }
    setBusyAction("create");
    setError(null);
    setVoiceError(null);
    setReport(null);
    setReportPayload(null);
    setReportModalOpen(false);
    setPendingMessageSubmission(null);
    setTurns([]);
    setInputValue("");

    try {
      const response = await createSession(selectedConfigId);
      setSession(response.session);
      storeTrainerSessionId(userId, response.session.session_id);
    } catch (startError) {
      setError(getClientErrorMessage(startError));
      setSession(null);
      clearStoredTrainerSessionId(userId);
    } finally {
      setBusyAction(null);
    }
  };

  const handleSend = async () => {
    /** Send one manager message to the active session and update the public-safe runtime state. */
    if (!session || !inputValue.trim() || loading || session.status !== "active") {
      return;
    }

    const message = inputValue.trim();
    const idempotencyKey =
      pendingMessageSubmission?.managerMessage === message
        ? pendingMessageSubmission.idempotencyKey
        : createMessageIdempotencyKey();
    setInputValue("");
    setBusyAction("send");
    setError(null);
    setVoiceError(null);
    setPendingMessageSubmission({
      idempotencyKey,
      managerMessage: message,
    });

    try {
      const response = await sendMessage(session.session_id, message, idempotencyKey);
      setSession(response.session);
      setTurns(response.turns);
      setPendingMessageSubmission(null);
    } catch (sendError) {
      setInputValue(message);
      setError(getClientErrorMessage(sendError));
    } finally {
      setBusyAction(null);
    }
  };

  const handleTranscribeAudio = async (audio: Blob) => {
    /** Upload one recorded batch for STT and append the recognized text to the textarea. */
    if (!session || session.status !== "active") {
      return;
    }

    setVoiceError(null);
    const response = await transcribeSpeech(audio, session.session_id);

    if (!response.text.trim()) {
      return;
    }

    setInputValue((currentValue) => appendTranscribedText(currentValue, response.text));
  };

  const handleFinish = async () => {
    /** Finish the active session and reopen the saved report modal as soon as the response arrives. */
    if (!session || loading || session.status !== "active") {
      return;
    }

    setBusyAction("finish");
    setError(null);
    setVoiceError(null);

    try {
      const response = await finishSession(session.session_id);
      setSession(response.session);
      setReport(response.report);
      setReportPayload(response.report_payload ?? null);
      setReportModalOpen(true);
    } catch (finishError) {
      setError(getClientErrorMessage(finishError));
    } finally {
      setBusyAction(null);
    }
  };

  if (busyAction === "boot") {
    return <div className="client-state"><strong>Загрузка тренажёра</strong></div>;
  }

  if (!session) {
    return (
      <TrainerStartScreen
        kicker="Тренажёр"
        title="Начните тренировку продаж"
        description="Отрабатывайте discovery-first продажи: роль, текущий процесс, боли, ограничения, критерии решения и следующий шаг."
        hint="Тренировка создаст новую симуляцию клиента и откроет рабочий диалог."
        buttonLabel="Начать тренировку"
        onStart={startNewSession}
        disabled={loading || trainingConfigs.length === 0}
        variant="runtime"
        error={error}
      >
        {trainingConfigs.length > 0 ? (
          <div className="trainer-config-select">
            <label>
              <span>Сценарий</span>
              <select
                value={selectedConfigId ?? ""}
                onChange={(event) => setSelectedConfigId(event.target.value || null)}
              >
                {trainingConfigs.map((config) => (
                  <option key={config.id} value={config.id}>{config.name}</option>
                ))}
              </select>
            </label>
          </div>
        ) : null}
      </TrainerStartScreen>
    );
  }

  return (
    <>
      <main className="client-trainer-layout">
        <aside className="trainer-side-panels trainer-side-panels--desktop" aria-label="Метрики и факты тренировки">
          <TrainerContextPanel session={session} factsState={factsState} mode="desktop" trainingConfigName={activeConfigName} />
        </aside>
        <section className="trainer-chat-area" aria-label="Диалог тренировки">
          <section className="trainer-chat-panel">
            <SessionHeader
              busy={loading}
              canFinish={session.status === "active"}
              canShowReport={Boolean(canShowReportButton)}
              onNewSession={startNewSession}
              onOpenReport={() => setReportModalOpen(true)}
              onFinish={handleFinish}
            />
            <div className="trainer-context-slot trainer-context-slot--mobile">
              <TrainerContextPanel session={session} factsState={factsState} mode="mobile" trainingConfigName={activeConfigName} />
            </div>
            <div className="trainer-chat-body">
              {error ? <div className="error-banner error-banner--inline">{error}</div> : null}
              <ChatWindow turns={turns} loading={isSending} publicBrief={session.public_brief} />
            </div>
            <Composer
              value={inputValue}
              onChange={(nextValue) => {
                setInputValue(nextValue);
                if (
                  pendingMessageSubmission !== null
                  && nextValue.trim() !== pendingMessageSubmission.managerMessage
                ) {
                  setPendingMessageSubmission(null);
                }
              }}
              onSend={handleSend}
              disabled={!canSend}
              loading={isSending}
              onTranscribeAudio={async (audio) => {
                try {
                  await handleTranscribeAudio(audio);
                } catch (transcriptionError) {
                  const message = getClientErrorMessage(transcriptionError);
                  setVoiceError(message);
                  throw new Error(message);
                }
              }}
              voiceDisabled={voiceDisabled}
              voiceError={voiceError}
            />
          </section>
        </section>
      </main>
      <TrainingReportModal
        open={reportModalOpen}
        report={report}
        reportPayload={reportPayload}
        onClose={() => setReportModalOpen(false)}
      />
    </>
  );
}

function createMessageIdempotencyKey(): string {
  /** Generate a stable per-send idempotency key with a timestamp fallback for older runtimes. */
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function appendTranscribedText(currentValue: string, transcribedText: string): string {
  const trimmedTranscript = transcribedText.trim();
  if (!trimmedTranscript) {
    return currentValue;
  }
  if (!currentValue.trim()) {
    return trimmedTranscript;
  }
  if (currentValue.endsWith(" ") || currentValue.endsWith("\n")) {
    return `${currentValue}${trimmedTranscript}`;
  }
  return `${currentValue} ${trimmedTranscript}`;
}
