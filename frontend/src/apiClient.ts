import type { ErrorResponse } from "./types";

const BACKEND_UNAVAILABLE_MESSAGE =
  "Сервис временно недоступен. Попробуйте обновить страницу или обратиться к администратору.";
const GENERIC_ERROR_MESSAGE = "Не удалось выполнить действие. Попробуйте ещё раз.";
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
    throw new ApiError("Не удалось подготовить безопасный запрос. Обновите страницу и попробуйте снова.");
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
      userMessageForError(response.status, errorPayload)
      || GENERIC_ERROR_MESSAGE;
    throw new ApiError(message, errorPayload?.error?.code, response.status);
  }

  return payload as T;
}

function userMessageForError(status: number, errorPayload: ErrorResponse | null): string | null {
  /** Convert backend error contracts to messages that are safe to show in product UI. */
  const code = errorPayload?.error?.code;
  if (code === "validation_error" || status === 422) {
    return "Проверьте заполнение полей и попробуйте снова.";
  }
  if (code === "forbidden" || status === 403) {
    return "Не удалось подтвердить действие. Обновите страницу и попробуйте снова.";
  }
  if (code === "unauthorized" || status === 401) {
    return "Войдите в аккаунт и попробуйте снова.";
  }
  if (code === "not_found" || status === 404) {
    return "Данные не найдены или больше недоступны.";
  }
  if (code === "conflict" || status === 409) {
    return "Действие сейчас нельзя выполнить. Обновите данные и попробуйте снова.";
  }
  if (code === "payload_too_large" || status === 413) {
    return "Файл слишком большой. Выберите файл меньшего размера.";
  }
  if (code === "too_many_requests" || status === 429) {
    return "Слишком много запросов. Подождите немного и попробуйте снова.";
  }
  if (status >= 500) {
    return BACKEND_UNAVAILABLE_MESSAGE;
  }
  return null;
}
