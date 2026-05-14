import { COLORS } from "../../utils/constants";

const AGENTS = [
  { name: "Ingestion", icon: "⬇", color: "#58a6ff" },
  { name: "Classification", icon: "🏷", color: "#a371f7" },
  { name: "Sentiment", icon: "💬", color: "#3fb950" },
  { name: "Dedup", icon: "🔍", color: "#d29922" },
  { name: "Insights", icon: "💡", color: "#f0883e" },
  { name: "Ticket Gen", icon: "🎫", color: "#ec6547" },
];

export default function PipelineFlow() {
  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-1">
      {AGENTS.map((a, i) => (
        <div key={a.name} className="flex items-center">
          <div
            className="flex flex-col items-center px-3.5 py-2.5 rounded-lg min-w-[80px] gap-1"
            style={{
              background: a.color + "15",
              border: `1px solid ${a.color}44`,
            }}
          >
            <span className="text-lg">{a.icon}</span>
            <span
              className="text-[11px] font-semibold whitespace-nowrap"
              style={{ color: a.color }}
            >
              {a.name}
            </span>
          </div>
          {i < AGENTS.length - 1 && (
            <div className="text-muted text-base px-1">→</div>
          )}
        </div>
      ))}
    </div>
  );
}
