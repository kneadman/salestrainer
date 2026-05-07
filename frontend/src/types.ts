export type InterestDTO = {
  score: number;
  band: string;
};

export type ClientStatePublic = {
  tone?: string;
  trust?: number;
  visible_objections?: string[];
  known_pains?: string[];
  buying_signals?: string[];
  discovered_role?: string | null;
  discovered_authority_level?: string | null;
  discovered_decision_criteria?: string[];
  discovered_constraints?: string[];
  discovered_current_process?: string[];
};

export type TurnPublicDTO = {
  turn_index: number;
  manager_message: string;
  client_answer: string;
  interest_before: number;
  interest_delta: number;
  interest_after: number;
  stage_before: string;
  stage_after: string;
  created_at: string;
};

export type SessionPublicDTO = {
  session_id: string;
  scenario_id: string;
  status: string;
  persona_name: string;
  public_brief: string;
  stage: string;
  interest: InterestDTO;
  client_state_public: ClientStatePublic;
  turn_count: number;
  summary: string;
  state_version: number;
};

export type SessionStateResponse = {
  session: SessionPublicDTO;
};

export type SessionDetailResponse = {
  session: SessionPublicDTO;
  turns: TurnPublicDTO[];
};

export type TurnResponse = {
  session: SessionPublicDTO;
  turns: TurnPublicDTO[];
  client_answer: string;
  interest_before: number;
  interest_delta: number;
  interest_after: number;
  stage_before: string;
  stage_after: string;
  turn_index: number;
};

export type FinishSessionResponse = {
  session: SessionPublicDTO;
  report: string;
  report_payload?: ReportPayload | null;
};

export type SessionReportResponse = {
  session: SessionPublicDTO;
  report: string;
  report_payload?: ReportPayload | null;
};

export type ReportPayload = Record<string, unknown>;

export type ClientAccount = {
  id: string;
  name: string;
  slug: string;
};

export type AuthUser = {
  id: string;
  email: string;
  role: string;
  must_change_password: boolean;
  client_account: ClientAccount;
};

export type AuthMeResponse = {
  user: AuthUser;
};

export type ErrorBody = {
  code: string;
  message: string;
  request_id?: string | null;
  details?: Array<Record<string, unknown>>;
};

export type ErrorResponse = {
  error: ErrorBody;
};
