import Link from "next/link";

import { getAnalysis } from "@/lib/api";
import { formatDate, humanizeCategory } from "@/lib/format";
import { ChangedFilesTable } from "@/components/ChangedFilesTable";
import { ConcernList } from "@/components/ConcernList";
import { RiskScoreCard } from "@/components/RiskScoreCard";
import { SimilarPRs } from "@/components/SimilarPRs";
import { SuggestedTests } from "@/components/SuggestedTests";

export const dynamic = "force-dynamic";

export default async function AnalysisDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const a = await getAnalysis(id);

  return (
    <main className="container">
      <div className="crumb">
        <Link href="/dashboard">← Back to dashboard</Link>
      </div>

      <div className="page-header">
        <h1>
          #{a.number} {a.title}
        </h1>
      </div>
      <p className="muted small">
        {a.repository} · by {a.author} · analyzed {formatDate(a.created_at)} ·{" "}
        {a.status === "fallback" ? "heuristic fallback" : "AI review"} (
        {a.provider}/{a.model})
        {a.url ? (
          <>
            {" · "}
            <a href={a.url} target="_blank" rel="noreferrer">
              PR on GitHub
            </a>
          </>
        ) : null}
      </p>

      <div className="banner">AI review — advisory only; it does not block merges.</div>

      <RiskScoreCard
        score={a.final_score}
        band={a.risk_band}
        rationale={a.risk.rationale}
        deterministicScore={a.deterministic_score}
      />

      <h2>Summary</h2>
      <p>{a.review.summary}</p>
      {a.review.risk_categories.length > 0 ? (
        <p className="muted small">
          Categories: {a.review.risk_categories.map(humanizeCategory).join(", ")}
        </p>
      ) : null}

      <h2>Top concerns</h2>
      <ConcernList concerns={a.review.top_concerns} />

      <h2>Suggested tests</h2>
      <SuggestedTests tests={a.review.suggested_tests} />

      {a.review.regression_risks.length > 0 ? (
        <>
          <h2>Regression risks</h2>
          <ul className="test-list">
            {a.review.regression_risks.map((r, i) => (
              <li key={i} className="muted">
                {r}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      <h2>Changed files</h2>
      <ChangedFilesTable files={a.changed_files} />

      <h2>Similar historical PRs</h2>
      <SimilarPRs items={a.similar} />
    </main>
  );
}
