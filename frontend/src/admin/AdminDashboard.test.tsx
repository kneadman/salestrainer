import { render, screen, waitFor } from "@testing-library/react";
import { AdminDashboard } from "./AdminDashboard";
import { getUsageSummary, listAuditLog, listOrganizations } from "./api";
import type { AuditLogDTO, OrganizationDTO, UsageSummaryDTO } from "./types";

vi.mock("./api", () => ({
  getUsageSummary: vi.fn(),
  listAuditLog: vi.fn(),
  listOrganizations: vi.fn(),
}));

const organization: OrganizationDTO = {
  id: "org-1",
  name: "Acme",
  slug: "acme",
  is_active: true,
  users_count: 2,
  training_configs_count: 1,
  created_at: "2026-05-13T06:00:00Z",
  updated_at: "2026-05-13T06:00:00Z",
  active_users_count: 2,
};

const usageSummary: UsageSummaryDTO = {
  total_sessions: 3,
  finished_sessions: 2,
  active_sessions: 1,
  unique_users: 2,
  total_turns: 10,
  avg_final_interest_score: 64,
  avg_turn_count: 4,
  sessions_by_status: { finished: 2, active: 1 },
  sessions_by_scenario: { first_contact_discovery: 3 },
  sessions_by_training_config: {},
  usage_events_count: 0,
};

const auditEvent: AuditLogDTO = {
  id: "audit-1",
  actor_user_id: "user-1",
  action: "training_config_created",
  entity_type: "training_config",
  entity_id: "config-1",
  payload: {},
  ip_address: null,
  user_agent: null,
  created_at: "2026-05-13T06:30:00Z",
};

describe("AdminDashboard", () => {
  beforeEach(() => {
    vi.mocked(listOrganizations).mockResolvedValue([organization]);
    vi.mocked(getUsageSummary).mockResolvedValue(usageSummary);
    vi.mocked(listAuditLog).mockResolvedValue([auditEvent]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders audit events without raw technical action, entity, or actor ids", async () => {
    render(<AdminDashboard onNavigate={vi.fn()} />);

    await waitFor(() => expect(screen.queryByText("Загрузка панели")).not.toBeInTheDocument());

    expect(screen.getByText("Настройка тренировки создана")).toBeInTheDocument();
    expect(screen.getByText("Настройка тренировки")).toBeInTheDocument();
    expect(screen.getByText("Администратор")).toBeInTheDocument();
    expect(screen.queryByText("training_config_created")).not.toBeInTheDocument();
    expect(screen.queryByText("training_config")).not.toBeInTheDocument();
    expect(screen.queryByText("user-1")).not.toBeInTheDocument();
  });
});
