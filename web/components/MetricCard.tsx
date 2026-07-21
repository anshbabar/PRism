export function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card metric-card">
      <div className="metric-value">{value}</div>
      <div className="muted small">{label}</div>
    </div>
  );
}
