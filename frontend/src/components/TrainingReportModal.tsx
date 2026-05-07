import { useEffect } from "react";
import type { ReportPayload } from "../types";
import { StructuredReportSummary } from "./StructuredReportSummary";
import { isJudgeSessionOutputPayload } from "./reportPayload";

type TrainingReportModalProps = {
  open: boolean;
  report: string | null;
  reportPayload: ReportPayload | null;
  onClose: () => void;
};

export function TrainingReportModal({ open, report, reportPayload, onClose }: TrainingReportModalProps) {
  /** Render the finished training report in a modal and preserve structured output when it exists. */
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.body.classList.add("training-report-modal-open");
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.classList.remove("training-report-modal-open");
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  const hasStructuredPayload = reportPayload !== null && isJudgeSessionOutputPayload(reportPayload);
  const shouldShowFallbackText = Boolean(report) && (!reportPayload || !hasStructuredPayload);

  return (
    <div className="training-report-modal__backdrop" role="presentation" onClick={onClose}>
      <section
        className="training-report-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Итоговый отчёт"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="training-report-modal__header">
          <div>
            <span className="client-kicker">Отчёт</span>
            <h2>Итоговый отчёт</h2>
            <p>Финальная оценка тренировки и ключевые выводы по диалогу.</p>
          </div>
          <button
            type="button"
            className="secondary-button training-report-modal__close"
            onClick={onClose}
            aria-label="Закрыть отчёт"
            title="Закрыть отчёт"
          >
            ×
          </button>
        </header>
        <div className="training-report-modal__body">
          {reportPayload ? <StructuredReportSummary payload={reportPayload} /> : null}
          {shouldShowFallbackText ? (
            <section className={`training-report-modal__fallback${reportPayload ? " training-report-modal__fallback--secondary" : ""}`}>
              <h3>Текстовая версия</h3>
              <pre className="report-block">{report}</pre>
            </section>
          ) : null}
          {!reportPayload && !report ? (
            <section className="training-report-modal__fallback">
              <h3>Отчёт недоступен</h3>
              <p className="training-report-modal__empty">Итоговый отчёт пока не был сформирован.</p>
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
