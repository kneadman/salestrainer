import type { JudgeSessionOutputDTO } from "../types";
import { isJudgeSessionOutputPayload } from "./reportPayload";

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

describe("isJudgeSessionOutputPayload", () => {
  it("returns true for a valid judge payload", () => {
    expect(isJudgeSessionOutputPayload(validPayload)).toBe(true);
  });

  it("returns false when recommendations are missing", () => {
    const payload = { ...validPayload } as Partial<JudgeSessionOutputDTO>;
    delete payload.recommendations;

    expect(isJudgeSessionOutputPayload(payload)).toBe(false);
  });

  it("returns false when overall_grade is unknown", () => {
    const payload = { ...validPayload, overall_grade: "legendary" };

    expect(isJudgeSessionOutputPayload(payload)).toBe(false);
  });

  it("returns false when a bento block has an unknown severity", () => {
    const payload = {
      ...validPayload,
      bento_blocks: [{ ...validPayload.bento_blocks[0], severity: "blue" }],
    };

    expect(isJudgeSessionOutputPayload(payload)).toBe(false);
  });

  it("returns false when a skill score has an unknown severity", () => {
    const payload = {
      ...validPayload,
      skill_scores: [{ ...validPayload.skill_scores[0], severity: "blue" }],
    };

    expect(isJudgeSessionOutputPayload(payload)).toBe(false);
  });
});
