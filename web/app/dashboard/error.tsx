"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="container">
      <h1>Analyzed PRs</h1>
      <div className="card error-card">
        <strong>Couldn&apos;t load analyses.</strong>
        <p className="muted">
          Is the backend running at the configured API URL? Start it with{" "}
          <code>make dev</code> (and <code>make db-up</code> for the database).
        </p>
        <p className="muted small">{error.message}</p>
        <button onClick={reset}>Retry</button>
      </div>
    </main>
  );
}
