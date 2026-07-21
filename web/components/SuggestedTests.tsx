import type { SuggestedTest } from "@/lib/types";

export function SuggestedTests({ tests }: { tests: SuggestedTest[] }) {
  if (tests.length === 0) {
    return <p className="muted">No test suggestions.</p>;
  }
  return (
    <ul className="test-list">
      {tests.map((t, i) => (
        <li key={i}>
          <strong>{t.area}</strong>
          <span className="muted"> — {t.reason}</span>
        </li>
      ))}
    </ul>
  );
}
