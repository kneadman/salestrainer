import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TrainerPage } from "./TrainerPage";
import type {
  FinishSessionResponse,
  SessionDetailResponse,
  SessionReportResponse,
  SessionStateResponse,
} from "../types";

const apiMocks = vi.hoisted(() => ({
  createSession: vi.fn<() => Promise<SessionStateResponse>>(),
  getSession: vi.fn<(sessionId: string) => Promise<SessionDetailResponse>>(),
  getReport: vi.fn<(sessionId: string) => Promise<SessionReportResponse>>(),
  finishSession: vi.fn<() => Promise<FinishSessionResponse>>(),
  sendMessage: vi.fn(),
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
  };
});

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

describe("TrainerPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("restores a finished session, opens the report modal, and clears report state on new session", async () => {
    const user = userEvent.setup();

    localStorage.setItem("salestrainer.currentSessionId", finishedSession.session_id);

    apiMocks.getSession.mockResolvedValue({
      session: finishedSession,
      turns: [],
    });
    apiMocks.getReport.mockResolvedValue({
      session: finishedSession,
      report: "Сильные стороны менеджера",
      report_payload: null,
    });
    apiMocks.createSession.mockResolvedValue({
      session: {
        ...finishedSession,
        session_id: "session-2",
        status: "active",
      },
    });

    const { container } = render(<TrainerPage onLogout={vi.fn().mockResolvedValue(undefined)} />);

    const reportButton = await screen.findByRole("button", { name: "Открыть итоговый отчёт" });
    expect(reportButton).toBeInTheDocument();
    expect(container.querySelector(".trainer-report-rail")).not.toBeInTheDocument();

    await user.click(reportButton);

    expect(await screen.findByRole("dialog", { name: "Итоговый отчёт" })).toBeInTheDocument();
    expect(screen.getByText("Сильные стороны менеджера")).toBeInTheDocument();

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
});
