import { request } from "../apiClient";
import type {
  AdminUserAnalyticsDetailDTO,
  AuditLogDTO,
  HistorySessionDetailDTO,
  HistorySessionSummaryDTO,
  OrganizationDTO,
  OrganizationPayload,
  ScenarioOptionDTO,
  TrainingConfigDTO,
  TrainingConfigPayload,
  UsageSummaryDTO,
  UserCreatePayload,
  UserDTO,
  UserTrainingConfigAssignmentDTO,
  UserUpdatePayload,
} from "./types";

function queryString(params: Record<string, string | number | null | undefined>): string {
  /** Convert optional filter params to a stable query string. */
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export function listOrganizations(): Promise<OrganizationDTO[]> {
  /** Load all organizations for the internal admin dashboard. */
  return request<OrganizationDTO[]>("/api/internal/organizations");
}

export function createOrganization(payload: OrganizationPayload): Promise<OrganizationDTO> {
  /** Create a client organization through the internal admin API. */
  return request<OrganizationDTO>("/api/internal/organizations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateOrganization(organizationId: string, payload: Partial<OrganizationPayload>): Promise<OrganizationDTO> {
  /** Update organization name or slug. */
  return request<OrganizationDTO>(`/api/internal/organizations/${organizationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function enableOrganization(organizationId: string): Promise<OrganizationDTO> {
  /** Enable a disabled organization after confirmation. */
  return request<OrganizationDTO>(`/api/internal/organizations/${organizationId}/enable`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function disableOrganization(organizationId: string): Promise<OrganizationDTO> {
  /** Disable an organization after confirmation. */
  return request<OrganizationDTO>(`/api/internal/organizations/${organizationId}/disable`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function listUsers(organizationId: string): Promise<UserDTO[]> {
  /** Load users for one organization. */
  return request<UserDTO[]>(`/api/internal/organizations/${organizationId}/users`);
}

export function getOrganizationUserAnalytics(organizationId: string, userId: string): Promise<AdminUserAnalyticsDetailDTO> {
  /** Load one organization user's analytics and recent history for internal admin review. */
  return request<AdminUserAnalyticsDetailDTO>(`/api/internal/organizations/${organizationId}/users/${userId}/analytics`);
}

export function createUser(organizationId: string, payload: UserCreatePayload): Promise<UserDTO> {
  /** Create a client-side lead or manager user. */
  return request<UserDTO>(`/api/internal/organizations/${organizationId}/users`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateUser(userId: string, payload: UserUpdatePayload): Promise<UserDTO> {
  /** Update a user's email or client role. */
  return request<UserDTO>(`/api/internal/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function resetUserPassword(userId: string, password: string): Promise<UserDTO> {
  /** Reset a temporary password without persisting it client-side. */
  return request<UserDTO>(`/api/internal/users/${userId}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export function enableUser(userId: string): Promise<UserDTO> {
  /** Enable a disabled user. */
  return request<UserDTO>(`/api/internal/users/${userId}/enable`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function disableUser(userId: string): Promise<UserDTO> {
  /** Disable a user after confirmation. */
  return request<UserDTO>(`/api/internal/users/${userId}/disable`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function listTrainingConfigs(organizationId: string): Promise<TrainingConfigDTO[]> {
  /** Load training configs for one organization. */
  return request<TrainingConfigDTO[]>(`/api/internal/organizations/${organizationId}/training-configs`);
}

export function createTrainingConfig(organizationId: string, payload: TrainingConfigPayload): Promise<TrainingConfigDTO> {
  /** Create a training config from the simplified admin form. */
  return request<TrainingConfigDTO>(`/api/internal/organizations/${organizationId}/training-configs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateTrainingConfig(configId: string, payload: Partial<TrainingConfigPayload>): Promise<TrainingConfigDTO> {
  /** Update only visible training config fields. */
  return request<TrainingConfigDTO>(`/api/internal/training-configs/${configId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function enableTrainingConfig(configId: string): Promise<TrainingConfigDTO> {
  /** Enable a disabled training config. */
  return request<TrainingConfigDTO>(`/api/internal/training-configs/${configId}/enable`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function disableTrainingConfig(configId: string): Promise<TrainingConfigDTO> {
  /** Disable a training config after confirmation. */
  return request<TrainingConfigDTO>(`/api/internal/training-configs/${configId}/disable`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function listUserTrainingConfigs(userId: string): Promise<UserTrainingConfigAssignmentDTO[]> {
  /** Load training config assignments for one user. */
  return request<UserTrainingConfigAssignmentDTO[]>(`/api/internal/users/${userId}/training-configs`);
}

export function assignTrainingConfig(userId: string, configId: string): Promise<UserTrainingConfigAssignmentDTO> {
  /** Assign a config to one user. */
  return request<UserTrainingConfigAssignmentDTO>(`/api/internal/users/${userId}/training-configs/${configId}/assign`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function makeDefaultTrainingConfig(userId: string, configId: string): Promise<UserTrainingConfigAssignmentDTO> {
  /** Mark one assigned training config as a user's default. */
  return request<UserTrainingConfigAssignmentDTO>(`/api/internal/users/${userId}/training-configs/${configId}/make-default`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function unassignTrainingConfig(userId: string, configId: string): Promise<{ status: string }> {
  /** Remove a training config assignment from one user. */
  return request<{ status: string }>(`/api/internal/users/${userId}/training-configs/${configId}/unassign`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function listScenarios(): Promise<ScenarioOptionDTO[]> {
  /** Load scenario options for training config forms. */
  return request<ScenarioOptionDTO[]>("/api/scenarios");
}

export function listOrganizationHistory(organizationId: string, params: Record<string, string | number | null | undefined>): Promise<HistorySessionSummaryDTO[]> {
  /** Load persistent training history for one organization. */
  return request<HistorySessionSummaryDTO[]>(`/api/internal/organizations/${organizationId}/history/sessions${queryString(params)}`);
}

export function getHistorySession(sessionId: string): Promise<HistorySessionDetailDTO> {
  /** Load public-safe history detail for one session. */
  return request<HistorySessionDetailDTO>(`/api/history/sessions/${sessionId}`);
}

export function getUsageSummary(organizationId: string): Promise<UsageSummaryDTO> {
  /** Load basic usage analytics for one organization. */
  return request<UsageSummaryDTO>(`/api/internal/organizations/${organizationId}/usage-summary`);
}

export function listAuditLog(params: Record<string, string | number | null | undefined>): Promise<AuditLogDTO[]> {
  /** Load audit events with optional internal-admin filters. */
  return request<AuditLogDTO[]>(`/api/internal/audit-log${queryString(params)}`);
}
