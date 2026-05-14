import { ApiError } from "../apiClient";
import { formatDate as formatSharedDate, statusLabel as sharedStatusLabel } from "../labels";
import type { AdminRouteState, JsonObject, OrganizationDetailTab } from "./types";

const ORGANIZATION_DETAIL_TABS = new Set<OrganizationDetailTab>(["overview", "users", "configs", "history", "usage", "audit"]);

export function parseAdminPath(path: string): AdminRouteState {
  /** Convert the browser path into the small route state used by AdminApp. */
  const [pathname, queryString] = path.split("?");
  const segments = pathname.split("/").filter(Boolean);
  const params = new URLSearchParams(queryString ?? "");
  const organizationTab = params.get("tab");
  if (segments[0] !== "admin") {
    return { route: "dashboard" };
  }
  if (segments[1] === "organizations" && segments[2] && segments[3] === "users" && segments[4] && segments[5] === "analytics") {
    return { route: "organization-user-analytics", organizationId: segments[2], userId: segments[4] };
  }
  if (segments[1] === "organizations" && segments[2]) {
    return {
      route: "organization-detail",
      organizationId: segments[2],
      tab: organizationTab && ORGANIZATION_DETAIL_TABS.has(organizationTab as OrganizationDetailTab)
        ? (organizationTab as OrganizationDetailTab)
        : undefined,
    };
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

export function auditPayloadSummary(value: JsonObject | null | undefined): string {
  /** Build a human-readable audit payload summary without exposing raw ids or JSON. */
  if (!value) {
    return "Без дополнительных данных";
  }

  const parts: string[] = [];
  if (typeof value.email === "string" && value.email.trim()) {
    parts.push(`Пользователь: ${value.email}`);
  }
  if (typeof value.name === "string" && value.name.trim()) {
    parts.push(`Настройка: ${value.name}`);
  }
  if (typeof value.client_slug === "string" && value.client_slug.trim()) {
    parts.push(`Организация: ${value.client_slug}`);
  }
  if (typeof value.default === "boolean") {
    parts.push(value.default ? "Назначена по умолчанию" : "Назначена как дополнительная");
  }

  return parts.length > 0 ? parts.join(" · ") : "Без дополнительных данных";
}

export function statusLabel(active: boolean): string {
  /** Map active flags to a short admin badge label. */
  return sharedStatusLabel(active);
}
