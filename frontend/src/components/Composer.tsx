import { useRef } from "react";
import type { KeyboardEvent } from "react";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";

type ComposerProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  disabled: boolean;
  loading: boolean;
  onTranscribeAudio?: (audio: Blob) => Promise<void>;
  voiceDisabled?: boolean;
  voiceLoading?: boolean;
  voiceError?: string | null;
};

export function Composer({
  value,
  onChange,
  onSend,
  disabled,
  loading,
  onTranscribeAudio,
  voiceDisabled = false,
  voiceLoading = false,
  voiceError = null,
}: ComposerProps) {
  const ignoreNextClickRef = useRef(false);
  const holdRecordingRef = useRef(false);
  const {
    state: voiceState,
    elapsedSeconds,
    isSupported,
    error: recorderError,
    startRecording,
    stopRecording,
    toggleRecording,
    clearError,
  } = useVoiceRecorder({
    enabled: !voiceDisabled && !!onTranscribeAudio,
    onTranscribeAudio: async (audio) => {
      if (!onTranscribeAudio) {
        return;
      }
      await onTranscribeAudio(audio);
    },
  });

  const isVoiceRecording = voiceState === "recording";
  const isVoiceTranscribing = voiceLoading || voiceState === "transcribing";
  const composerDisabled = disabled || isVoiceTranscribing;
  const inlineVoiceError = voiceError ?? recorderError;

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!composerDisabled && value.trim()) {
        onSend();
      }
    }
  };

  const handlePointerDown = async (pointerType: string) => {
    clearError();
    if (pointerType === "mouse" || voiceDisabled || !onTranscribeAudio) {
      holdRecordingRef.current = false;
      return;
    }
    holdRecordingRef.current = true;
    await startRecording();
  };

  const handlePointerStop = async () => {
    if (!holdRecordingRef.current) {
      return;
    }
    holdRecordingRef.current = false;
    ignoreNextClickRef.current = true;
    await stopRecording();
  };

  const handleVoiceClick = async () => {
    if (ignoreNextClickRef.current) {
      ignoreNextClickRef.current = false;
      return;
    }
    clearError();
    await toggleRecording();
  };

  return (
    <div className="composer">
      <textarea
        className="composer__input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Введите сообщение клиенту"
        rows={1}
        disabled={composerDisabled}
      />
      <button
        type="button"
        className={`composer__voice ${isVoiceRecording ? "composer__voice--recording" : ""}`}
        onClick={() => void handleVoiceClick()}
        onPointerDown={(event) => void handlePointerDown(event.pointerType)}
        onPointerUp={() => void handlePointerStop()}
        onPointerCancel={() => void handlePointerStop()}
        aria-label={isVoiceRecording ? "Остановить запись" : "Начать голосовой ввод"}
        title={isVoiceRecording ? "Остановить запись" : "Начать голосовой ввод"}
        disabled={voiceDisabled || !onTranscribeAudio || !isSupported || isVoiceTranscribing}
      >
        <span className="composer__voice-icon" aria-hidden="true">
          {isVoiceRecording ? "Стоп" : "Мик"}
        </span>
        {isVoiceRecording ? <span className="composer__voice-timer">{formatElapsedSeconds(elapsedSeconds)}</span> : null}
        {isVoiceTranscribing ? <span className="composer__voice-label">Распознаём...</span> : null}
      </button>
      <button type="button" className="composer__send" onClick={onSend} disabled={composerDisabled || !value.trim()}>
        {loading ? "..." : "Отправить"}
      </button>
      {inlineVoiceError ? <div className="composer__error">{inlineVoiceError}</div> : null}
      {!isSupported && onTranscribeAudio ? (
        <div className="composer__hint">Голосовой ввод не поддерживается в этом браузере.</div>
      ) : null}
    </div>
  );
}

function formatElapsedSeconds(value: number): string {
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
