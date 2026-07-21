import Link from "next/link";

import { listAnalyses } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { RiskBadge } from "@/components/RiskBadge";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const analyses = await listAnalyses();

  return (
    <main className="container">
      <div className="page-header">
        <h1>Analyzed PRs</h1>
        <span className="muted small">{analyses.length} analyses</span>
      </div>

      {analyses.length === 0 ? (
        <div className="card muted">
          No analyses yet. Start the API, then run <code>make seed</code> (or POST
          a fixture to <code>/api/analyze/local-fixture</code>) to populate the
          dashboard.
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>PR</th>
              <th>Risk</th>
              <th>Top concern</th>
              <th className="num">Files</th>
              <th>Analyzed</th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((a) => (
              <tr key={a.analysis_id}>
                <td>
                  <Link href={`/analyses/${a.analysis_id}`}>
                    #{a.number} {a.title}
                  </Link>
                  <div className="muted small">{a.repository}</div>
                </td>
                <td>
                  <RiskBadge band={a.risk_band} score={a.final_score} />
                </td>
                <td className="muted">{a.top_concern ?? "—"}</td>
                <td className="num">{a.files_changed}</td>
                <td className="muted small">{formatDate(a.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
