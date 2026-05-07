import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TrainerPage } from "./TrainerPage";
import type {
  FinishSessionResponse,
  JudgeSessionOutputDTO,
  SessionDetailResponse,
  SessionReportResponse,
  SessionStateResponse,
  SpeechTranscriptionResponse,
} from "../types";

const apiMocks = vi.hoisted(() => ({
  createSession: vi.fn<() => Promise<SessionStateResponse>>(),
  getSession: vi.fn<(sessionId: string) => Promise<SessionDetailResponse>>(),
  getReport: vi.fn<(sessionId: string) => Promise<SessionReportResponse>>(),
  finishSession: vi.fn<() => Promise<FinishSessionResponse>>(),
  sendMessage: vi.fn(),
  transcribeSpeech: vi.fn<() => Promise<SpeechTranscriptionResponse>>(),
}));

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    createSession: apiMocks.createSession,
    getSession: apiMocks.getSession,
    getReport: apiMocks.getReport,
    finishSession: apiMocks.finishSession,
    sendMessage: apiMocks.sendMessage,
    transcribeSpeech: apiMocks.transcribeSpeech,
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
  recommendations: [
    {
      title: "Усилить следующий шаг",
      description: "Закрепляйте договорённость конкретной датой.",
      example_phrase: "Давайте зафиксируем короткий созвон на четверг.",
      priority: "medium",
    },
  ],
  final_verdict: "Сильная попытка.",
  risk_flags: [],
};

const finishedSession = {
  session_id: "session-1",
  scenario_id: "cold-b2b",
  status: "finished",
  persona_name: "Ирина",
  public_brief: "Краткий бриф",
  stage: "closed",
  interest: { score: 74, band: "warm" },
  client_state_public: {},
  turn_count: 2,
  summary: "Финальная сводка",
  state_version: 3,
};

const activeSession = {
  ...finishedSession,
  session_id: "session-active",
  status: "active",
  stage: "discovery",
};

describe("TrainerPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("renders the trainer chat panel without phone shell markup and clears report state on new session", async () => {
    const user = userEvent.setup();

    localStorage.setItem("salestrainer.currentSessionId", finishedSession.session_id);

    apiMocks.getSession.mockResolvedValue({
      session: finishedSession,
      turns: [],
    });
    apiMocks.getReport.mockResolvedValue({
      session: finishedSession,
      report: "Сильные стороны менеджера",
      report_payload: structuredReportPayload,
    });
    apiMocks.createSession.mockResolvedValue({
      session: {
        ...activeSession,
        session_id: "session-2",
      },
    });

    const { container } = render(<TrainerPage onLogout={vi.fn().mockResolvedValue(undefined)} />);

    const reportButton = await screen.findByRole("button", { name: "Открыть итоговый отчёт" });
    expect(reportButton).toBeInTheDocument();
    expect(container.querySelector(".trainer-chat-panel")).toBeInTheDocument();
    expect(container.querySelector(".phone-shell")).not.toBeInTheDocument();
    expect(container.querySelector(".trainer-report-rail")).not.toBeInTheDocument();

    await user.click(reportButton);

    expect(await screen.findByRole("dialog", { name: "Итоговый отчёт" })).toBeInTheDocument();
    expect(screen.getByText("Структурированная оценка")).toBeInTheDocument();
    expect(screen.getByText("Менеджер качественно провёл discovery.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Новая тренировка" }));

    await waitFor(() => {
      expect(apiMocks.createSession).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Открыть итоговый отчёт" })).not.toBeInTheDocument();
    });
    expect(screen.queryByRole("dialog", { name: "Итоговый отчёт" })).not.toBeInTheDocument();
    expect(container.querySelector(".trainer-report-rail")).not.toBeInTheDocument();
  });

  it("opens the report modal immediately after finish returns a report payload", async () => {
    const user = userEvent.setup();

    localStorage.setItem("salestrainer.currentSessionId", activeSession.session_id);

    apiMocks.getSession.mockResolvedValue({
      session: activeSession,
      turns: [],
    });
    apiMocks.finishSession.mockResolvedValue({
      session: finishedSession,
      report: "Финальная текстовая версия отчёта",
      report_payload: structuredReportPayload,
    });

    render(<TrainerPage onLogout={vi.fn().mockResolvedValue(undefined)} />);

    const finishButton = await screen.findByRole("button", { name: "Завершить" });
    await user.click(finishButton);

    expect(await screen.findByRole("dialog", { name: "Итоговый отчёт" })).toBeInTheDocument();
    expect(apiMocks.finishSession).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Структурированная оценка")).toBeInTheDocument();
    expect(screen.getByText("Менеджер качественно провёл discovery.")).toBeInTheDocument();
  });
});
