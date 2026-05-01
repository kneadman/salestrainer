import type {
  AuthMeResponse,
  ErrorResponse,
  FinishSessionResponse,
  SessionDetailResponse,
  SessionReportResponse,
  SessionStateResponse,
  TurnResponse,
} from "./types";

const BACKEND_UNAVAILABLE_MESSAGE =
  "Backend is unavailable. Check that FastAPI is running on localhost:8000.";
const CSRF_HEADER = "X-CSRF-Token";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

let csrfToken: string | null = null;

export class ApiError extends Error {
  code?: string;
  status?: number;

  constructor(message: string, code?: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) {
    return csrfToken;
  }

  const response = await fetch("/auth/csrf", {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new ApiError(`CSRF request failed: ${response.status} ${response.statusText}`.trim());
  }
  const payload = (await response.json()) as { csrf_token: string };
  csrfToken = payload.csrf_token;
  return csrfToken;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  const method = (init?.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const initHeaders = new Headers(init?.headers);
  initHeaders.forEach((value, key) => {
    headers[key] = value;
  });

  if (MUTATING_METHODS.has(method) && path !== "/auth/login") {
    headers[CSRF_HEADER] = await ensureCsrfToken();
  }

  try {
    response = await fetch(path, {
      ...init,
      credentials: "include",
      headers,
    });
  } catch {
    throw new ApiError(BACKEND_UNAVAILABLE_MESSAGE);
  }

  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? ((await response.json()) as unknown) : null;

  if (!response.ok) {
    const errorPayload = payload as ErrorResponse | null;
    const message =
      errorPayload?.error?.message || `Request failed: ${response.status} ${response.statusText}`.trim();
    throw new ApiError(message, errorPayload?.error?.code, response.status);
  }

  return payload as T;
}

export function login(email: string, password: string): Promise<AuthMeResponse> {
  csrfToken = null;
  return request<AuthMeResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  await request<void>("/auth/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
  csrfToken = null;
}

export function getMe(): Promise<AuthMeResponse> {
  return request<AuthMeResponse>("/auth/me");
}

export function createSession(): Promise<SessionStateResponse> {
  return request<SessionStateResponse>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getSession(sessionId: string): Promise<SessionDetailResponse> {
  return request<SessionDetailResponse>(`/api/sessions/${sessionId}`);
}

export function sendMessage(sessionId: string, managerMessage: string): Promise<TurnResponse> {
  return request<TurnResponse>(`/api/sessions/${sessionId}/messages`, {
    method: "POST",
    body: JSON.stringify({ manager_message: managerMessage }),
  });
}

export function finishSession(sessionId: string): Promise<FinishSessionResponse> {
  return request<FinishSessionResponse>(`/api/sessions/${sessionId}/finish`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getReport(sessionId: string): Promise<SessionReportResponse> {
  return request<SessionReportResponse>(`/api/sessions/${sessionId}/report`);
}

export function submitLead(payload: Record<string, unknown>): Promise<{ status: string }> {
  return request<{ status: string }>("/api/leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitQuizLead(payload: Record<string, unknown>): Promise<{ status: string }> {
  return request<{ status: string }>("/api/quiz-leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
