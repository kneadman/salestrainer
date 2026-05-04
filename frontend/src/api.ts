import type {
  AuthMeResponse,
  FinishSessionResponse,
  SessionDetailResponse,
  SessionReportResponse,
  SessionStateResponse,
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

export function createSession(): Promise<SessionStateResponse> {
  /** Create a new runtime training session for the current user. */
  return request<SessionStateResponse>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getSession(sessionId: string): Promise<SessionDetailResponse> {
  /** Load public-safe runtime session detail. */
  return request<SessionDetailResponse>(`/api/sessions/${sessionId}`);
}

export function sendMessage(sessionId: string, managerMessage: string): Promise<TurnResponse> {
  /** Send one manager message to the training simulator. */
  return request<TurnResponse>(`/api/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ manager_message: managerMessage }),
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
