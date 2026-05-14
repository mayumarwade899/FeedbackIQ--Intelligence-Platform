import { useData } from "../hooks/useData";
import { api } from "../api/client";
import { COLORS, CATEGORY_COLORS, PRIORITY_COLORS, SENTIMENT_COLORS } from "../utils/constants";
import MetricCard from "../components/ui/MetricCard";
import Card from "../components/ui/Card";
import SectionHeader from "../components/ui/SectionHeader";
import DistributionBar from "../components/charts/DistributionBar";
import PipelineFlow from "../components/pipeline/PipelineFlow";
import IngestionSourcesPanel from "../components/ingestion/IngestionSourcesPanel";

export default function OverviewPage() {
  const { data: overview, reload } = useData(() => api("/analytics/overview"), [], 30000);
  const { data: topIssues } = useData(() => api("/analytics/top-issues"), []);

  if (!overview && !topIssues) return <div className="text-muted text-center p-[60px] text-[13px]">Loading…</div>;

  const ov = overview || {};

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Total Feedback" value={ov.total_feedback ?? 0} />
        <MetricCard label="Processed Today" value={ov.processed_today ?? 0} accent={COLORS.accent} />
        <MetricCard label="Pending Review" value={ov.pending_review ?? 0} accent={ov.pending_review > 10 ? COLORS.warning : COLORS.text} />
        <MetricCard label="Open Tickets" value={ov.open_tickets ?? 0} accent={COLORS.success} />
      </div>

      <div className="grid grid-cols-5 gap-3">
        <MetricCard label="Avg Confidence" value={`${Math.round((ov.avg_confidence ?? 0) * 100)}%`} />
        <MetricCard label="Success Rate" value={`${Math.round((ov.processing_success_rate ?? 0) * 100)}%`} accent={COLORS.success} />
        <MetricCard label="Avg Latency" value={`${Math.round(ov.avg_agent_latency_ms ?? 0)}ms`} />
        <MetricCard label="Total Tokens" value={ov.total_tokens?.toLocaleString() ?? 0} />
        <MetricCard label="Total Cost" value={`$${ov.total_cost_usd?.toFixed(4) ?? 0}`} accent={COLORS.success} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <SectionHeader title="By Category" />
          <DistributionBar data={ov.category_distribution} colorMap={CATEGORY_COLORS} />
        </Card>
        <Card>
          <SectionHeader title="By Priority" />
          <DistributionBar data={ov.priority_distribution} colorMap={PRIORITY_COLORS} />
        </Card>
        <Card>
          <SectionHeader title="By Sentiment" />
          <DistributionBar data={ov.sentiment_distribution} colorMap={SENTIMENT_COLORS} />
        </Card>
      </div>

      <Card>
        <SectionHeader title="Agent Pipeline" />
        <PipelineFlow />
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <SectionHeader title="By Source" />
          <DistributionBar data={ov.source_distribution} />
        </Card>
        <IngestionSourcesPanel onTrigger={reload} />
      </div>
    </div>
  );
}
