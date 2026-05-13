import { render, screen, waitFor } from "@testing-library/react";
import { AuditLogPage } from "./AuditLogPage";
import { listAuditLog, listOrganizations } from "./api";
import type { AuditLogDTO, OrganizationDTO } from "./types";

vi.mock("./api", () => ({
  listAuditLog: vi.fn(),
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

const auditEvent: AuditLogDTO = {
  id: "audit-1",
  actor_user_id: "user-1",
  action: "config_assigned",
  entity_type: "client_training_config",
  entity_id: "config-1",
  payload: {
    email: "manager@example.com",
    default: true,
    entity_id: "config-1",
    actor_user_id: "user-1",
  },
  ip_address: null,
  user_agent: null,
  created_at: "2026-05-13T06:30:00Z",
};

describe("AuditLogPage", () => {
  beforeEach(() => {
    vi.mocked(listOrganizations).mockResolvedValue([organization]);
    vi.mocked(listAuditLog).mockResolvedValue([auditEvent]);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders audit rows and filters without raw enum text, ids, or JSON payloads", async () => {
    render(<AuditLogPage />);

    await waitFor(() => expect(screen.queryByText("Загрузка журнала аудита")).not.toBeInTheDocument());

    expect(screen.getAllByText("Настройка назначена").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Настройка тренировки").length).toBeGreaterThan(0);
    expect(screen.getByText("Пользователь: manager@example.com · Назначена по умолчанию")).toBeInTheDocument();
    expect(screen.queryByText("ID пользователя")).not.toBeInTheDocument();
    expect(screen.queryByText("config_assigned")).not.toBeInTheDocument();
    expect(screen.queryByText("client_training_config")).not.toBeInTheDocument();
    expect(screen.queryByText("user-1")).not.toBeInTheDocument();
    expect(screen.queryByText("config-1")).not.toBeInTheDocument();
    expect(screen.queryByText("Показать технические данные")).not.toBeInTheDocument();
  });
});
