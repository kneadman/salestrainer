import type { ClientStatePublic, SessionPublicDTO } from "../types";
import { FactsPanel } from "./FactsPanel";
import { MetricsPanel } from "./MetricsPanel";

type TrainerContextPanelProps = {
  session: SessionPublicDTO;
  factsState: ClientStatePublic;
};

export function TrainerContextPanel({ session, factsState }: TrainerContextPanelProps) {
  /** Render metrics and facts with a desktop sidebar and a mobile collapsible accordion. */
  return (
    <div className="trainer-context">
      <div className="trainer-context__desktop">
        <MetricsPanel session={session} />
        <FactsPanel state={factsState} />
      </div>
      <details className="trainer-context__mobile">
        <summary>
          <span>Контекст тренировки</span>
          <strong>
            {session.turn_count} ходов · интерес {session.interest.score}
          </strong>
        </summary>
        <div className="trainer-context__mobile-body">
          <MetricsPanel session={session} />
          <FactsPanel state={factsState} />
        </div>
      </details>
    </div>
  );
}
