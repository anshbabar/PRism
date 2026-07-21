import type { RiskBand } from "@/lib/types";
import { bandColor, bandLabel } from "@/lib/format";

export function RiskBadge({ band, score }: { band: RiskBand; score?: number }) {
  const color = bandColor(band);
  return (
    <span className="risk-badge" style={{ borderColor: color, color }}>
      <span className="risk-dot" style={{ background: color }} aria-hidden />
      {bandLabel(band)}
      {score !== undefined ? ` · ${score}/5` : ""}
    </span>
  );
}
