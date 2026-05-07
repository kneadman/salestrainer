import type { JudgeSessionOutputDTO, JudgementGrade, JudgementSeverity } from "../types";

export function isJudgeSessionOutputPayload(payload: unknown): payload is JudgeSessionOutputDTO {
  /** Perform a small runtime shape check before rendering the structured report UI. */
  if (payload === null || typeof payload !== "object") {
    return false;
  }
  const candidate = payload as Record<string, unknown>;
  return (
    typeof candidate.overall_score === "number"
    && typeof candidate.overall_grade === "string"
    && typeof candidate.executive_summary === "string"
    && Array.isArray(candidate.bento_blocks)
    && Array.isArray(candidate.skill_scores)
  );
}

export function severityLabel(severity: JudgementSeverity): string {
  /** Map the backend severity enum to a Russian label for compact UI use. */
  const labels: Record<JudgementSeverity, string> = {
    green: "Сильная зона",
    yellow: "Средняя зона",
    red: "Риск",
    neutral: "Инфо",
  };
  return labels[severity];
}

export function gradeLabel(grade: JudgementGrade): string {
  /** Map the backend grade enum to a Russian label for the report header. */
  const labels: Record<JudgementGrade, string> = {
    critical: "Критично",
    weak: "Слабо",
    normal: "Нормально",
    good: "Хорошо",
    strong: "Сильно",
  };
  return labels[grade];
}

export function severityClassName(severity: JudgementSeverity): string {
  /** Build a stable CSS modifier name from the backend severity enum. */
  return `bento-report-tile--${severity}`;
}
