import type {
  AuthMeResponse,
  FinishSessionResponse,
  SessionDetailResponse,
  SessionReportResponse,
  SessionStateResponse,
  SpeechTranscriptionResponse,
  TurnResponse,
} from "./types";
import { ApiError, clearCachedCsrfToken, request } from "./apiClient";

export { ApiError };

export function login(email: string, password: string): Promise<AuthMeResponse> {
  /** Authenticate by email/password and reset stale CSRF cache. */
  clearCachedCsrfToken();
  return request<AuthMeResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  /** Revoke the current auth session and clear cached CSRF. */
  await request<void>("/auth/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
  clearCachedCsrfToken();
}

export function getMe(): Promise<AuthMeResponse> {
  /** Load the current browser-authenticated user. */
  return request<AuthMeResponse>("/auth/me");
}

export function createSession(trainingConfigId?: string): Promise<SessionStateResponse> {
  /** Create a new runtime training session for the current user. */
  return request<SessionStateResponse>("/api/sessions", {
    method: "POST",
    body: JSON.stringify(trainingConfigId ? { training_config_id: trainingConfigId } : {}),
  });
}

export function getSession(sessionId: string): Promise<SessionDetailResponse> {
  /** Load public-safe runtime session detail. */
  return request<SessionDetailResponse>(`/api/sessions/${sessionId}`);
}

export function sendMessage(sessionId: string, managerMessage: string, idempotencyKey?: string): Promise<TurnResponse> {
  /** Send one manager message to the training simulator. */
  return request<TurnResponse>(`/api/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({
      manager_message: managerMessage,
      ...(idempotencyKey ? { idempotency_key: idempotencyKey } : {}),
    }),
  });
}

export function transcribeSpeech(audio: Blob, sessionId?: string): Promise<SpeechTranscriptionResponse> {
  /** Upload one recorded audio batch for backend STT without sending a training turn. */
  const formData = new FormData();
  formData.append("audio", audio, `voice-input.${_extensionForAudio(audio.type)}`);
  if (sessionId) {
    formData.append("session_id", sessionId);
  }
  return request<SpeechTranscriptionResponse>("/api/speech/transcribe", {
    method: "POST",
    body: formData,
  });
}

export function finishSession(sessionId: string): Promise<FinishSessionResponse> {
  /** Finish a runtime training session and return its report. */
  return request<FinishSessionResponse>(`/api/sessions/${sessionId}/finish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getReport(sessionId: string): Promise<SessionReportResponse> {
  /** Load the final report for a finished runtime session. */
  return request<SessionReportResponse>(`/api/sessions/${sessionId}/report`);
}

export function submitLead(payload: Record<string, unknown>): Promise<{ status: string }> {
  /** Submit a public landing lead payload. */
  return request<{ status: string }>("/api/leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

function _extensionForAudio(mimeType: string): string {
  /** Keep a stable file extension so the backend sees a matching container hint. */
  if (mimeType.includes("ogg")) {
    return "ogg";
  }
  if (mimeType.includes("mp4")) {
    return "m4a";
  }
  if (mimeType.includes("mpeg")) {
    return "mp3";
  }
  return "webm";
}
