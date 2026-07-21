import type { RiskBand } from "@/lib/types";
import { bandColor, bandLabel } from "@/lib/format";

export function RiskScoreCard({
  score,
  band,
  rationale,
  deterministicScore,
}: {
  score: number;
  band: RiskBand;
  rationale: string;
  deterministicScore?: number;
}) {
  const color = bandColor(band);
  return (
    <div className="card score-card">
      <div className="score-figure">
        <div className="score-number" style={{ color }}>
          {score}
          <span className="score-max">/5</span>
        </div>
        <div className="score-band" style={{ color }}>
          {bandLabel(band)} risk
        </div>
      </div>
      <div className="score-body">
        <div className="meter" role="img" aria-label={`Risk ${score} of 5`}>
          {[1, 2, 3, 4, 5].map((i) => (
            <span
              key={i}
              className="meter-seg"
              style={{ background: i <= score ? color : "var(--border)" }}
            />
          ))}
        </div>
        <p className="muted rationale">{rationale}</p>
        {deterministicScore !== undefined && deterministicScore !== score ? (
          <p className="muted small">
            Heuristic base score {deterministicScore}/5; AI-adjusted to {score}/5
            (clamped to ±1).
          </p>
        ) : null}
      </div>
    </div>
  );
}
