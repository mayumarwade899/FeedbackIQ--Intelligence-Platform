import { useState } from "react";
import { useData } from "../hooks/useData";
import { api } from "../api/client";
import { COLORS, CATEGORY_COLORS } from "../utils/constants";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import SectionHeader from "../components/ui/SectionHeader";
import Sparkline from "../components/charts/Sparkline";
import Pagination from "../components/ui/Pagination";

export default function AnalyticsPage() {
  const [dupePage, setDupePage] = useState(1);
  const dupeLimit = 10;

  const { data: trends } = useData(() => api("/analytics/trends?days=14&group_by=category"), []);
  const { data: dupesData } = useData(() => api(`/analytics/duplicates?limit=${dupeLimit}&offset=${(dupePage - 1) * dupeLimit}`), [dupePage]);
  const { data: topIssues } = useData(() => api("/analytics/top-issues?limit=8"), []);

  const dupes = dupesData?.items || [];
  const dupeTotalPages = dupesData?.total ? Math.ceil(dupesData.total / dupeLimit) : 1;

  const categoryTrends = {};
  (trends || []).forEach(p => {
    const cat = p.category || "unknown";
    if (!categoryTrends[cat]) categoryTrends[cat] = [];
    categoryTrends[cat].push(p.count);
  });

  return (
    <div className="flex flex-col gap-5">
      <Card>
        <SectionHeader title="Category Trends (14 days)" />
        {Object.keys(categoryTrends).length > 0 ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4">
            {Object.entries(categoryTrends).map(([cat, points]) => (
              <div key={cat} className="p-3 bg-surfaceAlt rounded-lg">
                <div
                  className="text-xs font-semibold mb-2"
                  style={{ color: CATEGORY_COLORS[cat] || COLORS.accent }}
                >
                  {cat}
                </div>
                <Sparkline points={points} color={CATEGORY_COLORS[cat] || COLORS.accent} />
                <div className="text-[11px] text-muted mt-1">Total: {points.reduce((a, b) => a + b, 0)}</div>
              </div>
            ))}
          </div>
        ) : <div className="text-muted text-[13px]">No trend data yet — process some feedback to see trends</div>}
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <SectionHeader title="Top Issue Categories" />
          {topIssues?.length > 0 ? (
            <div className="flex flex-col gap-2">
              {topIssues.map((issue, i) => (
                <div key={i} className="flex justify-between px-3 py-2 bg-surfaceAlt rounded-md">
                  <span className="text-[13px]" style={{ color: CATEGORY_COLORS[issue.category] || COLORS.text }}>{issue.category}</span>
                  <span className="font-mono text-[13px] text-text font-semibold">{issue.count}</span>
                </div>
              ))}
            </div>
          ) : <div className="text-muted text-[13px]">No data yet</div>}
        </Card>

        <Card>
          <SectionHeader title="Duplicate Groups" />
          {dupes?.length > 0 ? (
            <div className="flex flex-col gap-2">
              {dupes.map(d => (
                <div key={d.id} className="p-3 px-3.5 bg-surfaceAlt rounded-lg text-xs border border-border">
                  <div className="flex justify-between items-center mb-2">
                    <Badge label={d.category} color={CATEGORY_COLORS[d.category] || COLORS.accent} small />
                    <span className="text-warning font-mono font-semibold">{Math.round((d.similarity_score || 0) * 100)}% similar</span>
                  </div>
                  <div className="flex gap-2 items-stretch">
                    <div className="flex-1 px-2.5 py-2 bg-bg rounded-md border-l-[3px] border-l-accent">
                      <div className="text-[10px] text-muted mb-1 uppercase tracking-wide">This item</div>
                      <div className="text-text leading-snug">{d.text || "—"}</div>
                    </div>
                    {d.original_text && (
                      <>
                        <div className="flex items-center text-muted text-base shrink-0">≈</div>
                        <div className="flex-1 px-2.5 py-2 bg-bg rounded-md border-l-[3px] border-l-warning">
                          <div className="text-[10px] text-muted mb-1 uppercase tracking-wide">Similar to</div>
                          <div className="text-textDim leading-snug">{d.original_text}</div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : <div className="text-muted text-[13px]">No duplicates detected</div>}
          <Pagination page={dupePage} totalPages={dupeTotalPages} setPage={setDupePage} />
        </Card>
      </div>
    </div>
  );
}
