import { render, screen } from "@testing-library/react";
import { AnalyticsPage } from "./AnalyticsPage";
import type { ClientUserAnalyticsDTO } from "./types";

const apiMocks = vi.hoisted(() => ({
  getMyAnalytics: vi.fn<() => Promise<ClientUserAnalyticsDTO>>(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getMyAnalytics: apiMocks.getMyAnalytics,
  };
});

const analyticsFixture: ClientUserAnalyticsDTO = {
  user_id: "user-1",
  user_email: "manager@example.com",
  total_sessions: 14,
  finished_sessions: 10,
  active_sessions: 3,
  completion_rate: 10 / 14,
  avg_final_interest_score: 71.2,
  avg_turn_count: 5.4,
  avg_judgement_score: 78.3,
  sessions_with_judgement: 8,
  weakest_skill_id: "discovery_quality",
  weakest_skill_title: "Качество диагностики",
  weakest_skill_avg_score: 49.5,
  strongest_skill_id: "objection_handling",
  strongest_skill_title: "Работа с возражениями",
  strongest_skill_avg_score: 86.5,
  last_activity_at: "2026-05-08T19:23:00Z",
  sessions_by_status: {
    finished: 10,
    active: 3,
    expired: 1,
  },
  sessions_by_scenario: {
    generic_b2b_first_contact: 9,
    objection_handling: 5,
  },
  trends_7d: {
    total_sessions: { current_7d: 6, previous_7d: 4, delta: 2, delta_percent: 50, direction: "up" },
    finished_sessions: { current_7d: 5, previous_7d: 3, delta: 2, delta_percent: 66.7, direction: "up" },
    completion_rate: { current_7d: 0.83, previous_7d: 0.75, delta: 0.08, delta_percent: 10.7, direction: "up" },
    avg_final_interest_score: { current_7d: 75.2, previous_7d: 68.1, delta: 7.1, delta_percent: 10.4, direction: "up" },
    avg_turn_count: { current_7d: 4.8, previous_7d: 5.5, delta: -0.7, delta_percent: -12.7, direction: "down" },
    avg_judgement_score: { current_7d: 80.3, previous_7d: 74.1, delta: 6.2, delta_percent: 8.4, direction: "up" },
    sessions_with_judgement: { current_7d: 4, previous_7d: 2, delta: 2, delta_percent: 100, direction: "up" },
  },
};

describe("AnalyticsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the bento cards with real 7-day dynamics and keeps grouped bars below", async () => {
    apiMocks.getMyAnalytics.mockResolvedValue(analyticsFixture);

    render(<AnalyticsPage />);

    expect(await screen.findByRole("heading", { name: "Прогресс" })).toBeInTheDocument();
    expect(screen.getByText("Всего тренировок")).toBeInTheDocument();
    expect(screen.getByText("Завершено")).toBeInTheDocument();
    expect(screen.getByText("Доля завершённых")).toBeInTheDocument();
    expect(screen.getByText("Средний интерес")).toBeInTheDocument();
    expect(screen.getByText("Среднее число ходов")).toBeInTheDocument();
    expect(screen.getByText("Средняя оценка тренировки")).toBeInTheDocument();
    expect(screen.getByText("С оценкой тренировки")).toBeInTheDocument();
    expect(screen.getByText("Сильнейший навык")).toBeInTheDocument();
    expect(screen.getAllByText("Работа с возражениями").length).toBeGreaterThan(0);
    expect(screen.getByText("Зона роста")).toBeInTheDocument();
    expect(screen.getByText("Качество диагностики")).toBeInTheDocument();
    expect(screen.getByText("Последняя активность")).toBeInTheDocument();
    expect(screen.getAllByText(/за 7 дней:/i).length).toBeGreaterThan(1);
    expect(screen.getAllByText(/Δ \+2 к прошлым 7 дням/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "По статусам" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "По сценариям" })).toBeInTheDocument();
    expect(screen.getAllByText("Завершена").length).toBeGreaterThan(0);
    expect(screen.getByText("Первичный контакт и разведка")).toBeInTheDocument();
    expect(screen.queryByText("Оценки навыков")).not.toBeInTheDocument();
    expect(screen.queryByText("finished")).not.toBeInTheDocument();
    expect(screen.queryByText("generic_b2b_first_contact")).not.toBeInTheDocument();
  });

  it("shows neutral no-data labels when trend values are missing", async () => {
    apiMocks.getMyAnalytics.mockResolvedValue({
      ...analyticsFixture,
      trends_7d: {
        ...analyticsFixture.trends_7d,
        avg_judgement_score: {
          current_7d: null,
          previous_7d: null,
          delta: null,
          delta_percent: null,
          direction: "none",
        },
      },
    });

    render(<AnalyticsPage />);

    expect(await screen.findByText("Средняя оценка тренировки")).toBeInTheDocument();
    expect(screen.getAllByText("за 7 дней: —").length).toBeGreaterThan(0);
    expect(screen.getByText("нет данных за 7 дней")).toBeInTheDocument();
  });
});
