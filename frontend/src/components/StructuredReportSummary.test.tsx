import { render, screen } from "@testing-library/react";
import type { JudgeSessionOutputDTO, ReportPayload } from "../types";
import { StructuredReportSummary } from "./StructuredReportSummary";

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

describe("StructuredReportSummary", () => {
  it("shows the fallback when payload shape is not recognized", () => {
    const invalidPayload = { ...validPayload } as Partial<JudgeSessionOutputDTO>;
    delete invalidPayload.recommendations;

    render(<StructuredReportSummary payload={invalidPayload as ReportPayload} />);

    expect(screen.getByText("Структурированная оценка")).toBeInTheDocument();
    expect(screen.getByText("Структурированная оценка сохранена, но формат не распознан.")).toBeInTheDocument();
    expect(screen.queryByText("Менеджер собрал хороший discovery.")).not.toBeInTheDocument();
  });
});
