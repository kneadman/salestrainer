import { useEffect } from "react";
import { StructuredReportSummary } from "./StructuredReportSummary";
import { isJudgeSessionOutputPayload } from "./reportPayload";
import type { ReportPayload } from "../types";

type TrainingReportModalProps = {
  open: boolean;
  onClose: () => void;
  report: string | null;
  payload: ReportPayload | null;
};

export function TrainingReportModal({ open, onClose, report, payload }: TrainingReportModalProps) {
  /** Keep modal close affordances and page scroll locking local to the overlay lifecycle. */
  const hasStructuredPayload = payload !== null && isJudgeSessionOutputPayload(payload);

  useEffect(() => {
    if (!open) {
      return;
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

  return (
    <div className="training-report-modal__backdrop" onClick={onClose} role="presentation">
      <section
        className="training-report-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="training-report-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="training-report-modal__header">
          <div>
            <h2 id="training-report-modal-title">Итоговый отчёт</h2>
            <p>Структурированная оценка тренировки</p>
          </div>
          <button
            type="button"
            className="training-report-modal__close"
            onClick={onClose}
            aria-label="Закрыть отчёт"
          >
            ×
          </button>
        </header>
        <div className="training-report-modal__body">
          {payload ? <StructuredReportSummary payload={payload} /> : null}
          {!payload && report ? (
            <section className="training-report-modal__fallback">
              <h3>Текстовый отчёт</h3>
              <pre className="report-block">{report}</pre>
            </section>
          ) : null}
          {payload && !hasStructuredPayload && report ? (
            <section className="training-report-modal__fallback training-report-modal__fallback--secondary">
              <h3>Текстовая версия</h3>
              <pre className="report-block">{report}</pre>
            </section>
          ) : null}
        </div>
      </section>
    </div>
  );
}
