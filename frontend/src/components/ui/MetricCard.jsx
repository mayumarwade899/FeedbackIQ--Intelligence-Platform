import Card from "./Card";

export default function MetricCard({ label, value, sub, accent }) {
  return (
    <Card>
      <div className="text-xs text-muted font-medium tracking-wide uppercase mb-2">
        {label}
      </div>
      <div
        className="text-[32px] font-bold leading-none font-mono"
        style={{ color: accent || "#e6edf3" }}
      >
        {value ?? "—"}
      </div>
      {sub && <div className="text-xs text-muted mt-1.5">{sub}</div>}
    </Card>
  );
}
