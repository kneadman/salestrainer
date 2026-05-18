export type InterestDTO = {
  score: number;
  band: string;
};

export type RevealedFactCategory =
  | "role"
  | "authority"
  | "pain"
  | "decision_criterion"
  | "constraint"
  | "current_process"
  | "buying_signal"
  | "objection";

export type RevealedFact = {
  category: RevealedFactCategory;
  text: string;
  turn_index: number;
};

export type ClientStatePublic = {
  tone?: string;
  trust?: number;
  visible_objections?: string[];
  buying_signals?: string[];
  revealed_facts?: RevealedFact[];
};

export type FactsPanelItemDTO = {
  category: RevealedFactCategory;
  label: string;
  text: string;
  turn_index: number;
};

export type FactsPanelDTO = {
  items: FactsPanelItemDTO[];
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
  public_brief: string;
  stage: string;
  interest: InterestDTO;
  client_state_public: ClientStatePublic;
  facts_panel: FactsPanelDTO;
  turn_count: number;
  summary: string;
  state_version: number;
  training_config_id?: string | null;
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

export type JudgementSeverity = "green" | "yellow" | "red" | "neutral";

export type JudgementGrade = "critical" | "weak" | "normal" | "good" | "strong";

export type FindingImpact = "low" | "medium" | "high";

export type BentoBlockType =
  | "summary"
  | "score"
  | "strength"
  | "weakness"
  | "missed_context"
  | "recommendation"
  | "timeline"
  | "next_step";

export type BentoReportBlockDTO = {
  id: string;
  title: string;
  type: BentoBlockType;
  severity: JudgementSeverity;
  score: number | null;
  short_text: string;
  detail: string;
  evidence_turn_indexes: number[];
};

export type SkillScoreDTO = {
  id: string;
  title: string;
  score: number;
  severity: JudgementSeverity;
  explanation: string;
  evidence_turn_indexes: number[];
};

export type ReportFindingDTO = {
  title: string;
  description: string;
  evidence_turn_indexes: number[];
  impact: FindingImpact;
};

export type ReportRecommendationDTO = {
  title: string;
  description: string;
  example_phrase: string | null;
  priority: FindingImpact;
};

export type JudgeSessionOutputDTO = {
  schema_version: 1;
  overall_score: number;
  overall_grade: JudgementGrade;
  outcome: string;
  executive_summary: string;
  bento_blocks: BentoReportBlockDTO[];
  skill_scores: SkillScoreDTO[];
  key_strengths: ReportFindingDTO[];
  key_weaknesses: ReportFindingDTO[];
  missed_opportunities: ReportFindingDTO[];
  recommendations: ReportRecommendationDTO[];
  final_verdict: string;
  risk_flags: string[];
};

export type SpeechTranscriptionResponse = {
  text: string;
  normalized: boolean;
  duration_ms: number | null;
};

export type ReportPayload = JudgeSessionOutputDTO | Record<string, unknown>;

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
