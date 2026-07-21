import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container">
      <h1>PRism</h1>
      <p className="muted">
        AI PR Reviewer + Regression Triage. PRism parses a pull request&apos;s diff,
        scores its risk with deterministic heuristics, generates a schema-validated
        AI review, and surfaces similar historical changes.
      </p>

      <div className="card">
        <strong>Dashboard</strong>
        <p className="muted">
          Browse analyzed pull requests, open a detailed risk report, and review
          the evaluation metrics.
        </p>
        <p>
          <Link href="/dashboard">View analyzed PRs →</Link>
          {"  ·  "}
          <Link href="/eval">Evaluation metrics →</Link>
        </p>
      </div>
    </main>
  );
}
