import { request } from "../apiClient";
import type { AuthMeResponse } from "../types";
import type {
  ClientUserAnalyticsDTO,
  HistoryReportDTO,
  HistorySessionDetailDTO,
  HistorySessionSummaryDTO,
  TeamUsageSummaryDTO,
  TeamUserDTO,
  TeamUserDetailDTO,
  TrainingConfigOptionDTO,
} from "./types";

function queryString(params: Record<string, string | number | null | undefined>): string {
  /** Convert optional filters into a query string for client endpoints. */
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export function getHistorySessions(params: Record<string, string | number | null | undefined>): Promise<HistorySessionSummaryDTO[]> {
  /** Load role-scoped persistent history for the current user. */
  return request<HistorySessionSummaryDTO[]>(`/api/history/sessions${queryString(params)}`);
}

export function getHistorySessionDetail(sessionId: string): Promise<HistorySessionDetailDTO> {
  /** Load public-safe detail for one persistent history session. */
  return request<HistorySessionDetailDTO>(`/api/history/sessions/${sessionId}`);
}

export function getHistoryReport(sessionId: string): Promise<HistoryReportDTO> {
  /** Load a saved persistent report for one history session. */
  return request<HistoryReportDTO>(`/api/history/sessions/${sessionId}/report`);
}

export function getTrainingConfigs(): Promise<TrainingConfigOptionDTO[]> {
  /** Load training config options available in the client cabinet. */
  return request<TrainingConfigOptionDTO[]>("/api/client/training-configs");
}

export function getMyAnalytics(): Promise<ClientUserAnalyticsDTO> {
  /** Load personal analytics for the current user. */
  return request<ClientUserAnalyticsDTO>("/api/client/analytics/me");
}

export function getTeamUsers(): Promise<TeamUserDTO[]> {
  /** Load same-organization team users for a client lead. */
  return request<TeamUserDTO[]>("/api/team/users");
}

export function getTeamUsageSummary(): Promise<TeamUsageSummaryDTO> {
  /** Load same-organization team usage summary for a client lead. */
  return request<TeamUsageSummaryDTO>("/api/team/usage-summary");
}

export function getTeamUserDetail(userId: string): Promise<TeamUserDetailDTO> {
  /** Load one same-organization user's analytics for a client lead. */
  return request<TeamUserDetailDTO>(`/api/team/users/${userId}/analytics`);
}

export function getTeamUserHistory(userId: string, params: Record<string, string | number | null | undefined>): Promise<HistorySessionSummaryDTO[]> {
  /** Load one same-organization user's history for a client lead. */
  return request<HistorySessionSummaryDTO[]>(`/api/team/users/${userId}/history/sessions${queryString(params)}`);
}

export function changePassword(currentPassword: string, newPassword: string): Promise<AuthMeResponse> {
  /** Change the current user's password through the auth API. */
  return request<AuthMeResponse>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}
