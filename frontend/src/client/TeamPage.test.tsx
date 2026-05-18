import { render, screen } from "@testing-library/react";
import { TeamPage } from "./TeamPage";
import type { TeamUserDTO } from "./types";

const apiMocks = vi.hoisted(() => ({
  getTeamUsers: vi.fn(),
  getTeamUserDetail: vi.fn(),
}));

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getTeamUsers: apiMocks.getTeamUsers,
    getTeamUserDetail: apiMocks.getTeamUserDetail,
  };
});

function makeUser(overrides: Partial<TeamUserDTO> = {}): TeamUserDTO {
  return {
    id: "user-1",
    email: "manager@example.com",
    role: "client_manager",
    is_active: true,
    total_sessions: 4,
    finished_sessions: 3,
    avg_final_interest_score: 71.5,
    last_activity_at: "2026-05-15T10:00:00Z",
    ...overrides,
  };
}

describe("TeamPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render a password-change badge in the client team table", async () => {
    apiMocks.getTeamUsers.mockResolvedValue([makeUser()]);

    const { container } = render(<TeamPage onNavigate={vi.fn()} />);

    expect(await screen.findByText("manager@example.com")).toBeInTheDocument();
    expect(screen.queryByText("смена пароля")).not.toBeInTheDocument();
    expect(container.textContent).not.toContain("must_change_password");
  });
});
