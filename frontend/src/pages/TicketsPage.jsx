import { useState } from "react";
import { useData } from "../hooks/useData";
import { api } from "../api/client";
import { COLORS, PRIORITY_COLORS } from "../utils/constants";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Btn from "../components/ui/Btn";
import Spinner from "../components/ui/Spinner";
import FilterSelect from "../components/ui/FilterSelect";
import Pagination from "../components/ui/Pagination";
import TicketCard from "../components/tickets/TicketCard";

const LIMIT = 25;

export default function TicketsPage() {
  const [filters, setFilters] = useState({ status: "", priority: "", category: "" });
  const [page, setPage] = useState(1);

  const buildQuery = () => {
    const p = new URLSearchParams({ limit: LIMIT, offset: (page - 1) * LIMIT });
    Object.entries(filters).forEach(([k, v]) => v && p.set(k, v));
    return `/tickets?${p}`;
  };

  const { data, loading, reload } = useData(() => api(buildQuery()), [JSON.stringify(filters), page], 30000);
  const tickets = data?.items || [];
  const totalPages = data?.total ? Math.ceil(data.total / LIMIT) : 1;

  const handleFilterChange = (field, value) => setFilters(f => ({ ...f, [field]: value }));

  const grouped = {};
  (tickets || []).forEach(t => {
    if (!grouped[t.priority]) grouped[t.priority] = [];
    grouped[t.priority].push(t);
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <div className="flex gap-2.5">
          <FilterSelect field="status" value={filters.status} options={["open", "in_progress", "resolved", "closed"]} onChange={handleFilterChange} />
          <FilterSelect field="priority" value={filters.priority} options={["Critical", "High", "Medium", "Low"]} onChange={handleFilterChange} />
          <FilterSelect field="category" value={filters.category} options={["Bug", "Feature Request", "Complaint", "Praise"]} onChange={handleFilterChange} />
        </div>
        <Btn variant="secondary" small onClick={reload}>↻ Refresh</Btn>
      </div>

      {loading ? (
        <div className="flex justify-center p-[60px]"><Spinner size={32} /></div>
      ) : !tickets?.length ? (
        <Card><div className="text-center text-muted p-10">No tickets yet. Process some feedback to generate tickets.</div></Card>
      ) : (
        ["Critical", "High", "Medium", "Low"].map(priority => {
          const items = grouped[priority];
          if (!items?.length) return null;
          return (
            <div key={priority}>
              <div className="flex items-center gap-2 mb-2.5">
                <Badge label={priority} color={PRIORITY_COLORS[priority]} />
                <span className="text-xs text-muted">{items.length} ticket{items.length !== 1 ? "s" : ""}</span>
              </div>
              <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-3">
                {items.map(t => <TicketCard key={t.id} ticket={t} onUpdate={reload} />)}
              </div>
            </div>
          );
        })
      )}
      <Pagination page={page} totalPages={totalPages} setPage={setPage} />
    </div>
  );
}
