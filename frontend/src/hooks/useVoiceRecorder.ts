import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type VoiceRecorderState = "idle" | "recording" | "transcribing" | "error";

type UseVoiceRecorderOptions = {
  enabled: boolean;
  onTranscribeAudio: (audio: Blob) => Promise<void>;
};

type UseVoiceRecorderResult = {
  state: VoiceRecorderState;
  elapsedSeconds: number;
  isSupported: boolean;
  error: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  toggleRecording: () => Promise<void>;
  clearError: () => void;
};

export function useVoiceRecorder({
  enabled,
  onTranscribeAudio,
}: UseVoiceRecorderOptions): UseVoiceRecorderResult {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const startTimeRef = useRef<number | null>(null);
  const [state, setState] = useState<VoiceRecorderState>("idle");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const isSupported = useMemo(() => {
    return typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== "undefined";
  }, []);

  const clearTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const resetRecorder = useCallback(() => {
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    startTimeRef.current = null;
    setElapsedSeconds(0);
  }, []);

  const clearError = useCallback(() => {
    if (state === "error") {
      setState("idle");
    }
    setError(null);
  }, [state]);

  const stopInternal = useCallback(async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      return;
    }
    recorder.stop();
  }, []);

  useEffect(() => {
    if (state !== "recording") {
      return;
    }
    const intervalId = window.setInterval(() => {
      if (startTimeRef.current === null) {
        return;
      }
      setElapsedSeconds(Math.max(0, Math.floor((Date.now() - startTimeRef.current) / 1000)));
    }, 250);
    return () => window.clearInterval(intervalId);
  }, [state]);

  useEffect(() => {
    if (!enabled && state === "recording") {
      void stopInternal();
    }
  }, [enabled, state, stopInternal]);

  useEffect(() => {
    return () => {
      clearTracks();
      resetRecorder();
    };
  }, [clearTracks, resetRecorder]);

  const startRecording = useCallback(async () => {
    if (!enabled || state === "recording" || state === "transcribing") {
      return;
    }
    if (!isSupported) {
      setState("error");
      setError("Голосовой ввод недоступен в этом браузере.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, _mediaRecorderOptions());
      clearError();
      streamRef.current = stream;
      chunksRef.current = [];
      startTimeRef.current = Date.now();
      setElapsedSeconds(0);
      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onerror = () => {
        setState("error");
        setError("Не удалось записать аудио.");
        clearTracks();
        resetRecorder();
      };
      recorder.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });
        clearTracks();
        resetRecorder();
        if (!audioBlob.size) {
          setState("error");
          setError("Аудио не записалось.");
          return;
        }
        setState("transcribing");
        void onTranscribeAudio(audioBlob)
          .then(() => {
            setState("idle");
          })
          .catch((recordingError: unknown) => {
            setState("error");
            setError(recordingError instanceof Error ? recordingError.message : "Не удалось распознать речь.");
          });
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setState("recording");
    } catch {
      setState("error");
      setError("Нет доступа к микрофону.");
      clearTracks();
      resetRecorder();
    }
  }, [clearError, clearTracks, enabled, isSupported, onTranscribeAudio, resetRecorder, state]);

  const stopRecording = useCallback(async () => {
    if (state !== "recording") {
      return;
    }
    await stopInternal();
  }, [state, stopInternal]);

  const toggleRecording = useCallback(async () => {
    if (state === "recording") {
      await stopRecording();
      return;
    }
    await startRecording();
  }, [startRecording, state, stopRecording]);

  return {
    state,
    elapsedSeconds,
    isSupported,
    error,
    startRecording,
    stopRecording,
    toggleRecording,
    clearError,
  };
}

function _mediaRecorderOptions(): MediaRecorderOptions | undefined {
  /** Prefer common browser containers that the backend accepts without client transcoding. */
  if (typeof MediaRecorder === "undefined" || typeof MediaRecorder.isTypeSupported !== "function") {
    return undefined;
  }
  for (const mimeType of ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"]) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return { mimeType };
    }
  }
  return undefined;
}
