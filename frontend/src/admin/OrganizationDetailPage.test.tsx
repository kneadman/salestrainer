import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrganizationDetailPage } from "./OrganizationDetailPage";
import {
  getUsageSummary,
  listAuditLog,
  listOrganizationHistory,
  listOrganizations,
  listTrainingConfigs,
  listUserTrainingConfigs,
  listUsers,
} from "./api";
import type { AuditLogDTO, HistorySessionSummaryDTO, OrganizationDTO, TrainingConfigDTO, UsageSummaryDTO } from "./types";

vi.mock("./api", async () => {
  const actual = await vi.importActual<typeof import("./api")>("./api");
  return {
    ...actual,
    getUsageSummary: vi.fn(),
    listAuditLog: vi.fn(),
    listOrganizationHistory: vi.fn(),
    listOrganizations: vi.fn(),
    listTrainingConfigs: vi.fn(),
    listUserTrainingConfigs: vi.fn(),
    listUsers: vi.fn(),
  };
});

const organization: OrganizationDTO = {
  id: "org-1",
  name: "Acme",
  slug: "acme",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
  users_count: 0,
  active_users_count: 0,
  training_configs_count: 1,
};

const trainingConfig: TrainingConfigDTO = {
  id: "config-1",
  client_account_id: "org-1",
  name: "Existing config",
  is_active: true,
  default_scenario_id: "qualification_and_authority",
  persona_generation_context: "Existing persona context",
  persona_policy: { hidden: true },
  ui_config: { theme: "internal" },
  limits: { turns: 8 },
  llm_provider_config_id: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

function setupApiMocks(): void {
  vi.mocked(listOrganizations).mockResolvedValue([organization]);
  vi.mocked(listUsers).mockResolvedValue([]);
  vi.mocked(listTrainingConfigs).mockResolvedValue([trainingConfig]);
  vi.mocked(listOrganizationHistory).mockResolvedValue([] as HistorySessionSummaryDTO[]);
  vi.mocked(getUsageSummary).mockResolvedValue(null as unknown as UsageSummaryDTO);
  vi.mocked(listAuditLog).mockResolvedValue([] as AuditLogDTO[]);
  vi.mocked(listUserTrainingConfigs).mockResolvedValue([]);
}

async function renderConfigsTab(): Promise<ReturnType<typeof userEvent.setup>> {
  const user = userEvent.setup();
  render(<OrganizationDetailPage organizationId="org-1" onNavigate={vi.fn()} />);

  await user.click(await screen.findByRole("button", { name: "Настройки" }));
  await screen.findByText("Existing config");
  return user;
}

describe("OrganizationDetailPage training configs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupApiMocks();
  });

  it("hides legacy training config fields from the form", async () => {
    await renderConfigsTab();

    expect(screen.queryByText("Формат тренировки")).not.toBeInTheDocument();
    expect(screen.queryByText("Дополнительные правила личности")).not.toBeInTheDocument();
    expect(screen.queryByText("Настройки интерфейса")).not.toBeInTheDocument();
    expect(screen.queryByText("Лимиты")).not.toBeInTheDocument();
  });

  it("removes the format column from the configs table", async () => {
    await renderConfigsTab();

    expect(screen.queryByRole("columnheader", { name: "Формат" })).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Название" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Контекст" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Статус" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Действия" })).toBeInTheDocument();
  });

  it("fills only visible fields when editing an existing config", async () => {
    const user = await renderConfigsTab();
    const editButton = screen
      .getAllByRole("button")
      .find((button) => button.textContent?.includes("Изменить"));

    expect(editButton).toBeDefined();
    await user.click(editButton as HTMLButtonElement);

    await waitFor(() => {
      expect(screen.getByDisplayValue("Existing config")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Existing persona context")).toBeInTheDocument();
    });
    expect(screen.queryByText("Дополнительные правила личности")).not.toBeInTheDocument();
    expect(screen.queryByText("Настройки интерфейса")).not.toBeInTheDocument();
    expect(screen.queryByText("Лимиты")).not.toBeInTheDocument();
  });
});
