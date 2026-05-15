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
  getTrainingConfigs: vi.fn<() => Promise<{ id: string; name: string; is_default: boolean }[]>>(),
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

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
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
  public_brief: "Краткий бриф",
  stage: "closed",
  interest: { score: 74, band: "warm" },
  client_state_public: {},
  facts_panel: { items: [] },
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

const trainerStorageKey = "salestrainer.currentSessionId.user-1";

const makeTurn = (turnIndex: number) => ({
  turn_index: turnIndex,
  manager_message: `Вопрос ${turnIndex}`,
  client_answer: `Ответ ${turnIndex}`,
  interest_before: 40 + turnIndex,
  interest_delta: 1,
  interest_after: 41 + turnIndex,
  stage_before: "discovery",
  stage_after: "discovery",
  created_at: `2026-05-08T00:${turnIndex.toString().padStart(2, "0")}:00Z`,
});

describe("TrainerPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    apiMocks.getTrainingConfigs.mockResolvedValue([
      { id: "config-1", name: "B2B discovery", is_default: true },
    ]);
  });

  it("renders the trainer chat panel without phone shell markup and clears report state on new session", async () => {
    const user = userEvent.setup();

    localStorage.setItem(trainerStorageKey, finishedSession.session_id);

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

    const { container } = render(<TrainerPage userId="user-1" />);

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
    expect(apiMocks.createSession).toHaveBeenCalledWith("config-1");
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Открыть итоговый отчёт" })).not.toBeInTheDocument();
    });
    expect(screen.queryByRole("dialog", { name: "Итоговый отчёт" })).not.toBeInTheDocument();
    expect(container.querySelector(".trainer-report-rail")).not.toBeInTheDocument();
  });

  it("opens the report modal immediately after finish returns a report payload", async () => {
    const user = userEvent.setup();

    localStorage.setItem(trainerStorageKey, activeSession.session_id);

    apiMocks.getSession.mockResolvedValue({
      session: activeSession,
      turns: [],
    });
    apiMocks.finishSession.mockResolvedValue({
      session: finishedSession,
      report: "Финальная текстовая версия отчёта",
      report_payload: structuredReportPayload,
    });

    render(<TrainerPage userId="user-1" />);

    const finishButton = await screen.findByRole("button", { name: "Завершить" });
    await user.click(finishButton);

    expect(await screen.findByRole("dialog", { name: "Итоговый отчёт" })).toBeInTheDocument();
    expect(apiMocks.finishSession).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Структурированная оценка")).toBeInTheDocument();
    expect(screen.getByText("Менеджер качественно провёл discovery.")).toBeInTheDocument();
  });

  it("keeps the error banner inside trainer-chat-body while composer remains a direct panel child", async () => {
    const user = userEvent.setup();

    localStorage.setItem(trainerStorageKey, activeSession.session_id);

    apiMocks.getSession.mockResolvedValue({
      session: activeSession,
      turns: [],
    });
    apiMocks.sendMessage.mockRejectedValue(new Error("Сервис временно недоступен"));

    const { container } = render(<TrainerPage userId="user-1" />);

    const textarea = await screen.findByPlaceholderText("Введите сообщение клиенту");
    await user.type(textarea, "Привет");
    await user.click(screen.getByRole("button", { name: "Отправить сообщение" }));

    const errorBanner = await screen.findByText("Сервис временно недоступен");
    const trainerChatPanel = container.querySelector(".trainer-chat-panel");
    const trainerChatBody = container.querySelector(".trainer-chat-body");
    const composer = container.querySelector(".composer");
    const chatWindow = container.querySelector(".chat-window");

    expect(trainerChatPanel).not.toBeNull();
    expect(trainerChatBody).not.toBeNull();
    expect(chatWindow).not.toBeNull();
    expect(composer).not.toBeNull();
    expect(container.querySelector(".phone-shell")).not.toBeInTheDocument();
    expect(container.querySelector(".trainer-report-rail")).not.toBeInTheDocument();
    expect(trainerChatBody).toContainElement(errorBanner);
    expect(trainerChatBody).toContainElement(chatWindow as HTMLElement);
    expect(trainerChatPanel?.lastElementChild).toBe(composer);
  });

  it("reuses the same idempotency key when the same failed message is retried", async () => {
    const user = userEvent.setup();
    const randomUuid = vi.fn()
      .mockReturnValueOnce("msg-key-1")
      .mockReturnValueOnce("msg-key-2");
    const originalCrypto = globalThis.crypto;
    try {
      Object.defineProperty(globalThis, "crypto", {
        configurable: true,
        value: {
          ...originalCrypto,
          randomUUID: randomUuid,
        },
      });

      localStorage.setItem(trainerStorageKey, activeSession.session_id);

      apiMocks.getSession.mockResolvedValue({
        session: activeSession,
        turns: [],
      });
      apiMocks.sendMessage
        .mockRejectedValueOnce(new Error("network down"))
        .mockResolvedValueOnce({
          session: activeSession,
          turns: [makeTurn(1)],
          client_answer: "Ответ 1",
          interest_before: 41,
          interest_delta: 1,
          interest_after: 42,
          stage_before: "discovery",
          stage_after: "discovery",
          turn_index: 1,
        });

      const { container } = render(<TrainerPage userId="user-1" />);

      const textarea = await screen.findByRole("textbox");
      const sendButton = container.querySelector(".composer__send");
      expect(sendButton).not.toBeNull();
      await user.type(textarea, "Привет");
      await user.click(sendButton as HTMLElement);
      await screen.findByText("network down");
      await user.click(sendButton as HTMLElement);

      expect(apiMocks.sendMessage).toHaveBeenNthCalledWith(1, activeSession.session_id, "Привет", "msg-key-1");
      expect(apiMocks.sendMessage).toHaveBeenNthCalledWith(2, activeSession.session_id, "Привет", "msg-key-1");
      expect(randomUuid).toHaveBeenCalledTimes(1);
    } finally {
      Object.defineProperty(globalThis, "crypto", {
        configurable: true,
        value: originalCrypto,
      });
    }
  });

  it("keeps chat-window inside trainer-chat-body for long conversations", async () => {
    localStorage.setItem(trainerStorageKey, activeSession.session_id);

    apiMocks.getSession.mockResolvedValue({
      session: activeSession,
      turns: Array.from({ length: 32 }, (_, index) => makeTurn(index + 1)),
    });

    const { container } = render(<TrainerPage userId="user-1" />);

    await screen.findByText("Ответ 32");

    const trainerChatPanel = container.querySelector(".trainer-chat-panel");
    const trainerChatBody = container.querySelector(".trainer-chat-body");
    const chatWindow = container.querySelector(".chat-window");
    const composer = container.querySelector(".composer");

    expect(trainerChatPanel).not.toBeNull();
    expect(trainerChatBody).not.toBeNull();
    expect(chatWindow).not.toBeNull();
    expect(composer).not.toBeNull();
    expect(trainerChatBody).toContainElement(chatWindow as HTMLElement);
    expect(trainerChatBody?.nextElementSibling).toBe(composer);
    expect(trainerChatPanel).toContainElement(trainerChatBody as HTMLElement);
  });

  it("shows config selector on start screen and passes selected config to createSession", async () => {
    const user = userEvent.setup();

    apiMocks.getTrainingConfigs.mockResolvedValue([
      { id: "config-1", name: "B2B discovery", is_default: true },
      { id: "config-2", name: "Objection practice", is_default: false },
    ]);
    apiMocks.createSession.mockResolvedValue({
      session: {
        ...activeSession,
        session_id: "session-2",
        training_config_id: "config-2",
      },
    });

    render(<TrainerPage userId="user-1" />);

    const select = await screen.findByRole("combobox", { name: /сценарий/i });
    expect(select).toBeInTheDocument();
    expect(screen.getByText("B2B discovery")).toBeInTheDocument();

    await user.selectOptions(select, "config-2");
    await user.click(screen.getByRole("button", { name: "Начать тренировку" }));

    await waitFor(() => {
      expect(apiMocks.createSession).toHaveBeenCalledWith("config-2");
    });
  });

  it("shows error and disables start button when training configs fail to load", async () => {
    apiMocks.getTrainingConfigs.mockRejectedValue(new Error("Network error"));

    render(<TrainerPage userId="user-1" />);

    expect(await screen.findByText(/Настройки тренировки недоступны/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Начать тренировку" })).toBeDisabled();
  });
});
