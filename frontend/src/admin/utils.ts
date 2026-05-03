import { ApiError } from "../apiClient";
import type { AdminRouteState, JsonObject } from "./types";

export const FALLBACK_SCENARIOS = [
  "generic_b2b_first_contact",
  "sales_audit_cold_outreach",
  "accounting_outsource_cold_outreach",
];

export function parseAdminPath(path: string): AdminRouteState {
  /** Convert the browser path into the small route state used by AdminApp. */
  const segments = path.split("/").filter(Boolean);
  if (segments[0] !== "admin") {
    return { route: "dashboard" };
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
  return "Unexpected error.";
}

export function formatDate(value: string | null | undefined): string {
  /** Format an ISO date for compact admin tables. */
  if (!value) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export function parseJsonObject(value: string, fieldName: string): JsonObject {
  /** Parse a textarea JSON value and require an object payload. */
  const parsed = JSON.parse(value) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${fieldName}: JSON must be an object.`);
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
  return active ? "active" : "disabled";
}
