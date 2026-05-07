import { useLayoutEffect, useRef } from "react";
import type { KeyboardEvent, SVGProps } from "react";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";

const TEXTAREA_MAX_HEIGHT = 160;

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
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
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

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "auto";
    const nextHeight = Math.min(textarea.scrollHeight, TEXTAREA_MAX_HEIGHT);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > TEXTAREA_MAX_HEIGHT ? "auto" : "hidden";
  }, [value]);

  const isVoiceRecording = voiceState === "recording";
  const isVoiceTranscribing = voiceLoading || voiceState === "transcribing";
  const composerDisabled = disabled || isVoiceTranscribing;
  const inlineVoiceError = voiceError ?? recorderError;
  const voiceButtonLabel = isVoiceRecording ? "Остановить запись" : "Голосовой ввод";

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
        ref={textareaRef}
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
        aria-label={voiceButtonLabel}
        title={voiceButtonLabel}
        disabled={voiceDisabled || !onTranscribeAudio || !isSupported || isVoiceTranscribing}
      >
        <span className="composer__voice-icon" aria-hidden="true">
          <MicrophoneIcon />
        </span>
        <span className="composer__voice-label">{isVoiceTranscribing ? "Распознаём..." : "Голос"}</span>
        {isVoiceRecording ? <span className="composer__voice-timer">{formatElapsedSeconds(elapsedSeconds)}</span> : null}
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

function MicrophoneIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 3a3 3 0 0 1 3 3v6a3 3 0 1 1-6 0V6a3 3 0 0 1 3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <path d="M12 19v3" />
      <path d="M8 22h8" />
    </svg>
  );
}

function formatElapsedSeconds(value: number): string {
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
