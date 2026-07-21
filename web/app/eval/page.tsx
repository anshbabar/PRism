import { getEvalLatest } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { MetricCard } from "@/components/MetricCard";

export const dynamic = "force-dynamic";

export default async function EvalPage() {
  const evalResult = await getEvalLatest();
  const m = evalResult.metrics;

  const cards: { label: string; value: string }[] = [
    { label: "valid JSON rate", value: m.valid_json_rate.toFixed(2) },
    { label: "score accuracy (±1)", value: m.risk_score_accuracy_within_1.toFixed(2) },
    { label: "category precision", value: m.risk_category_precision.toFixed(2) },
    { label: "category recall", value: m.risk_category_recall.toFixed(2) },
    { label: "test overlap", value: m.suggested_test_overlap.toFixed(2) },
    { label: "avg latency", value: `${m.average_latency_ms.toFixed(1)} ms` },
  ];

  return (
    <main className="container">
      <div className="page-header">
        <h1>Evaluation metrics</h1>
        <span className="muted small">
          {evalResult.provider}/{evalResult.model} · {evalResult.fixture_count}{" "}
          fixtures
        </span>
      </div>
      <p className="muted small">Generated {formatDate(evalResult.generated_at)}</p>

      <div className="metric-grid">
        {cards.map((c) => (
          <MetricCard key={c.label} label={c.label} value={c.value} />
        ))}
      </div>

      <h2>Per fixture</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Fixture</th>
            <th className="num">Score</th>
            <th className="num">Expected</th>
            <th>±1</th>
            <th className="num">Overlap</th>
            <th className="num">ms</th>
          </tr>
        </thead>
        <tbody>
          {evalResult.fixtures.map((f) => (
            <tr key={f.name}>
              <td className="mono">{f.name}</td>
              <td className="num">{f.predicted_score}</td>
              <td className="num">{f.expected_score}</td>
              <td>{f.score_within_1 ? "✓" : "✗"}</td>
              <td className="num">
                {f.test_overlap === null ? "—" : f.test_overlap.toFixed(2)}
              </td>
              <td className="num">{f.latency_ms.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
