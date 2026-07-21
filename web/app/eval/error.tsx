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
      <h1>Evaluation metrics</h1>
      <div className="card error-card">
        <strong>Couldn&apos;t load evaluation results.</strong>
        <p className="muted">
          Run <code>make eval</code> to generate <code>eval/results/latest.json</code>,
          and make sure the backend is running.
        </p>
        <p className="muted small">{error.message}</p>
        <button onClick={reset}>Retry</button>
      </div>
    </main>
  );
}
