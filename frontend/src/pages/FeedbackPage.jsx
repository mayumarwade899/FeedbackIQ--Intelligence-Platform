import { useState } from "react";
import { useData } from "../hooks/useData";
import { api } from "../api/client";
import Card from "../components/ui/Card";
import Btn from "../components/ui/Btn";
import Spinner from "../components/ui/Spinner";
import FilterSelect from "../components/ui/FilterSelect";
import Pagination from "../components/ui/Pagination";
import FeedbackRow from "../components/feedback/FeedbackRow";
import PendingFeedbackRow from "../components/feedback/PendingFeedbackRow";
import FeedbackDrawer from "../components/feedback/FeedbackDrawer";
import SubmitModal from "../components/feedback/SubmitModal";

const LIMIT = 25;

export default function FeedbackPage() {
  const [filters, setFilters] = useState({ category: "", priority: "", sentiment: "", review_status: "" });
  const [selected, setSelected] = useState(null);
  const [showSubmit, setShowSubmit] = useState(false);
  const [page, setPage] = useState(1);

  const buildQuery = () => {
    const params = new URLSearchParams({ limit: LIMIT, offset: (page - 1) * LIMIT });
    Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
    return `/feedback/processed?${params}`;
  };

  const { data, loading, reload } = useData(() => api(buildQuery()), [JSON.stringify(filters), page], 5000);
  const feedback = data?.items || [];
  const totalPages = data?.total ? Math.ceil(data.total / LIMIT) : 1;
  const { data: pendingFeedback, reload: reloadPending } = useData(() => api("/feedback/raw?processed=false&limit=10"), [], 5000);

  const handleRefresh = () => { reload(); reloadPending?.(); };
  const handleFilterChange = (field, value) => setFilters(f => ({ ...f, [field]: value }));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-2.5 flex-wrap">
          <FilterSelect field="category" value={filters.category} options={["Bug", "Feature Request", "Complaint", "Praise", "Spam"]} onChange={handleFilterChange} />
          <FilterSelect field="priority" value={filters.priority} options={["Critical", "High", "Medium", "Low"]} onChange={handleFilterChange} />
          <FilterSelect field="sentiment" value={filters.sentiment} options={["positive", "negative", "neutral", "mixed"]} onChange={handleFilterChange} />
          <FilterSelect field="review_status" value={filters.review_status} options={["pending", "approved", "rejected"]} onChange={handleFilterChange} />
        </div>
        <div className="flex gap-2">
          <Btn variant="secondary" small onClick={handleRefresh}>↻ Refresh</Btn>
          <Btn small onClick={() => setShowSubmit(true)}>+ Submit</Btn>
        </div>
      </div>

      <Card style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div className="flex justify-center p-10"><Spinner size={32} /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-surfaceAlt border-b border-border">
                  {["Feedback", "Category", "Priority", "Sentiment", "Review", "Confidence"].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-muted text-xs font-medium whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(pendingFeedback || []).map(item => (
                  <PendingFeedbackRow key={item.id} item={item} />
                ))}
                {(feedback || []).map(item => (
                  <FeedbackRow key={item.id} item={item} onSelect={setSelected} />
                ))}
                {!(feedback?.length) && !(pendingFeedback?.length) && (
                  <tr><td colSpan={6} className="p-10 text-center text-muted">
                    No feedback found. Submit some or trigger ingestion from the Overview page.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <Pagination page={page} totalPages={totalPages} setPage={setPage} />

      {selected && <FeedbackDrawer item={selected} onClose={() => setSelected(null)} onReview={handleRefresh} />}
      {showSubmit && <SubmitModal onClose={() => setShowSubmit(false)} onSuccess={handleRefresh} />}
    </div>
  );
}
