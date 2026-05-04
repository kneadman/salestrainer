import type { AuthUser } from "../types";

export type AdminRoute =
  | "dashboard"
  | "organizations"
  | "organization-detail"
  | "history"
  | "history-detail"
  | "audit-log";

export type AdminRouteState = {
  route: AdminRoute;
  organizationId?: string;
  sessionId?: string;
};

export type AdminAppProps = {
  user: AuthUser;
  path: string;
  onNavigate: (path: string, replace?: boolean) => void;
  onLogout: () => Promise<void>;
};

export type JsonObject = Record<string, unknown>;

export type OrganizationDTO = {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  users_count: number;
  active_users_count: number;
  training_configs_count: number;
};

export type OrganizationPayload = {
  name: string;
  slug: string;
};

export type UserDTO = {
  id: string;
  client_account_id: string;
  email: string;
  role: "client_lead" | "client_manager" | string;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
  updated_at: string;
  client_account?: {
    id: string;
    name: string;
    slug: string;
  } | null;
};

export type UserCreatePayload = {
  email: string;
  password: string;
  role: "client_lead" | "client_manager";
};

export type UserUpdatePayload = {
  email?: string;
  role?: "client_lead" | "client_manager";
};

export type TrainingConfigDTO = {
  id: string;
  client_account_id: string;
  name: string;
  is_active: boolean;
  default_scenario_id: string;
  product_line: string;
  persona_policy: JsonObject;
  ui_config: JsonObject;
  limits: JsonObject;
  llm_provider_config_id: string | null;
  created_at: string;
  updated_at: string;
};

export type TrainingConfigPayload = {
  name: string;
  default_scenario_id: string;
  product_line: string;
  persona_policy: JsonObject;
  ui_config: JsonObject;
  limits: JsonObject;
  llm_provider_config_id?: string | null;
};

export type UserTrainingConfigAssignmentDTO = {
  user_id: string;
  training_config_id: string;
  is_default: boolean;
  training_config: TrainingConfigDTO;
};

export type LLMProviderConfigDTO = {
  id: string;
  client_account_id: string;
  name: string;
  provider: string;
  is_active: boolean;
  has_persona_api_key: boolean;
  persona_api_key_preview: string | null;
  persona_folder_id: string | null;
  persona_agent_id: string | null;
  persona_master_prompt: string | null;
  persona_json_template: string | null;
  has_dialogue_api_key: boolean;
  dialogue_api_key_preview: string | null;
  dialogue_folder_id: string | null;
  dialogue_agent_id: string | null;
  dialogue_master_prompt: string | null;
  dialogue_json_template: string | null;
  created_at: string;
  updated_at: string;
};

export type LLMProviderConfigPayload = {
  name?: string;
  provider?: "yandex_compatible" | "openai_compatible" | "fake";
  persona_api_key?: string;
  persona_folder_id?: string | null;
  persona_agent_id?: string | null;
  persona_master_prompt?: string | null;
  persona_json_template?: string | null;
  dialogue_api_key?: string;
  dialogue_folder_id?: string | null;
  dialogue_agent_id?: string | null;
  dialogue_master_prompt?: string | null;
  dialogue_json_template?: string | null;
};

export type AuditLogDTO = {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  payload: JsonObject;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
};

export type ScenarioOptionDTO = {
  scenario_id: string;
  name: string;
  offer: string;
  target_audience: string;
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

export type UsageSummaryDTO = {
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
};
