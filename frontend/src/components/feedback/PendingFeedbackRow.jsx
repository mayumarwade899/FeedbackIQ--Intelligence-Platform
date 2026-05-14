import { COLORS } from "../../utils/constants";
import Spinner from "../ui/Spinner";
import { fmtDateOnly } from "../../utils/date";

export default function PendingFeedbackRow({ item }) {
  return (
    <tr className="bg-surfaceAlt border-b border-border opacity-80">
      <td className="px-4 py-3 max-w-[280px]">
        <div className="text-[13px] text-text overflow-hidden text-ellipsis whitespace-nowrap">
          {item.title || item.body?.slice(0, 60) || "—"}
        </div>
        <div className="text-[11px] text-muted mt-0.5">
          {item.source} · {fmtDateOnly(item.ingested_at)}
        </div>
      </td>
      <td colSpan={5} className="px-4 py-3 text-accent">
        <div className="flex items-center gap-2.5">
          <Spinner size={14} />
          <span
            className="text-xs font-medium"
            style={{ color: item.processing_status === "processing" ? COLORS.success : COLORS.muted }}
          >
            {item.processing_status === "processing" ? "● AI Processing Pipeline Active..." : "○ Waiting in Queue..."}
          </span>
        </div>
      </td>
    </tr>
  );
}
