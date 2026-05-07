import type { BentoReportBlockDTO, ReportRecommendationDTO, SkillScoreDTO } from "../types";
import { severityClassName, severityLabel } from "./reportPayload";

type BentoReportGridProps = {
  blocks: BentoReportBlockDTO[];
  skillScores: SkillScoreDTO[];
  recommendations: ReportRecommendationDTO[];
};

type BentoReportTileProps = {
  block: BentoReportBlockDTO;
};

function formatEvidence(indexes: number[]): string | null {
  /** Present evidence indexes in a compact human-readable form. */
  if (indexes.length === 0) {
    return null;
  }
  return `Ходы: ${indexes.map((index) => `#${index}`).join(", ")}`;
}

export function BentoReportTile({ block }: BentoReportTileProps) {
  /** Render one structured bento tile with severity coloring and optional score. */
  const evidence = formatEvidence(block.evidence_turn_indexes);
  return (
    <article className={`bento-report-tile ${severityClassName(block.severity)}`}>
      <div className="bento-report-tile__header">
        <div>
          <span className="bento-report-tile__severity">{severityLabel(block.severity)}</span>
          <h3>{block.title}</h3>
        </div>
        {typeof block.score === "number" ? <strong className="bento-report-tile__score">{block.score}/100</strong> : null}
      </div>
      <p className="bento-report-tile__summary">{block.short_text}</p>
      <p>{block.detail}</p>
      {evidence ? <p className="bento-report-tile__evidence">{evidence}</p> : null}
    </article>
  );
}

export function SkillScoreList({ skillScores }: { skillScores: SkillScoreDTO[] }) {
  /** Render skill rows with score, severity label, and compact evidence. */
  return (
    <section className="skill-score-list">
      <h3>Навыки</h3>
      {skillScores.map((skill) => (
        <div key={skill.id} className="skill-score-row">
          <div>
            <strong>{skill.title}</strong>
            <p>{skill.explanation}</p>
            {skill.evidence_turn_indexes.length > 0 ? (
              <span>{formatEvidence(skill.evidence_turn_indexes)}</span>
            ) : null}
          </div>
          <div className="skill-score-row__meta">
            <strong>{skill.score}/100</strong>
            <span>{severityLabel(skill.severity)}</span>
          </div>
        </div>
      ))}
    </section>
  );
}

export function RecommendationList({ recommendations }: { recommendations: ReportRecommendationDTO[] }) {
  /** Render a compact list of structured recommendations from the saved payload. */
  if (recommendations.length === 0) {
    return null;
  }
  return (
    <section className="recommendation-list">
      <h3>Рекомендации</h3>
      {recommendations.map((recommendation, index) => (
        <article key={`${recommendation.title}-${index}`} className="recommendation-card">
          <div className="recommendation-card__header">
            <strong>{recommendation.title}</strong>
            <span>{recommendation.priority}</span>
          </div>
          <p>{recommendation.description}</p>
          {recommendation.example_phrase ? <blockquote>{recommendation.example_phrase}</blockquote> : null}
        </article>
      ))}
    </section>
  );
}

export function BentoReportGrid({ blocks, skillScores, recommendations }: BentoReportGridProps) {
  /** Compose tiles, skill rows, and recommendations into one compact report surface. */
  return (
    <div className="structured-report-summary__body">
      <div className="bento-report-grid">
        {blocks.map((block) => (
          <BentoReportTile key={block.id} block={block} />
        ))}
      </div>
      <SkillScoreList skillScores={skillScores} />
      <RecommendationList recommendations={recommendations} />
    </div>
  );
}
