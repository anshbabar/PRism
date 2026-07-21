import Link from "next/link";

import type { SimilarPR } from "@/lib/types";
import { percent } from "@/lib/format";
import { RiskBadge } from "./RiskBadge";

export function SimilarPRs({ items }: { items: SimilarPR[] }) {
  if (items.length === 0) {
    return (
      <p className="muted">
        No similar prior PRs in this repository yet — analyze related PRs to build
        history.
      </p>
    );
  }
  return (
    <ul className="similar-list">
      {items.map((s) => (
        <li key={s.analysis_id} className="card similar">
          <div className="similar-head">
            <Link href={`/analyses/${s.analysis_id}`}>
              #{s.number} {s.title}
            </Link>
            <span className="similarity">{percent(s.similarity)} similar</span>
          </div>
          <div className="similar-meta">
            <RiskBadge band={s.risk_band} score={s.risk_score} />
            <span className="muted small">{s.summary}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
