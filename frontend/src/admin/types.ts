import type { AuthUser, ReportPayload } from "../types";
import type { ClientUserAnalyticsDTO } from "../client/types";

export type AdminRoute =
  | "dashboard"
  | "organizations"
  | "organization-detail"
  | "organization-user-analytics"
  | "history"
  | "history-detail"
  | "audit-log";

export type OrganizationDetailTab = "overview" | "users" | "configs" | "history" | "usage" | "audit";

export type AdminRouteState = {
  route: AdminRoute;
  organizationId?: string;
  tab?: OrganizationDetailTab;
  userId?: string;
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
  default_training_config_id?: string | null;
  client_account?: {
    id: string;
    name: string;
    slug: string;
  } | null;
};

export type AdminUserAnalyticsDetailDTO = {
  user: UserDTO;
  analytics: ClientUserAnalyticsDTO;
  history: HistorySessionSummaryDTO[];
};

export type UserCreatePayload = {
  email: string;
  password: string;
  role: "client_lead" | "client_manager";
};

export type UserUpdatePayload = {
  email?: string;
  role?: "client_lead" | "client_manager";
  default_training_config_id?: string | null;
};

export type ObjectionItem = {
  text: string;
  type: string;
};

export type SeedConfig = {
  training_context: {
    product_area: string;
    target_segment: string;
    training_type: string;
    target_action: string;
    target_action_description: string;
    target_action_proper_name: string;
    call_goal: string;
    call_goal_is_not?: string[];
    preconditions?: string[];
    negative_behaviors?: string[];
  };
  product: {
    category: string;
    value_proposition: string;
    what_manager_sells_now: string;
    full_product_name: string;
    product_area_short: string;
  };
  lpr_and_roles: {
    allowed_roles?: string[];
    authority_level?: string;
    role_requirements: string;
  };
  segment_and_scale?: {
    industries?: string[];
    company_sizes?: string[];
  };
  triggers?: string[];
  pains?: string[];
  objections?: ObjectionItem[];
  decision_criteria?: string[];
  hidden_constraints?: string[];
  motivations?: string[];
  internal_conflict?: {
    side_a?: string[];
    side_b?: string[];
  };
  current_solutions?: {
    solution_types?: string[];
    alternative_solutions?: string[];
  };
  information_gaps?: string[];
  trust_requirements?: string[];
  novelty?: {
    anti_patterns?: string[];
    avoid_clusters?: string[];
  };
  starting_params: {
    initial_openness: { min: number; max: number };
    starting_interest: { min: number; max: number };
    trust_baseline: { min: number; max: number };
    price_sensitivity: { min: number; max: number };
    urgency: { min: number; max: number };
  };
};

export type TrainingConfigDTO = {
  id: string;
  client_account_id: string;
  name: string;
  is_active: boolean;
  persona_generation_context: string;
  seed_config: SeedConfig | null;
  created_at: string;
  updated_at: string;
};

export type TrainingConfigPayload = {
  name: string;
  persona_generation_context: string;
  seed_config?: SeedConfig | null;
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

export type HistorySessionSummaryDTO = {
  session_id: string;
  user_id: string;
  user_email: string;
  client_account_id: string;
  training_config_id: string | null;
  training_config_name: string | null;
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
  report_payload?: ReportPayload | null;
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

export type PerUserTokenUsageDTO = {
  user_id: string;
  email: string;
  total_input: number;
  total_output: number;
  total: number;
};

export type TokenUsageSummaryDTO = {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  per_user: PerUserTokenUsageDTO[];
};
