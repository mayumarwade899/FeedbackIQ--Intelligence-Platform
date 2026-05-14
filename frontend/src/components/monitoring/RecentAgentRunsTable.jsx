import Badge from "../ui/Badge";
import { COLORS } from "../../utils/constants";
import { fmtDate } from "../../utils/date";
import { useData } from "../../hooks/useData";
import { api } from "../../api/client";

export default function RecentAgentRunsTable() {
  const { data: runs } = useData(() => api("/monitoring/agent-runs?limit=20"), [], 15000);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr className="border-b border-border">
            {["Agent", "Status", "Latency", "Tokens", "Cost", "Started At"].map(h => (
              <th key={h} className="px-3 py-2 text-left text-muted font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(runs || []).map(run => (
            <tr key={run.id} className="border-b border-border">
              <td className="px-3 py-2 text-textDim">{run.agent_name.replace(/_/g, " ")}</td>
              <td className="px-3 py-2">
                <Badge
                  label={run.status}
                  color={run.status === "success" ? COLORS.success : run.status === "failed" ? COLORS.danger : COLORS.muted}
                  small
                />
              </td>
              <td className="px-3 py-2 font-mono text-muted">{run.latency_ms ? `${Math.round(run.latency_ms)}ms` : "—"}</td>
              <td className="px-3 py-2 font-mono text-muted">{run.tokens_used?.toLocaleString() ?? "—"}</td>
              <td className="px-3 py-2 font-mono text-success">${run.estimated_cost?.toFixed(5) ?? "0.00"}</td>
              <td className="px-3 py-2 text-muted">{fmtDate(run.started_at)}</td>
            </tr>
          ))}
          {!runs?.length && (
            <tr><td colSpan={6} className="p-5 text-center text-muted">No agent runs recorded yet</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
