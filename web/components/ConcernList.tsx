import type { TopConcern } from "@/lib/types";

export function ConcernList({ concerns }: { concerns: TopConcern[] }) {
  if (concerns.length === 0) {
    return <p className="muted">No specific concerns flagged.</p>;
  }
  return (
    <ul className="concern-list">
      {concerns.map((c, i) => (
        <li key={i} className="card concern">
          <strong>{c.title}</strong>
          <p className="muted">{c.detail}</p>
        </li>
      ))}
    </ul>
  );
}
