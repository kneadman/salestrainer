import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TokenUsageChart, TokenUsageLegend, buildDateRange } from "./TokenUsageChart";

const mockSnapshots = [
  { snapshot_date: "2026-05-15", total_tokens: 1200, input_tokens: 700, output_tokens: 500 },
  { snapshot_date: "2026-05-16", total_tokens: 1500, input_tokens: 800, output_tokens: 700 },
  { snapshot_date: "2026-05-17", total_tokens: 1000, input_tokens: 600, output_tokens: 400 },
];

describe("TokenUsageChart", () => {
  it("renders message when no snapshots", () => {
    render(<TokenUsageChart snapshots={[]} />);
    expect(screen.getByText(/Нет данных за выбранный период/i)).toBeInTheDocument();
  });

  it("renders SVG chart when snapshots provided", () => {
    render(<TokenUsageChart snapshots={mockSnapshots} />);
    const svg = document.querySelector("svg.admin-svg-chart");
    expect(svg).toBeInTheDocument();
    expect(svg?.querySelectorAll("circle").length).toBeGreaterThan(0);
  });
});

describe("TokenUsageLegend", () => {
  it("renders three legend items", () => {
    render(<TokenUsageLegend />);
    expect(screen.getByText("Всего")).toBeInTheDocument();
    expect(screen.getByText("Input")).toBeInTheDocument();
    expect(screen.getByText("Output")).toBeInTheDocument();
  });
});

describe("buildDateRange", () => {
  it("returns today range", () => {
    const result = buildDateRange("today", "", "");
    expect(result.from_date).toBe(result.to_date);
  });

  it("returns yesterday range", () => {
    const result = buildDateRange("yesterday", "", "");
    expect(result.from_date).toBe(result.to_date);
    expect(result.from_date).not.toBe(new Date().toISOString().slice(0, 10));
  });

  it("returns week range", () => {
    const result = buildDateRange("week", "", "");
    expect(result.from_date).not.toBe(result.to_date);
  });

  it("returns custom range", () => {
    const result = buildDateRange("custom", "2026-01-01", "2026-01-10");
    expect(result.from_date).toBe("2026-01-01");
    expect(result.to_date).toBe("2026-01-10");
  });
});
