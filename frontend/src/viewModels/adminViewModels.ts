import {
  auditActionLabel,
  auditEntityLabel,
  formatDate,
  roleLabel,
  scenarioLabel,
  stageLabel,
  statusLabel,
} from "../labels";
import type {
  AuditLogDTO,
  HistorySessionSummaryDTO,
  HistoryTurnDTO,
  OrganizationDTO,
  TrainingConfigDTO,
  UsageSummaryDTO,
  UserDTO,
} from "../admin/types";

export type OrganizationViewModel = {
  id: string;
  name: string;
  slug: string;
  isActive: boolean;
  statusLabel: string;
  statusTone: "good" | "danger";
  createdAtLabel: string;
  updatedAtLabel: string;
  usersCount: number;
  activeUsersCount: number;
  trainingConfigsCount: number;
};

export function buildOrganizationViewModel(dto: OrganizationDTO): OrganizationViewModel {
  return {
    id: dto.id,
    name: dto.name,
    slug: dto.slug,
    isActive: dto.is_active,
    statusLabel: statusLabel(dto.is_active),
    statusTone: dto.is_active ? "good" : "danger",
    createdAtLabel: formatDate(dto.created_at),
    updatedAtLabel: formatDate(dto.updated_at),
    usersCount: dto.users_count,
    activeUsersCount: dto.active_users_count,
    trainingConfigsCount: dto.training_configs_count,
  };
}

export type UserViewModel = {
  id: string;
  email: string;
  roleLabel: string;
  isActive: boolean;
  statusLabel: string;
  statusTone: "good" | "danger";
  defaultTrainingConfigName: string | null;
};

export function buildUserViewModel(dto: UserDTO, configs: TrainingConfigDTO[]): UserViewModel {
  const defaultConfig = configs.find((c) => c.id === dto.default_training_config_id);
  return {
    id: dto.id,
    email: dto.email,
    roleLabel: roleLabel(dto.role),
    isActive: dto.is_active,
    statusLabel: statusLabel(dto.is_active),
    statusTone: dto.is_active ? "good" : "danger",
    defaultTrainingConfigName: defaultConfig?.name ?? null,
  };
}

export type HistorySessionViewModel = {
  sessionId: string;
  userEmail: string;
  statusLabel: string;
  scenarioLabel: string;
  trainingConfigLabel: string;
  startedAtLabel: string;
  turnCount: number;
  finalInterestScore: string;
};

export type HistoryTurnViewModel = {
  turnIndex: number;
  managerMessage: string;
  clientAnswer: string;
  createdAtLabel: string;
  interestBefore: number;
  interestAfter: number;
  stageBeforeLabel: string;
  stageAfterLabel: string;
};

export function buildHistoryTurnViewModel(dto: HistoryTurnDTO): HistoryTurnViewModel {
  return {
    turnIndex: dto.turn_index,
    managerMessage: dto.manager_message,
    clientAnswer: dto.client_answer,
    createdAtLabel: formatDate(dto.created_at),
    interestBefore: dto.interest_before,
    interestAfter: dto.interest_after,
    stageBeforeLabel: stageLabel(dto.stage_before),
    stageAfterLabel: stageLabel(dto.stage_after),
  };
}

export function buildHistorySessionViewModel(dto: HistorySessionSummaryDTO): HistorySessionViewModel {
  return {
    sessionId: dto.session_id,
    userEmail: dto.user_email,
    statusLabel: statusLabel(dto.status),
    scenarioLabel: scenarioLabel(dto.scenario_id),
    trainingConfigLabel: dto.training_config_name || scenarioLabel(dto.scenario_id),
    startedAtLabel: formatDate(dto.started_at),
    turnCount: dto.turn_count,
    finalInterestScore: dto.final_interest_score?.toString() ?? "—",
  };
}

export type AuditLogViewModel = {
  id: string;
  createdAtLabel: string;
  actionLabel: string;
  entityLabel: string;
  actorLabel: string;
  payloadSummary: string;
};

export function buildAuditLogViewModel(dto: AuditLogDTO): AuditLogViewModel {
  return {
    id: dto.id,
    createdAtLabel: formatDate(dto.created_at),
    actionLabel: auditActionLabel(dto.action),
    entityLabel: auditEntityLabel(dto.entity_type),
    actorLabel: dto.actor_user_id ? "Администратор" : "Система",
    payloadSummary: auditPayloadSummary(dto.payload),
  };
}

function auditPayloadSummary(payload: Record<string, unknown> | null | undefined): string {
  if (!payload) {
    return "Без дополнительных данных";
  }
  const parts: string[] = [];
  if (typeof payload.email === "string" && payload.email.trim()) {
    parts.push(`Пользователь: ${payload.email}`);
  }
  if (typeof payload.name === "string" && payload.name.trim()) {
    parts.push(`Настройка: ${payload.name}`);
  }
  if (typeof payload.client_slug === "string" && payload.client_slug.trim()) {
    parts.push(`Организация: ${payload.client_slug}`);
  }
  if (typeof payload.default === "boolean") {
    parts.push(payload.default ? "Назначена по умолчанию" : "Назначена как дополнительная");
  }
  return parts.length > 0 ? parts.join(" · ") : "Без дополнительных данных";
}

export type UsageBreakdownViewModel = {
  title: string;
  rows: { key: string; label: string; value: number }[];
};

export type UsageSummaryViewModel = {
  totalSessions: number;
  finishedSessions: number;
  activeSessions: number;
  uniqueUsers: number;
  totalTurns: number;
  avgFinalInterestScore: string;
  avgTurnCount: string;
  usageEventsCount: number;
  trainingConfigsWithSessions: number;
  statusBreakdown: UsageBreakdownViewModel;
  scenarioBreakdown: UsageBreakdownViewModel;
};

export function buildUsageSummaryViewModel(dto: UsageSummaryDTO): UsageSummaryViewModel {
  return {
    totalSessions: dto.total_sessions,
    finishedSessions: dto.finished_sessions,
    activeSessions: dto.active_sessions,
    uniqueUsers: dto.unique_users,
    totalTurns: dto.total_turns,
    avgFinalInterestScore: dto.avg_final_interest_score?.toFixed(1) ?? "—",
    avgTurnCount: dto.avg_turn_count?.toFixed(1) ?? "—",
    usageEventsCount: dto.usage_events_count,
    trainingConfigsWithSessions: Object.keys(dto.sessions_by_training_config).length,
    statusBreakdown: {
      title: "По статусам",
      rows: Object.entries(dto.sessions_by_status).map(([key, value]) => ({
        key,
        label: statusLabel(key),
        value,
      })),
    },
    scenarioBreakdown: {
      title: "По сценариям",
      rows: Object.entries(dto.sessions_by_scenario).map(([key, value]) => ({
        key,
        label: scenarioLabel(key),
        value,
      })),
    },
  };
}
