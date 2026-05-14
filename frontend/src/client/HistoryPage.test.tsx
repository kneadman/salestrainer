import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HistoryPage } from "./HistoryPage";
import type { HistorySessionDetailDTO, HistorySessionSummaryDTO } from "./types";
import type { JudgeSessionOutputDTO, ReportPayload } from "../types";

const apiMocks = vi.hoisted(() => ({
  getHistorySessionDetail: vi.fn<() => Promise<HistorySessionDetailDTO>>(),
  getHistorySessions: vi.fn(),
  getTrainingConfigs: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getHistorySessionDetail: apiMocks.getHistorySessionDetail,
    getHistorySessions: apiMocks.getHistorySessions,
    getTrainingConfigs: apiMocks.getTrainingConfigs,
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
    turns?: HistorySessionDetailDTO["turns"];
  } = {},
): HistorySessionDetailDTO {
  return {
      session: {
        session_id: "session-123456",
        user_email: "manager@example.com",
        training_config_name: "B2B discovery",
        scenario_id: "generic_b2b_first_contact",
        status: "finished",
      started_at: "2026-05-08T19:23:00Z",
      finished_at: "2026-05-08T19:53:00Z",
      last_activity_at: "2026-05-08T19:53:00Z",
      turn_count: 1,
      final_interest_score: 72,
      final_stage: "next_step",
      summary: "Сводка",
      ...overrides.session,
    },
    public_brief: "public_brief" in overrides ? overrides.public_brief ?? null : "Публичный бриф",
    turns: overrides.turns ?? [],
    report: {
      session_id: "session-123456",
      report: "LEGACY TEXT REPORT",
      report_payload: reportPayload,
      report_version: 1,
      created_at: "2026-05-08T19:53:00Z",
      updated_at: "2026-05-08T19:53:00Z",
    },
  };
}

function makeSummary(overrides: Partial<HistorySessionSummaryDTO> = {}): HistorySessionSummaryDTO {
  return {
    session_id: "session-123456",
    user_email: "manager@example.com",
    training_config_name: "B2B discovery",
    scenario_id: "generic_b2b_first_contact",
    status: "finished",
    started_at: "2026-05-08T19:23:00Z",
    finished_at: "2026-05-08T19:53:00Z",
    last_activity_at: "2026-05-08T19:53:00Z",
    turn_count: 1,
    final_interest_score: 72,
    final_stage: "next_step",
    summary: "Summary",
    ...overrides,
  };
}

describe("HistoryPage list filters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getTrainingConfigs.mockResolvedValue([
      { id: "config-1", name: "B2B discovery", is_default: true },
      { id: "config-2", name: "Objection practice", is_default: false },
    ]);
  });

  it("renders training config filters and rows without raw scenario ids in visible text", async () => {
    apiMocks.getHistorySessions.mockResolvedValue([makeSummary()]);

    const { container } = render(<HistoryPage onNavigate={vi.fn()} />);

    expect(await screen.findByText("manager@example.com")).toBeInTheDocument();
    expect(container.textContent).not.toContain("generic_b2b_first_contact");
    expect(container.textContent).not.toContain("sales_audit_cold_outreach");
    expect(screen.getAllByText("B2B discovery").length).toBeGreaterThan(0);
    expect(screen.getByText("Objection practice")).toBeInTheDocument();
    expect(screen.getAllByRole("combobox")[1].textContent).not.toContain("generic_b2b_first_contact");
  });

  it("loads history with training config filters from query params", async () => {
    apiMocks.getHistorySessions.mockResolvedValue([makeSummary()]);

    render(<HistoryPage path="/app/history?status=finished&training_config_id=config-2" onNavigate={vi.fn()} />);

    expect(await screen.findByText("manager@example.com")).toBeInTheDocument();
    expect(apiMocks.getHistorySessions).toHaveBeenCalledWith({
      status: "finished",
      training_config_id: "config-2",
      limit: 100,
      offset: 0,
    });
  });

  it("navigates on filter submit without reloading history immediately", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    apiMocks.getHistorySessions.mockResolvedValue([makeSummary()]);

    render(<HistoryPage path="/app/history" onNavigate={onNavigate} />);

    expect(await screen.findByText("manager@example.com")).toBeInTheDocument();
    const initialHistoryCalls = apiMocks.getHistorySessions.mock.calls.length;
    const [statusSelect, trainingConfigSelect] = screen.getAllByRole("combobox");
    await user.selectOptions(statusSelect, "finished");
    await user.selectOptions(trainingConfigSelect, "config-2");
    await user.click(screen.getByRole("button", { name: "Применить" }));

    expect(onNavigate).toHaveBeenCalledWith("/app/history?status=finished&training_config_id=config-2", true);
    expect(apiMocks.getHistorySessions).toHaveBeenCalledTimes(initialHistoryCalls);
  });
});

describe("HistoryPage detail header and layout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the started-at date in h1 and removes the summary block", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(makeDetail(null));

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    const heading = await screen.findByRole("heading", { level: 1 });
    expect(heading.textContent).toMatch(/^Тренировка /);
    expect(heading.textContent).not.toContain("session-1");
    expect(heading.textContent).not.toContain("123456");
    expect(screen.queryByText("Сводка тренировки")).not.toBeInTheDocument();
    expect(screen.queryByText("Контекст тренировки")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ходы" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Отчёт" })).toBeInTheDocument();
  });

  it("falls back to a plain training title when started_at is unavailable", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(
      makeDetail(null, {
        session: { started_at: "" },
      }),
    );

    render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Тренировка" })).toBeInTheDocument();
  });
  it("renders turn stages through shared labels instead of raw stage ids", async () => {
    apiMocks.getHistorySessionDetail.mockResolvedValue(
      makeDetail(null, {
        turns: [
          {
            turn_index: 1,
            manager_message: "Need details?",
            client_answer: "Can discuss process.",
            interest_before: 40,
            interest_delta: 8,
            interest_after: 48,
            stage_before: "first_contact",
            stage_after: "need_discovery",
            client_state_public: null,
            evaluation: null,
            created_at: "2026-05-08T19:24:00Z",
          },
        ],
      }),
    );

    const { container } = render(<HistoryPage sessionId="session-123456" onNavigate={vi.fn()} />);

    expect(await screen.findByText("Need details?")).toBeInTheDocument();
    expect(container.textContent).not.toContain("first_contact");
    expect(container.textContent).not.toContain("need_discovery");
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
