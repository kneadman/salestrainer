import { ApiError } from "./apiClient";

export function getErrorMessage(error: unknown): string {
  /** Normalize thrown API/client errors to displayable text. */
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неожиданная ошибка.";
}
