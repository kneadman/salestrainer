import { ApiError } from "../apiClient";
import type { ClientRouteState } from "./types";

export function parseClientPath(path: string): ClientRouteState {
  /** Convert /app browser paths to the lightweight client route state. */
  const segments = path.split("/").filter(Boolean);
  if (segments[0] !== "app") {
    return { route: "dashboard" };
  }
  if (segments[1] === "trainer") {
    return { route: "trainer" };
  }
  if (segments[1] === "history" && segments[2]) {
    return { route: "history-detail", sessionId: segments[2] };
  }
  if (segments[1] === "history") {
    return { route: "history" };
  }
  if (segments[1] === "analytics") {
    return { route: "analytics" };
  }
  if (segments[1] === "team" && segments[2]) {
    return { route: "team-detail", userId: segments[2] };
  }
  if (segments[1] === "team") {
    return { route: "team" };
  }
  if (segments[1] === "team-analytics") {
    return { route: "team-analytics" };
  }
  if (segments[1] === "balance") {
    return { route: "balance" };
  }
  if (segments[1] === "settings") {
    return { route: "settings" };
  }
  return { route: "dashboard" };
}

export function getClientErrorMessage(error: unknown): string {
  /** Normalize thrown client/API errors to readable UI text. */
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Unexpected error.";
}

export function formatClientDate(value: string | null | undefined): string {
  /** Format dates consistently in the client cabinet. */
  if (!value) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function percent(value: number): string {
  /** Format decimal ratios as whole percent labels. */
  return `${Math.round(value * 100)}%`;
}
