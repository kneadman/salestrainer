type StructuredReportSummaryProps = {
  payload: Record<string, unknown> | null;
};

function readNumber(payload: Record<string, unknown>, key: string): number | null {
  /** Read one optional numeric field from the generic payload object. */
  const value = payload[key];
  return typeof value === "number" ? value : null;
}

function readString(payload: Record<string, unknown>, key: string): string | null {
  /** Read one optional string field from the generic payload object. */
  const value = payload[key];
  return typeof value === "string" && value.trim() ? value : null;
}

function readArrayLength(payload: Record<string, unknown>, key: string): number | null {
  /** Read one optional array length from the generic payload object. */
  const value = payload[key];
  return Array.isArray(value) ? value.length : null;
}

export function StructuredReportSummary({ payload }: StructuredReportSummaryProps) {
  /** Show a compact structured judge summary without replacing the main text report. */
  if (payload === null) {
    return null;
  }

  const overallScore = readNumber(payload, "overall_score");
  const overallGrade = readString(payload, "overall_grade");
  const executiveSummary = readString(payload, "executive_summary");
  const bentoBlockCount = readArrayLength(payload, "bento_blocks");

  return (
    <section className="structured-report-summary">
      <div className="panel-card__header">
        <h2>Структурированная оценка</h2>
      </div>
      <div className="structured-report-summary__grid">
        {overallScore !== null ? (
          <div className="structured-report-summary__metric">
            <span>Общая оценка</span>
            <strong>{overallScore}/100</strong>
          </div>
        ) : null}
        {overallGrade !== null ? (
          <div className="structured-report-summary__metric">
            <span>Уровень</span>
            <strong>{overallGrade}</strong>
          </div>
        ) : null}
        {bentoBlockCount !== null ? (
          <div className="structured-report-summary__metric">
            <span>Блоков</span>
            <strong>{bentoBlockCount}</strong>
          </div>
        ) : null}
      </div>
      {executiveSummary ? <p>{executiveSummary}</p> : null}
    </section>
  );
}
