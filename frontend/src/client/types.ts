export type ClientRoute =
  | "dashboard"
  | "trainer"
  | "history"
  | "history-detail"
  | "analytics"
  | "team"
  | "team-detail"
  | "team-analytics"
  | "balance"
  | "settings";

export type ClientRouteState = {
  route: ClientRoute;
  sessionId?: string;
  userId?: string;
};

export type JsonObject = Record<string, unknown>;

export type ClientUserAnalyticsDTO = {
  user_id: string;
  user_email: string;
  total_sessions: number;
  finished_sessions: number;
  active_sessions: number;
  completion_rate: number;
  avg_final_interest_score: number | null;
  avg_turn_count: number | null;
  last_activity_at: string | null;
  sessions_by_status: Record<string, number>;
  sessions_by_scenario: Record<string, number>;
};

export type HistorySessionSummaryDTO = {
  session_id: string;
  user_id: string;
  user_email: string;
  client_account_id: string;
  training_config_id: string | null;
  scenario_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  last_activity_at: string;
  turn_count: number;
  final_interest_score: number | null;
  final_stage: string | null;
  summary: string | null;
};

export type HistoryTurnDTO = {
  turn_index: number;
  manager_message: string;
  client_answer: string;
  interest_before: number;
  interest_delta: number;
  interest_after: number;
  stage_before: string;
  stage_after: string;
  client_state_public: JsonObject | null;
  evaluation: JsonObject | null;
  created_at: string;
};

export type HistoryReportDTO = {
  session_id: string;
  report: string;
  report_payload?: JsonObject | null;
  report_version: number;
  created_at: string;
  updated_at: string;
};

export type HistorySessionDetailDTO = {
  session: HistorySessionSummaryDTO;
  public_brief: string | null;
  turns: HistoryTurnDTO[];
  report: HistoryReportDTO | null;
};

export type TeamUserDTO = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  total_sessions: number;
  finished_sessions: number;
  avg_final_interest_score: number | null;
  last_activity_at: string | null;
};

export type TeamUserDetailDTO = {
  user: TeamUserDTO;
  analytics: ClientUserAnalyticsDTO;
  history: HistorySessionSummaryDTO[];
};

export type TeamUsageSummaryDTO = {
  total_sessions: number;
  finished_sessions: number;
  active_sessions: number;
  unique_users: number;
  total_turns: number;
  avg_final_interest_score: number | null;
  avg_turn_count: number | null;
  sessions_by_status: Record<string, number>;
  sessions_by_scenario: Record<string, number>;
  sessions_by_training_config: Record<string, number>;
  usage_events_count: number;
  users: TeamUserDTO[];
};
