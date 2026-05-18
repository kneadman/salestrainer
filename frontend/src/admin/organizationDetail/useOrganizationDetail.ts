import { useCallback, useEffect, useState } from "react";
import {
  getUsageSummary,
  listAuditLog,
  listOrganizationHistory,
  listOrganizations,
  listTrainingConfigs,
  listUsers,
} from "../api";
import type {
  AuditLogDTO,
  HistorySessionSummaryDTO,
  OrganizationDTO,
  TrainingConfigDTO,
  UsageSummaryDTO,
  UserDTO,
} from "../types";
import { getErrorMessage } from "../utils";

export type UseOrganizationDetailResult = {
  organization: OrganizationDTO | null;
  users: UserDTO[];
  configs: TrainingConfigDTO[];
  history: HistorySessionSummaryDTO[];
  usage: UsageSummaryDTO | null;
  audit: AuditLogDTO[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
};

export function useOrganizationDetail(organizationId: string): UseOrganizationDetailResult {
  /** Load and reload all organization detail data from internal admin endpoints. */
  const [organization, setOrganization] = useState<OrganizationDTO | null>(null);
  const [users, setUsers] = useState<UserDTO[]>([]);
  const [configs, setConfigs] = useState<TrainingConfigDTO[]>([]);
  const [history, setHistory] = useState<HistorySessionSummaryDTO[]>([]);
  const [usage, setUsage] = useState<UsageSummaryDTO | null>(null);
  const [audit, setAudit] = useState<AuditLogDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const orgs = await listOrganizations();
      const selectedOrg = orgs.find((item) => item.id === organizationId) ?? null;
      setOrganization(selectedOrg);
      if (!selectedOrg) {
        throw new Error("Организация не найдена.");
      }
      const [loadedUsers, loadedConfigs, loadedHistory, loadedUsage, loadedAudit] = await Promise.all([
        listUsers(organizationId),
        listTrainingConfigs(organizationId),
        listOrganizationHistory(organizationId, { limit: 50, offset: 0 }).catch(() => [] as HistorySessionSummaryDTO[]),
        getUsageSummary(organizationId).catch(() => null),
        listAuditLog({ organization_id: organizationId, limit: 50, offset: 0 }).catch(() => [] as AuditLogDTO[]),
      ]);
      setUsers(loadedUsers);
      setConfigs(loadedConfigs);
      setHistory(loadedHistory);
      setUsage(loadedUsage);
      setAudit(loadedAudit);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return {
    organization,
    users,
    configs,
    history,
    usage,
    audit,
    loading,
    error,
    reload,
  };
}
