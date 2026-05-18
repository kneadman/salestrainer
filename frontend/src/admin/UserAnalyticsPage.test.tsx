import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AdminUserAnalyticsPage } from "./UserAnalyticsPage";
import { getOrganizationUserAnalytics } from "./api";
import type { AdminUserAnalyticsDetailDTO } from "./types";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getOrganizationUserAnalytics: vi.fn(),
  };
});

const detail: AdminUserAnalyticsDetailDTO = {
  user: {
    id: "user-1",
    client_account_id: "org-1",
    email: "manager@example.com",
    role: "client_manager",
    is_active: true,
    must_change_password: false,
    created_at: "2026-05-01T10:00:00Z",
    updated_at: "2026-05-02T10:00:00Z",
    client_account: {
      id: "org-1",
      name: "Acme",
      slug: "acme",
    },
  },
  analytics: {
    user_id: "user-1",
    user_email: "manager@example.com",
    total_sessions: 12,
    finished_sessions: 9,
    active_sessions: 3,
    completion_rate: 0.75,
    avg_final_interest_score: 68.4,
    avg_turn_count: 4.2,
    avg_judgement_score: 7.6,
    sessions_with_judgement: 8,
    weakest_skill_id: "diagnosis",
    weakest_skill_title: "Качество диагностики",
    weakest_skill_avg_score: 5.1,
    strongest_skill_id: "next_step",
    strongest_skill_title: "Следующий шаг",
    strongest_skill_avg_score: 8.4,
    last_activity_at: "2026-05-08T19:23:00Z",
    sessions_by_status: {
      finished: 9,
      active: 3,
    },
    sessions_by_scenario: {
      first_contact_discovery: 7,
      objection_handling: 5,
    },
    trends_7d: {
      total_sessions: { current_7d: 4, previous_7d: 2, delta: 2, delta_percent: 100, direction: "up" },
      finished_sessions: { current_7d: 3, previous_7d: 1, delta: 2, delta_percent: 200, direction: "up" },
      completion_rate: { current_7d: 0.75, previous_7d: 0.5, delta: 0.25, delta_percent: 50, direction: "up" },
      avg_final_interest_score: { current_7d: 71, previous_7d: 64, delta: 7, delta_percent: 10.9, direction: "up" },
      avg_turn_count: { current_7d: 4.5, previous_7d: 3.5, delta: 1, delta_percent: 28.6, direction: "up" },
      avg_judgement_score: { current_7d: 7.8, previous_7d: 6.4, delta: 1.4, delta_percent: 21.9, direction: "up" },
      sessions_with_judgement: { current_7d: 2, previous_7d: 1, delta: 1, delta_percent: 100, direction: "up" },
    },
  },
  history: [
    {
      session_id: "session-1",
      user_id: "user-1",
      user_email: "manager@example.com",
      client_account_id: "org-1",
      training_config_id: "config-1",
      training_config_name: "B2B discovery",
      scenario_id: "first_contact_discovery",
      status: "finished",
      started_at: "2026-05-08T19:23:00Z",
      finished_at: "2026-05-08T19:40:00Z",
      last_activity_at: "2026-05-08T19:40:00Z",
      turn_count: 5,
      final_interest_score: 74,
      final_stage: "proposal",
      summary: "summary",
    },
  ],
};

describe("AdminUserAnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders user analytics, trend labels, and recent history links", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    vi.mocked(getOrganizationUserAnalytics).mockResolvedValue(detail);

    render(<AdminUserAnalyticsPage organizationId="org-1" userId="user-1" onNavigate={onNavigate} />);

    expect(await screen.findByRole("heading", { name: "manager@example.com" })).toBeInTheDocument();
    expect(screen.getByText("Всего тренировок")).toBeInTheDocument();
    expect(screen.getByText("Завершено")).toBeInTheDocument();
    expect(screen.getByText("Активные")).toBeInTheDocument();
    expect(screen.getByText("Средняя оценка тренировки")).toBeInTheDocument();
    expect(screen.getByText("Сильнейший навык")).toBeInTheDocument();
    expect(screen.getByText("Следующий шаг")).toBeInTheDocument();
    expect(screen.getByText("Зона роста")).toBeInTheDocument();
    expect(screen.getByText("Качество диагностики")).toBeInTheDocument();
    expect(screen.getAllByText(/за 7 дней/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Δ \+2 к прошлым 7 дням/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Последние тренировки" })).toBeInTheDocument();
    expect(screen.getAllByText("Первичный контакт и разведка").length).toBeGreaterThan(0);
    expect(screen.queryByText("first_contact_discovery")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Открыть" }));
    expect(onNavigate).toHaveBeenCalledWith("/admin/history/sessions/session-1");
  });

  it("navigates back to the organization users tab", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    vi.mocked(getOrganizationUserAnalytics).mockResolvedValue(detail);

    render(<AdminUserAnalyticsPage organizationId="org-1" userId="user-1" onNavigate={onNavigate} />);

    await user.click(await screen.findByRole("button", { name: "← Пользователи" }));

    expect(onNavigate).toHaveBeenCalledWith("/admin/organizations/org-1?tab=users");
  });

  it("renders error state when the analytics endpoint fails", async () => {
    vi.mocked(getOrganizationUserAnalytics).mockRejectedValue(new Error("boom"));

    render(<AdminUserAnalyticsPage organizationId="org-1" userId="user-1" onNavigate={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("Аналитика пользователя недоступна")).toBeInTheDocument();
      expect(screen.getByText("boom")).toBeInTheDocument();
    });
  });
});
