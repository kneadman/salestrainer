import type { ReportPayload } from "../types";
import { BentoReportGrid } from "./BentoReportGrid";
import { gradeLabel, isJudgeSessionOutputPayload } from "./reportPayload";

type StructuredReportSummaryProps = {
  payload: ReportPayload | null;
};

export function StructuredReportSummary({ payload }: StructuredReportSummaryProps) {
  /** Render either a full structured report surface or a small fallback for unknown payload shapes. */
  if (payload === null) {
    return null;
  }
  if (!isJudgeSessionOutputPayload(payload)) {
    return (
      <section className="structured-report-summary">
        <div className="structured-report-summary__header">
          <div>
            <h2>Структурированная оценка</h2>
            <p>Структурированная оценка сохранена, но формат не распознан.</p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="structured-report-summary">
      <div className="structured-report-summary__header">
        <div>
          <h2>Структурированная оценка</h2>
          <p>{payload.executive_summary}</p>
        </div>
        <div className="structured-report-summary__score">
          <strong>{payload.overall_score}/100</strong>
          <span>{gradeLabel(payload.overall_grade)}</span>
        </div>
      </div>
      <BentoReportGrid
        blocks={payload.bento_blocks}
        skillScores={payload.skill_scores}
        recommendations={payload.recommendations}
      />
    </section>
  );
}
