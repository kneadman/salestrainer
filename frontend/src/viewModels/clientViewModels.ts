import { formatDate, roleLabel, scenarioLabel, stageLabel, statusLabel } from "../labels";
import type { HistorySessionSummaryDTO, HistoryTurnDTO, ClientUserAnalyticsDTO } from "../client/types";
import type { FactsPanelDTO, RevealedFactCategory, ReportPayload, SessionPublicDTO } from "../types";
import { isJudgeSessionOutputPayload } from "../components/reportPayload";

export type ClientHistorySessionViewModel = {
  sessionId: string;
  userEmail: string;
  startedAtLabel: string;
  statusLabel: string;
  scenarioLabel: string;
  turnCount: number;
  finalInterestScore: string;
};

export function buildClientHistorySessionViewModel(dto: HistorySessionSummaryDTO): ClientHistorySessionViewModel {
  return {
    sessionId: dto.session_id,
    userEmail: dto.user_email,
    startedAtLabel: formatDate(dto.started_at),
    statusLabel: statusLabel(dto.status),
    scenarioLabel: dto.training_config_name || scenarioLabel(dto.scenario_id),
    turnCount: dto.turn_count,
    finalInterestScore: dto.final_interest_score?.toString() ?? "—",
  };
}

export type ClientTurnViewModel = {
  turnIndex: number;
  managerMessage: string;
  clientAnswer: string;
  createdAtLabel: string;
  interestBefore: number;
  interestAfter: number;
  stageBeforeLabel: string;
  stageAfterLabel: string;
};

export function buildClientTurnViewModel(dto: HistoryTurnDTO): ClientTurnViewModel {
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

export type TeamUserViewModel = {
  id: string;
  email: string;
  roleLabel: string;
  isActive: boolean;
  statusLabel: string;
  statusTone: "good" | "danger" | "neutral";
};

export function buildTeamUserViewModel(dto: { id: string; email: string; role: string; is_active: boolean }): TeamUserViewModel {
  return {
    id: dto.id,
    email: dto.email,
    roleLabel: roleLabel(dto.role),
    isActive: dto.is_active,
    statusLabel: statusLabel(dto.is_active),
    statusTone: dto.is_active ? "good" : "danger",
  };
}

export type ClientAnalyticsViewModel = {
  totalSessions: number;
  finishedSessions: number;
  activeSessions: number;
  completionRateLabel: string;
  avgFinalInterestScore: string;
  avgTurnCount: string;
  avgJudgementScore: string;
  sessionsWithJudgement: number;
  strongestSkillTitle: string;
  strongestSkillDetail: string;
  weakestSkillTitle: string;
  weakestSkillDetail: string;
  lastActivityAtLabel: string;
  statusBreakdown: { key: string; label: string; value: number }[];
  scenarioBreakdown: { key: string; label: string; value: number }[];
};

function formatSkillScore(value: number | null): string {
  return value === null ? "нет данных по оценкам" : `средняя оценка ${value.toFixed(1)}`;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function buildClientAnalyticsViewModel(dto: ClientUserAnalyticsDTO): ClientAnalyticsViewModel {
  return {
    totalSessions: dto.total_sessions,
    finishedSessions: dto.finished_sessions,
    activeSessions: dto.active_sessions,
    completionRateLabel: formatPercent(dto.completion_rate),
    avgFinalInterestScore: dto.avg_final_interest_score?.toFixed(1) ?? "—",
    avgTurnCount: dto.avg_turn_count?.toFixed(1) ?? "—",
    avgJudgementScore: dto.avg_judgement_score?.toFixed(1) ?? "—",
    sessionsWithJudgement: dto.sessions_with_judgement,
    strongestSkillTitle: dto.strongest_skill_title ?? "—",
    strongestSkillDetail: formatSkillScore(dto.strongest_skill_avg_score),
    weakestSkillTitle: dto.weakest_skill_title ?? "—",
    weakestSkillDetail: formatSkillScore(dto.weakest_skill_avg_score),
    lastActivityAtLabel: formatDate(dto.last_activity_at),
    statusBreakdown: Object.entries(dto.sessions_by_status).map(([key, value]) => ({
      key,
      label: statusLabel(key),
      value,
    })),
    scenarioBreakdown: Object.entries(dto.sessions_by_scenario).map(([key, value]) => ({
      key,
      label: scenarioLabel(key),
      value,
    })),
  };
}

const CATEGORY_LABELS: Record<RevealedFactCategory, string> = {
  role: "Роль",
  authority: "Полномочия",
  current_process: "Текущий процесс",
  decision_criterion: "Критерии решения",
  constraint: "Ограничения",
  buying_signal: "Сигналы интереса",
  pain: "Выявленные боли",
  objection: "Возражения",
};

const CATEGORY_ORDER: RevealedFactCategory[] = [
  "role",
  "authority",
  "current_process",
  "decision_criterion",
  "constraint",
  "buying_signal",
  "pain",
  "objection",
];

export type FactSectionViewModel = {
  label: string;
  values: string[];
};

export function buildFactsViewModel(factsPanel: FactsPanelDTO): FactSectionViewModel[] {
  const grouped = new Map<RevealedFactCategory, string[]>();
  for (const fact of factsPanel.items) {
    const text = fact.text.trim().replace(/\s+/g, " ");
    if (text.length === 0 || text.includes("_") || /^[a-z][a-z0-9_]*$/.test(text)) {
      continue;
    }
    const values = grouped.get(fact.category) ?? [];
    if (!values.some((value) => value.toLocaleLowerCase() === text.toLocaleLowerCase())) {
      values.push(text);
      grouped.set(fact.category, values);
    }
  }

  return CATEGORY_ORDER.map((category) => ({
    label: CATEGORY_LABELS[category],
    values: grouped.get(category) ?? [],
  })).filter((section) => section.values.length > 0);
}

const toneLabels: Record<string, string> = {
  cold: "Холодный",
  skeptical: "Скептичный",
  neutral: "Нейтральный",
  interested: "Заинтересованный",
  warm: "Тёплый",
  ready_next_step: "Готов к следующему шагу",
};

const interestBandLabels: Record<string, string> = {
  cold: "Холодный",
  skeptical: "Скептичный",
  neutral: "Нейтральный",
  warm: "Тёплый",
  hot: "Горячий",
};

export type MetricsViewModel = {
  interestScore: number;
  trust: number;
  toneLabel: string;
  turnCount: number;
  interestBandLabel: string;
  trainingConfigName?: string;
};

export function buildMetricsViewModel(session: SessionPublicDTO, trainingConfigName?: string): MetricsViewModel {
  const state = session.client_state_public;
  return {
    interestScore: session.interest.score,
    trust: typeof state.trust === "number" ? state.trust : 0,
    toneLabel: toneLabels[state.tone ?? ""] ?? state.tone ?? "Неизвестно",
    turnCount: session.turn_count,
    interestBandLabel: interestBandLabels[session.interest.band] ?? session.interest.band,
    trainingConfigName,
  };
}

export type UserProfileViewModel = {
  email: string;
  roleLabel: string;
  organizationName: string;
  passwordStatusLabel: string;
  passwordStatusTone: "good" | "warning";
};

export function buildUserProfileViewModel(user: { email: string; role: string; client_account: { name: string }; must_change_password: boolean }): UserProfileViewModel {
  return {
    email: user.email,
    roleLabel: roleLabel(user.role),
    organizationName: user.client_account.name,
    passwordStatusLabel: user.must_change_password ? "Требуется смена" : "Актуален",
    passwordStatusTone: user.must_change_password ? "warning" : "good",
  };
}

export type ReportViewModel = {
  hasStructuredPayload: boolean;
  executiveSummary: string;
  overallScore: number;
  overallGradeLabel: string;
  blocks: ReportPayload["bento_blocks"];
  skillScores: ReportPayload["skill_scores"];
  recommendations: unknown[];
  plainText: string | null;
};

export function buildReportViewModel(report: string | null, reportPayload: ReportPayload | null): ReportViewModel {
  const payload = isJudgeSessionOutputPayload(reportPayload) ? reportPayload : null;
  return {
    hasStructuredPayload: payload !== null,
    executiveSummary: payload?.executive_summary ?? "",
    overallScore: payload?.overall_score ?? 0,
    overallGradeLabel: payload?.overall_grade ?? "",
    blocks: payload?.bento_blocks ?? [],
    skillScores: payload?.skill_scores ?? [],
    recommendations: payload?.recommendations ?? [],
    plainText: report,
  };
}
