import type { ReportPayload } from "../types";
import { StructuredReportSummary } from "./StructuredReportSummary";
import { isJudgeSessionOutputPayload } from "./reportPayload";

type ReportSurfaceProps = {
  report: string | null;
  reportPayload: ReportPayload | null;
  fallbackClassName?: string;
  fallbackTextClassName?: string;
};

export function ReportSurface({ report, reportPayload, fallbackClassName, fallbackTextClassName }: ReportSurfaceProps) {
  /** Show one report representation: structured payload first, plain text only as a fallback. */
  const hasStructuredPayload = isJudgeSessionOutputPayload(reportPayload);

  if (hasStructuredPayload) {
    return <StructuredReportSummary payload={reportPayload} />;
  }

  if (report) {
    return (
      <section className={fallbackClassName ?? "training-report-modal__fallback"}>
        <h3>Текстовая версия отчёта</h3>
        <pre className={fallbackTextClassName ?? "report-block"}>{report}</pre>
      </section>
    );
  }

  return (
    <section className={fallbackClassName ?? "training-report-modal__fallback"}>
      <h3>Отчёт недоступен</h3>
      <p className="training-report-modal__empty">Итоговый отчёт пока не был сформирован.</p>
    </section>
  );
}
