import { buildCreateTrainingConfigPayload, buildUpdateTrainingConfigPayload } from "./api";

describe("training config payload adapters", () => {
  it("adds backend-compatible legacy fields for create", () => {
    const payload = buildCreateTrainingConfigPayload({
      name: "Sales discovery",
      persona_generation_context: "CFO buyers with budget objections",
    });

    expect(payload).toEqual({
      name: "Sales discovery",
      persona_generation_context: "CFO buyers with budget objections",
      default_scenario_id: "first_contact_discovery",
      persona_policy: {},
      ui_config: {},
      limits: {},
    });
  });

  it("keeps hidden legacy fields out of update payloads", () => {
    const payload = buildUpdateTrainingConfigPayload({
      name: "Updated discovery",
      persona_generation_context: "Updated context",
    });

    expect(payload).toEqual({
      name: "Updated discovery",
      persona_generation_context: "Updated context",
    });
    expect(payload).not.toHaveProperty("default_scenario_id");
    expect(payload).not.toHaveProperty("persona_policy");
    expect(payload).not.toHaveProperty("ui_config");
    expect(payload).not.toHaveProperty("limits");
  });
});
