import type {
  ErrorResponse,
  FinishSessionResponse,
  SessionDetailResponse,
  SessionReportResponse,
  SessionStateResponse,
  TurnResponse,
} from "./types";

const BACKEND_UNAVAILABLE_MESSAGE =
  "Backend недоступен. Проверьте, что FastAPI запущен на localhost:8000.";

export class ApiError extends Error {
  code?: string;

  constructor(message: string, code?: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(path, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
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
      errorPayload?.error?.message || `Ошибка запроса: ${response.status} ${response.statusText}`.trim();
    throw new ApiError(message, errorPayload?.error?.code);
  }

  return payload as T;
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
