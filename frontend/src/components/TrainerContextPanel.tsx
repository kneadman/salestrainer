import type { FactsPanelDTO, SessionPublicDTO } from "../types";
import { FactsPanel } from "./FactsPanel";
import { MetricsPanel } from "./MetricsPanel";

type TrainerContextPanelProps = {
  session: SessionPublicDTO;
  factsPanel: FactsPanelDTO;
  mode?: "desktop" | "mobile" | "both";
  trainingConfigName?: string;
};

export function TrainerContextPanel({ session, factsPanel, mode = "both", trainingConfigName }: TrainerContextPanelProps) {
  /** Render metrics and facts with a desktop sidebar and/or a mobile collapsible accordion. */
  const desktop = (
    <div className="trainer-context__desktop">
      <MetricsPanel session={session} trainingConfigName={trainingConfigName} />
      <FactsPanel factsPanel={factsPanel} />
    </div>
  );

  const mobile = (
    <details className="trainer-context__mobile">
      <summary>
        <span>Контекст тренировки</span>
        <strong>
          {session.turn_count} ходов · интерес {session.interest.score}
        </strong>
      </summary>
      <div className="trainer-context__mobile-body">
        <MetricsPanel session={session} trainingConfigName={trainingConfigName} />
        <FactsPanel factsPanel={factsPanel} />
      </div>
    </details>
  );

  return (
    <div className="trainer-context">
      {mode === "desktop" || mode === "both" ? desktop : null}
      {mode === "mobile" || mode === "both" ? mobile : null}
    </div>
  );
}
