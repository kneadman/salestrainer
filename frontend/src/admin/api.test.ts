import { request } from "../apiClient";
import { createTrainingConfig, updateTrainingConfig } from "./api";

vi.mock("../apiClient", () => ({
  request: vi.fn(),
}));

describe("training config API payloads", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(request).mockResolvedValue({} as never);
  });

  it("createTrainingConfig sends only visible fields", async () => {
    await createTrainingConfig("org-1", {
      name: "Sales discovery",
      persona_generation_context: "CFO buyers with budget objections",
    });

    expect(request).toHaveBeenCalledWith("/api/internal/organizations/org-1/training-configs", {
      method: "POST",
      body: JSON.stringify({
        name: "Sales discovery",
        persona_generation_context: "CFO buyers with budget objections",
      }),
    });
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("default_scenario_id");
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("persona_policy");
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("ui_config");
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("limits");
  });

  it("updateTrainingConfig sends only visible fields", async () => {
    await updateTrainingConfig("config-1", {
      name: "Updated discovery",
      persona_generation_context: "Updated context",
    });

    expect(request).toHaveBeenCalledWith("/api/internal/training-configs/config-1", {
      method: "PATCH",
      body: JSON.stringify({
        name: "Updated discovery",
        persona_generation_context: "Updated context",
      }),
    });
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("default_scenario_id");
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("persona_policy");
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("ui_config");
    expect(JSON.parse(vi.mocked(request).mock.calls[0][1]?.body as string)).not.toHaveProperty("limits");
  });
});
