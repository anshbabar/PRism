import { listAnalyses } from "@/lib/api";
import type { AnalysisSummary } from "@/lib/types";

export default async function DashboardPage() {
  // Placeholder: returns [] until the backend list endpoint exists.
  const analyses: AnalysisSummary[] = await listAnalyses();

  return (
    <main className="container">
      <span className="badge">placeholder</span>
      <h1>Dashboard</h1>
      <p className="muted">
        Analyzed pull requests will appear here — risk score, top concern, and a
        link to the full analysis.
      </p>

      {analyses.length === 0 ? (
        <div className="card muted">
          No analyses yet. Once the ingestion + analysis pipeline lands, PRs you
          analyze will be listed here.
        </div>
      ) : (
        <ul>
          {analyses.map((a) => (
            <li key={a.id}>
              {a.repo} #{a.number} — {a.title} (risk {a.riskScore})
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
