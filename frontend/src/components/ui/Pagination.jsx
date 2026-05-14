import { COLORS } from "../../utils/constants";

export default function Pagination({ page, totalPages, setPage }) {
  if (totalPages <= 1) return null;

  const pages = [];
  const maxVisible = 5;

  if (totalPages <= maxVisible) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (page > 3) pages.push("...");
    const start = Math.max(2, page - 1);
    const end = Math.min(totalPages - 1, page + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (page < totalPages - 2) pages.push("...");
    pages.push(totalPages);
  }

  return (
    <div className="flex justify-center items-center gap-3 mt-4">
      <button
        onClick={() => setPage(p => Math.max(1, p - 1))}
        disabled={page === 1}
        className="bg-transparent border-none text-sm font-medium p-0"
        style={{
          color: page === 1 ? COLORS.muted : COLORS.accent,
          cursor: page === 1 ? "default" : "pointer",
        }}
      >
        &lt; Previous
      </button>

      <div className="flex gap-1.5">
        {pages.map((p, i) =>
          p === "..." ? (
            <span key={`dots-${i}`} className="px-2 py-1 text-textDim font-semibold">...</span>
          ) : (
            <button
              key={`page-${p}-${i}`}
              onClick={() => setPage(p)}
              className="flex justify-center items-center w-8 h-8 rounded-lg cursor-pointer text-sm p-0"
              style={{
                background: page === p ? COLORS.surfaceAlt : "transparent",
                border: page === p ? `1px solid ${COLORS.border}` : "1px solid transparent",
                color: page === p ? COLORS.text : COLORS.accent,
                fontWeight: page === p ? 600 : 500,
              }}
            >
              {p}
            </button>
          )
        )}
      </div>

      <button
        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
        disabled={page === totalPages}
        className="bg-transparent border-none text-sm font-medium p-0"
        style={{
          color: page === totalPages ? COLORS.muted : COLORS.accent,
          cursor: page === totalPages ? "default" : "pointer",
        }}
      >
        Next &gt;
      </button>
    </div>
  );
}
