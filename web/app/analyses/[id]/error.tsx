"use client";

import Link from "next/link";

export default function Error({ error }: { error: Error & { digest?: string } }) {
  return (
    <main className="container">
      <div className="crumb">
        <Link href="/dashboard">← Back to dashboard</Link>
      </div>
      <div className="card error-card">
        <strong>Couldn&apos;t load this analysis.</strong>
        <p className="muted">It may not exist, or the backend may be unavailable.</p>
        <p className="muted small">{error.message}</p>
      </div>
    </main>
  );
}
