import type { ReportPayload } from "../types";

type TrainingReportModalProps = {
  open: boolean;
  report: string | null;
  reportPayload: ReportPayload | null;
  onClose: () => void;
};

export function TrainingReportModal({ open, report, reportPayload, onClose }: TrainingReportModalProps) {
  /** Render the finished training report in a modal without pushing the trainer layout around. */
  if (!open) {
    return null;
  }

  const fallbackPayload = reportPayload ? JSON.stringify(reportPayload, null, 2) : null;

  return (
    <div className="training-report-modal" role="presentation" onClick={onClose}>
      <section
        className="training-report-modal__dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Итоговый отчёт"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="training-report-modal__header">
          <div>
            <span className="client-kicker">Отчёт</span>
            <h2>Итоговый отчёт</h2>
          </div>
          <button
            type="button"
            className="secondary-button training-report-modal__close"
            onClick={onClose}
            aria-label="Закрыть итоговый отчёт"
          >
            Закрыть
          </button>
        </header>
        <div className="training-report-modal__body">
          {report ? <pre className="training-report-modal__text">{report}</pre> : null}
          {!report && fallbackPayload ? <pre className="training-report-modal__text">{fallbackPayload}</pre> : null}
          {!report && !fallbackPayload ? <p className="training-report-modal__empty">Отчёт пока недоступен.</p> : null}
        </div>
      </section>
    </div>
  );
}
