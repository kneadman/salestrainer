import type { ErrorResponse } from "./types";

const BACKEND_UNAVAILABLE_MESSAGE =
  "Backend недоступен. Проверьте, что FastAPI запущен на localhost:8000.";
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

export function clearCachedCsrfToken(): void {
  /** Clear cached CSRF after login/logout changes the browser auth context. */
  csrfToken = null;
}

async function ensureCsrfToken(): Promise<string> {
  /** Fetch and cache the readable CSRF token required by mutating browser requests. */
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
    throw new ApiError(`Не удалось получить CSRF-токен: ${response.status} ${response.statusText}`.trim());
  }
  const payload = (await response.json()) as { csrf_token: string };
  csrfToken = payload.csrf_token;
  return csrfToken;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  /** Run one typed JSON API request with cookies, CSRF, and normalized errors. */
  let response: Response;
  const method = (init?.method ?? "GET").toUpperCase();
  const isFormDataBody = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const headers: Record<string, string> = isFormDataBody
    ? {}
    : {
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
      errorPayload?.error?.message || `Запрос завершился ошибкой: ${response.status} ${response.statusText}`.trim();
    throw new ApiError(message, errorPayload?.error?.code, response.status);
  }

  return payload as T;
}
