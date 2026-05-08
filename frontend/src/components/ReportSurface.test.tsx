import { render, screen } from "@testing-library/react";
import type { JudgeSessionOutputDTO, ReportPayload } from "../types";
import { ReportSurface } from "./ReportSurface";

const validPayload: JudgeSessionOutputDTO = {
  schema_version: 1,
  overall_score: 81,
  overall_grade: "good",
  outcome: "meeting",
  executive_summary: "Менеджер собрал хороший discovery.",
  bento_blocks: [
    {
      id: "summary-1",
      title: "Discovery",
      type: "summary",
      severity: "green",
      score: 81,
      short_text: "Есть контекст и критерии.",
      detail: "Менеджер уточнил текущий процесс и критерии выбора.",
      evidence_turn_indexes: [1, 2],
    },
  ],
  skill_scores: [
    {
      id: "discovery",
      title: "Discovery",
      score: 83,
      severity: "green",
      explanation: "Вопросы были уместны.",
      evidence_turn_indexes: [1],
    },
  ],
  key_strengths: [],
  key_weaknesses: [],
  missed_opportunities: [],
  recommendations: [
    {
      title: "Следующий шаг",
      description: "Фиксируйте конкретный слот в календаре.",
      example_phrase: "Предлагаю подтвердить созвон на четверг.",
      priority: "medium",
    },
  ],
  final_verdict: "Сильная попытка.",
  risk_flags: [],
};

describe("ReportSurface", () => {
  it("renders only the structured report when payload is valid", () => {
    render(<ReportSurface report="LEGACY RAW REPORT" reportPayload={validPayload} />);

    expect(screen.getByText("Менеджер собрал хороший discovery.")).toBeInTheDocument();
    expect(screen.queryByText("LEGACY RAW REPORT")).not.toBeInTheDocument();
    expect(screen.queryByText("Текстовая версия отчёта")).not.toBeInTheDocument();
  });

  it("renders fallback text when payload is missing", () => {
    render(<ReportSurface report="Текстовый отчёт" reportPayload={null} />);

    expect(screen.getByText("Текстовая версия отчёта")).toBeInTheDocument();
    expect(screen.getByText("Текстовый отчёт")).toBeInTheDocument();
  });

  it("renders fallback text when payload is invalid", () => {
    const invalidPayload = { ...validPayload } as Partial<JudgeSessionOutputDTO>;
    delete invalidPayload.recommendations;

    render(<ReportSurface report="Текстовый fallback" reportPayload={invalidPayload as ReportPayload} />);

    expect(screen.getByText("Текстовая версия отчёта")).toBeInTheDocument();
    expect(screen.getByText("Текстовый fallback")).toBeInTheDocument();
    expect(screen.queryByText("Менеджер собрал хороший discovery.")).not.toBeInTheDocument();
  });
});
