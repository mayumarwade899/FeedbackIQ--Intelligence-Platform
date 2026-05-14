import { COLORS } from "../../utils/constants";
import { fmtDate } from "../../utils/date";
import { useData } from "../../hooks/useData";
import { api } from "../../api/client";
import MetricCard from "../ui/MetricCard";
import Card from "../ui/Card";
import SectionHeader from "../ui/SectionHeader";
import RecentAgentRunsTable from "./RecentAgentRunsTable";

export default function MonitoringPanel() {
  const { data: metrics } = useData(() => api("/monitoring/metrics"), [], 15000);

  if (!metrics) return <div className="text-muted text-center p-10 text-[13px]">Loading metrics…</div>;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Total Runs (7d)" value={metrics?.total_runs_24h ?? 0} />
        <MetricCard label="Total Tokens (7d)" value={metrics?.total_tokens_24h?.toLocaleString() ?? 0} />
        <MetricCard label="Estimated Cost" value={`$${metrics?.total_cost_24h_usd ?? 0}`} accent={COLORS.success} />
        <MetricCard
          label="Last Ingestion"
          value={metrics?.last_ingestion ? fmtDate(metrics.last_ingestion, { hour: "2-digit", minute: "2-digit", second: undefined }) : "Never"}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <SectionHeader title="Agent Success Rate" />
          {metrics?.agent_success_rate && Object.keys(metrics.agent_success_rate).length > 0 ? (
            <div className="flex flex-col gap-2">
              {Object.entries(metrics.agent_success_rate).map(([name, rate]) => (
                <div key={name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-textDim">{name.replace(/_/g, " ")}</span>
                    <span
                      className="font-mono"
                      style={{ color: rate > 0.9 ? COLORS.success : rate > 0.7 ? COLORS.warning : COLORS.danger }}
                    >
                      {Math.round(rate * 100)}%
                    </span>
                  </div>
                  <div className="bg-border rounded-[3px] h-1">
                    <div
                      className="h-full rounded-[3px]"
                      style={{
                        width: `${rate * 100}%`,
                        background: rate > 0.9 ? COLORS.success : rate > 0.7 ? COLORS.warning : COLORS.danger,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : <div className="text-muted text-[13px]">No agent data yet</div>}
        </Card>

        <Card>
          <SectionHeader title="Avg Latency (ms)" />
          {metrics?.agent_avg_latency && Object.keys(metrics.agent_avg_latency).length > 0 ? (
            <div className="flex flex-col gap-2">
              {Object.entries(metrics.agent_avg_latency).map(([name, lat]) => (
                <div key={name} className="flex justify-between text-[13px]">
                  <span className="text-textDim">{name.replace(/_/g, " ")}</span>
                  <span
                    className="font-mono"
                    style={{ color: lat < 500 ? COLORS.success : lat < 2000 ? COLORS.warning : COLORS.danger }}
                  >
                    {Math.round(lat)}ms
                  </span>
                </div>
              ))}
            </div>
          ) : <div className="text-muted text-[13px]">No latency data yet</div>}
        </Card>
      </div>

      <Card>
        <SectionHeader title="Recent Agent Runs" />
        <RecentAgentRunsTable />
      </Card>
    </div>
  );
}
