import Badge from "../ui/Badge";
import { COLORS, CATEGORY_COLORS, PRIORITY_COLORS, SENTIMENT_COLORS } from "../../utils/constants";
import { fmtDateOnly } from "../../utils/date";

export default function FeedbackRow({ item, onSelect }) {
  const catColor = CATEGORY_COLORS[item.category] || COLORS.accent;
  const priColor = PRIORITY_COLORS[item.priority] || COLORS.accent;
  const sentColor = SENTIMENT_COLORS[item.sentiment] || COLORS.muted;

  return (
    <tr
      onClick={() => onSelect(item)}
      className="cursor-pointer border-b border-border hover:bg-surfaceAlt transition-colors"
    >
      <td className="px-4 py-3 max-w-[280px]">
        <div className="text-[13px] text-text overflow-hidden text-ellipsis whitespace-nowrap">
          {item.raw?.title || item.raw?.body?.slice(0, 60) || "—"}
        </div>
        <div className="text-[11px] text-muted mt-0.5">
          {item.raw?.source} · {fmtDateOnly(item.processed_at)}
        </div>
      </td>
      <td className="px-2 py-3"><Badge label={item.category} color={catColor} small /></td>
      <td className="px-2 py-3"><Badge label={item.priority} color={priColor} small /></td>
      <td className="px-2 py-3"><Badge label={item.sentiment} color={sentColor} small /></td>
      <td className="px-2 py-3">
        <Badge
          label={item.review_status}
          color={item.review_status === "pending" ? COLORS.warning : item.review_status === "approved" ? COLORS.success : COLORS.muted}
          small
        />
      </td>
      <td className="px-2 py-3 font-mono text-xs text-muted">
        {Math.round(item.confidence * 100)}%
      </td>
    </tr>
  );
}
