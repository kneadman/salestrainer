import { ApiError } from "../apiClient";
import { formatDate as formatSharedDate, statusLabel as sharedStatusLabel } from "../labels";
import type { AdminRouteState, JsonObject } from "./types";

export const FALLBACK_SCENARIOS = [
  "first_contact_discovery",
  "qualification_and_authority",
  "needs_diagnosis",
  "objection_handling",
  "price_and_value",
  "bad_experience_recovery",
  "next_step_booking",
  "follow_up_after_pause",
];

export function parseAdminPath(path: string): AdminRouteState {
  /** Convert the browser path into the small route state used by AdminApp. */
  const segments = path.split("/").filter(Boolean);
  if (segments[0] !== "admin") {
    return { route: "dashboard" };
  }
  if (segments[1] === "organizations" && segments[2] && segments[3] === "users" && segments[4] && segments[5] === "analytics") {
    return { route: "organization-user-analytics", organizationId: segments[2], userId: segments[4] };
  }
  if (segments[1] === "organizations" && segments[2]) {
    return { route: "organization-detail", organizationId: segments[2] };
  }
  if (segments[1] === "organizations") {
    return { route: "organizations" };
  }
  if (segments[1] === "history" && segments[2] === "sessions" && segments[3]) {
    return { route: "history-detail", sessionId: segments[3] };
  }
  if (segments[1] === "history") {
    return { route: "history" };
  }
  if (segments[1] === "audit-log") {
    return { route: "audit-log" };
  }
  return { route: "dashboard" };
}

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

export function formatDate(value: string | null | undefined): string {
  /** Format an ISO date for compact admin tables. */
  return formatSharedDate(value);
}

export function parseJsonObject(value: string, fieldName: string): JsonObject {
  /** Parse a textarea JSON value and require an object payload. */
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${fieldName}: JSON должен быть объектом.`);
  }
  return parsed as JsonObject;
}

export function stringifyJson(value: JsonObject | null | undefined): string {
  /** Pretty-print stored JSON objects for textarea editing. */
  return JSON.stringify(value ?? {}, null, 2);
}

export function compactJson(value: JsonObject): string {
  /** Render compact JSON for audit/history payload cells. */
  return JSON.stringify(value, null, 2);
}

export function statusLabel(active: boolean): string {
  /** Map active flags to a short admin badge label. */
  return sharedStatusLabel(active);
}
