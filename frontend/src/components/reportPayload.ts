import type { JudgeSessionOutputDTO, JudgementGrade, JudgementSeverity } from "../types";

const JUDGEMENT_GRADES: readonly JudgementGrade[] = ["critical", "weak", "normal", "good", "strong"];
const JUDGEMENT_SEVERITIES: readonly JudgementSeverity[] = ["green", "yellow", "red", "neutral"];

export function isJudgeSessionOutputPayload(payload: unknown): payload is JudgeSessionOutputDTO {
  /** Perform a compact runtime shape check before rendering the structured report UI. */
  if (payload === null || typeof payload !== "object") {
    return false;
  }

  const candidate = payload as Record<string, unknown>;

  return (
    typeof candidate.overall_score === "number"
    && isJudgementGrade(candidate.overall_grade)
    && typeof candidate.executive_summary === "string"
    && Array.isArray(candidate.bento_blocks)
    && candidate.bento_blocks.every(isBentoBlockCandidate)
    && Array.isArray(candidate.skill_scores)
    && candidate.skill_scores.every(isSkillScoreCandidate)
    && Array.isArray(candidate.recommendations)
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

function isJudgementGrade(value: unknown): value is JudgementGrade {
  return typeof value === "string" && JUDGEMENT_GRADES.includes(value as JudgementGrade);
}

function isJudgementSeverity(value: unknown): value is JudgementSeverity {
  return typeof value === "string" && JUDGEMENT_SEVERITIES.includes(value as JudgementSeverity);
}

function isBentoBlockCandidate(value: unknown): value is { severity: JudgementSeverity } {
  if (value === null || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return isJudgementSeverity(candidate.severity);
}

function isSkillScoreCandidate(value: unknown): value is { severity: JudgementSeverity } {
  if (value === null || typeof value !== "object") {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return isJudgementSeverity(candidate.severity);
}
