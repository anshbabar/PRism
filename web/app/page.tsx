import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <span className="badge">Milestone 1 · skeleton</span>
      <h1>PRism</h1>
      <p className="muted">
        AI PR Reviewer + Regression Triage. PRism analyzes GitHub pull requests,
        scores their risk, suggests regression tests, and surfaces similar
        historical changes.
      </p>

      <div className="card">
        <strong>Status:</strong> project skeleton. The analysis pipeline, API,
        and dashboard data are wired in later milestones (see{" "}
        <code>docs/technical-design.md</code>).
      </div>

      <p>
        <Link href="/dashboard">Go to the dashboard →</Link>
      </p>
    </main>
  );
}
