import { render, screen } from "@testing-library/react";
import { HistoryPage } from "./HistoryPage";
import type { HistorySessionDetailDTO } from "./types";
import type { JudgeSessionOutputDTO, ReportPayload } from "../types";

const apiMocks = vi.hoisted(() => ({
  getHistorySessionDetail: vi.fn<() => Promise<HistorySessionDetailDTO>>(),
  getHistorySessions: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getHistorySessionDetail: apiMocks.getHistorySessionDetail,
    getHistorySessions: apiMocks.getHistorySessions,
  };
});

const structuredReportPayload: JudgeSessionOutputDTO = {
  schema_version: 1,
  overall_score: 82,
  overall_grade: "good",
  outcome: "meeting",
  executive_summary: "Менеджер качественно провёл discovery.",
  bento_blocks: [
    {
      id: "summary-1",
      title: "Discovery",
      type: "summary",
      severity: "green",
      score: 82,
      short_text: "Хорошее раскрытие контекста.",
      detail: "Менеджер уточнил роль, процесс и критерии решения.",
      evidence_turn_indexes: [1, 2],
    },
  ],
  skill_scores: [
    {
      id: "discovery",
      title: "Discovery",
      score: 84,
      severity: "green",
      explanation: "Вопросы шли в правильной последовательности.",
      evidence_turn_indexes: [1, 2],
    },
  ],
  key_strengths: [],
  key_weaknesses: [],
  missed_opportunities: [],
  recommendations: [],
  final_verdict: "Сильная попытка.",
  risk_flags: [],
};

function makeDetail(
  reportPayload: ReportPayload | null,
  overrides: Partial<Pick<HistorySessionDetailDTO, "public_brief">> & {
    session?: Partial<HistorySessionDetailDTO["session"]>;
  } = {},
): HistorySessionDetailDTO {
  return {
    session: {
      session_id: "session-123456",
      user_id: "user-1",
      user_email: "manager@example.com",
      client_account_id: "account-1",
      training_config_id: "config-1",
      scenario_id: "generic_b2b_first_contact",
      status: "finished",
      started_at: "2026-05-08T06:00:00Z",
      finished_at: "2026-05-08T06:30:00Z",
      last_activity_at: "2026-05-08T06:30:00Z",
      turn_count: 1,
      final_interest_score: 72,
      final_stage: "next_step",
      summary: "Сводка",
      ...overrides.session,
    },
    public_brief: "public_brief" in overrides ? overrides.public_brief ?? null : "Публичный бриф",
    turns: [],
    report: {
      session_id: "session-123456",
      report: "LEGACY TEXT REPORT",
      report_payload: reportPayload,
      report_version: 1,
      created_at: "2026-05-08T06:30:00Z",
      updated_at: "2026-05-08T06:30:00Z",
    },
  };
}

describe("HistoryPage summary rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders plain string summary as normal text", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(
      makeDetail(null, {
        session: { summary: "Менеджер выявил боль и договорился о следующем шаге." },
        public_brief: null,
      }),
    );

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Менеджер выявил боль и договорился о следующем шаге.")).toBeInTheDocument();
    expect(screen.getByText("Сводка тренировки")).toBeInTheDocument();
    expect(screen.queryByText(/"Менеджер выявил боль/)).not.toBeInTheDocument();
  });

  it("renders JSON object summary with readable labels and values", async () => {
    const summary = JSON.stringify({
      final_interest_score: 74,
      turn_count: 6,
      key_takeaway: "Менеджер выявил боль, но поздно зафиксировал следующий шаг",
      status: "finished",
      scenario_id: "generic_b2b_first_contact",
    });
    apiMocks.getHistorySessionDetail.mockResolvedValue(makeDetail(null, { session: { summary }, public_brief: null }));

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Итоговый интерес")).toBeInTheDocument();
    expect(screen.getByText("74")).toBeInTheDocument();
    expect(screen.getByText("Сообщений")).toBeInTheDocument();
    expect(screen.getByText("6")).toBeInTheDocument();
    expect(screen.getByText("Ключевой вывод")).toBeInTheDocument();
    expect(screen.getByText("Менеджер выявил боль, но поздно зафиксировал следующий шаг")).toBeInTheDocument();
    expect(screen.getAllByText("Завершена").length).toBeGreaterThan(0);
    expect(screen.getByText("Первичный контакт и разведка")).toBeInTheDocument();
    expect(screen.queryByText("final_interest_score")).not.toBeInTheDocument();
    expect(screen.queryByText("generic_b2b_first_contact")).not.toBeInTheDocument();
    expect(screen.queryByText(summary)).not.toBeInTheDocument();
  });

  it("renders invalid JSON summary as safe plain text", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(
      makeDetail(null, { session: { summary: "{bad json" }, public_brief: null }),
    );

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("{bad json")).toBeInTheDocument();
  });

  it("renders an empty state when summary is missing or empty", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(makeDetail(null, { session: { summary: "" }, public_brief: null }));

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Сводка тренировки пока недоступна.")).toBeInTheDocument();
  });

  it("renders public brief only when it is present", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(
      makeDetail(null, {
        session: { summary: "Короткая сводка" },
        public_brief: "Контекст для менеджера",
      }),
    );

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Контекст тренировки")).toBeInTheDocument();
    expect(screen.getByText("Контекст для менеджера")).toBeInTheDocument();
  });

  it("does not render public brief block when it is missing", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(
      makeDetail(null, {
        session: { summary: "Короткая сводка" },
        public_brief: null,
      }),
    );

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    await screen.findByText("Короткая сводка");
    expect(screen.queryByText("Контекст тренировки")).not.toBeInTheDocument();
  });
});

describe("HistoryPage report rendering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render legacy report text when structured payload is valid", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(makeDetail(structuredReportPayload));

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Менеджер качественно провёл discovery.")).toBeInTheDocument();
    expect(screen.queryByText("LEGACY TEXT REPORT")).not.toBeInTheDocument();
  });

  it("renders fallback report text when payload is missing", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(makeDetail(null));

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Текстовая версия отчёта")).toBeInTheDocument();
    expect(screen.getByText("LEGACY TEXT REPORT")).toBeInTheDocument();
  });

  it("renders fallback report text when payload is invalid", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(makeDetail({ unexpected: true }));

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Текстовая версия отчёта")).toBeInTheDocument();
    expect(screen.getByText("LEGACY TEXT REPORT")).toBeInTheDocument();
  });
});
