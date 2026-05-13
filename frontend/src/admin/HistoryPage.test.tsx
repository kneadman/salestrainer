import { render, screen, waitFor } from "@testing-library/react";
import { HistoryPage } from "./HistoryPage";
import { getHistorySession, listOrganizationHistory, listOrganizations } from "./api";
import type { HistorySessionDetailDTO, HistorySessionSummaryDTO, OrganizationDTO } from "./types";

vi.mock("./api", () => ({
  getHistorySession: vi.fn(),
  listOrganizationHistory: vi.fn(),
  listOrganizations: vi.fn(),
}));

const organization: OrganizationDTO = {
  id: "org-1",
  name: "Acme",
  slug: "acme",
  is_active: true,
  created_at: "2026-05-13T06:00:00Z",
  updated_at: "2026-05-13T06:00:00Z",
  users_count: 2,
  active_users_count: 2,
  training_configs_count: 1,
};

const sessionSummary: HistorySessionSummaryDTO = {
  session_id: "session-123456789",
  user_id: "user-1",
  user_email: "manager@example.com",
  client_account_id: "org-1",
  training_config_id: "config-1",
  scenario_id: "first_contact_discovery",
  status: "finished",
  started_at: "2026-05-13T06:30:00Z",
  finished_at: "2026-05-13T06:45:00Z",
  last_activity_at: "2026-05-13T06:45:00Z",
  turn_count: 2,
  final_interest_score: 68,
  final_stage: "need_discovery",
  summary: "Менеджер провёл первичный контакт.",
};

const sessionDetail: HistorySessionDetailDTO = {
  session: sessionSummary,
  public_brief: "Краткое описание тренировки.",
  turns: [
    {
      turn_index: 1,
      manager_message: "Здравствуйте.",
      client_answer: "Добрый день.",
      interest_before: 30,
      interest_delta: 10,
      interest_after: 40,
      stage_before: "first_contact",
      stage_after: "need_discovery",
      client_state_public: null,
      evaluation: null,
      created_at: "2026-05-13T06:31:00Z",
    },
  ],
  report: null,
};

describe("HistoryPage", () => {
  beforeEach(() => {
    vi.mocked(listOrganizations).mockResolvedValue([organization]);
    vi.mocked(listOrganizationHistory).mockResolvedValue([sessionSummary]);
    vi.mocked(getHistorySession).mockResolvedValue(sessionDetail);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders history list without session ids or raw scenario filter input", async () => {
    render(<HistoryPage onNavigate={vi.fn()} />);

    await waitFor(() => expect(screen.queryByText("Загрузка истории тренировок")).not.toBeInTheDocument());

    expect(screen.queryByRole("columnheader", { name: "ID сессии" })).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Начало" })).toBeInTheDocument();
    expect(screen.getByText("manager@example.com")).toBeInTheDocument();
    expect(screen.getAllByText("Первичный контакт и разведка").length).toBeGreaterThan(0);
    expect(screen.queryByText("session-")).not.toBeInTheDocument();
    expect(screen.queryByDisplayValue("first_contact_discovery")).not.toBeInTheDocument();
  });

  it("renders history detail with readable title and stage labels", async () => {
    render(<HistoryPage sessionId="session-123456789" onNavigate={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: /Тренировка от/ })).toBeInTheDocument();
    expect(screen.getByText(/этап Первичный контакт → Выявление потребностей/)).toBeInTheDocument();
    expect(screen.queryByText(/Сессия session-/)).not.toBeInTheDocument();
    expect(screen.queryByText(/first_contact/)).not.toBeInTheDocument();
    expect(screen.queryByText(/need_discovery/)).not.toBeInTheDocument();
  });
});
