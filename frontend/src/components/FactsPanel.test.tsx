import { render, screen } from "@testing-library/react";
import { FactsPanel } from "./FactsPanel";

describe("FactsPanel", () => {
  it("renders only revealed facts and ignores legacy discovered fields", () => {
    render(
      <FactsPanel
        state={{
          discovered_role: "cfo",
          discovered_authority_level: "final_decider",
          known_pains: ["hidden pain"],
          buying_signals: ["hidden signal"],
          revealed_facts: [],
        }}
      />,
    );

    expect(screen.getByText(/Пока фактов мало/)).toBeInTheDocument();
    expect(screen.queryByText("cfo")).not.toBeInTheDocument();
    expect(screen.queryByText("hidden pain")).not.toBeInTheDocument();
  });

  it("groups readable revealed facts and filters technical values", () => {
    render(
      <FactsPanel
        state={{
          revealed_facts: [
            { category: "role", text: "финансовый директор", turn_index: 1 },
            { category: "authority", text: "final_decider", turn_index: 1 },
            { category: "constraint", text: "current_vendor_loyalty", turn_index: 2 },
            { category: "pain", text: "долго собираем отчётность", turn_index: 2 },
          ],
        }}
      />,
    );

    expect(screen.getByText("Роль")).toBeInTheDocument();
    expect(screen.getByText("финансовый директор")).toBeInTheDocument();
    expect(screen.getByText("Выявленные боли")).toBeInTheDocument();
    expect(screen.getByText("долго собираем отчётность")).toBeInTheDocument();
    expect(screen.queryByText("final_decider")).not.toBeInTheDocument();
    expect(screen.queryByText("current_vendor_loyalty")).not.toBeInTheDocument();
  });
});
