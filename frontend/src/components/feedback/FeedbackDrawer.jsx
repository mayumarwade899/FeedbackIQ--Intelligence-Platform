import { useState } from "react";
import Badge from "../ui/Badge";
import Btn from "../ui/Btn";
import { COLORS, CATEGORY_COLORS, PRIORITY_COLORS, SENTIMENT_COLORS } from "../../utils/constants";
import { api } from "../../api/client";

const CATEGORIES = ["Bug", "Feature Request", "Complaint", "Praise", "Spam", "Question"];
const PRIORITIES = ["Critical", "High", "Medium", "Low"];
const SENTIMENTS = ["positive", "negative", "neutral", "mixed"];

export default function FeedbackDrawer({ item, onClose, onReview }) {
  const [reviewing, setReviewing] = useState(false);
  const [reviewer, setReviewer] = useState("analyst");
  const [notes, setNotes] = useState("");
  const [overrideCategory, setOverrideCategory] = useState(item?.category || "");
  const [overridePriority, setOverridePriority] = useState(item?.priority || "");
  const [overrideSentiment, setOverrideSentiment] = useState(item?.sentiment || "");
  const [overrideConfidence, setOverrideConfidence] = useState(item ? Math.round(item.confidence * 100) : 100);

  if (!item) return null;

  const handleReview = async (action) => {
    setReviewing(true);
    try {
      const params = new URLSearchParams({
        action,
        reviewer,
        notes: notes || "",
        category: overrideCategory,
        priority: overridePriority,
        sentiment: overrideSentiment,
        confidence: (overrideConfidence / 100).toFixed(2),
      });
      await api(`/feedback/processed/${item.id}/review?${params.toString()}`, { method: "POST" });
      onReview();
      onClose();
    } catch (e) {
      alert("Review failed: " + e.message);
    } finally {
      setReviewing(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 flex justify-end"
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="w-[520px] bg-surface h-full overflow-y-auto border-l border-border p-6 flex flex-col gap-5"
      >
        <div className="flex justify-between items-start">
          <h3 className="m-0 text-base text-text">Feedback Detail</h3>
          <button onClick={onClose} className="bg-transparent border-none text-muted text-xl cursor-pointer">✕</button>
        </div>

        <div className="bg-surfaceAlt rounded-lg p-4">
          <div className="text-[13px] text-textDim leading-relaxed">
            {item.raw?.title && <div className="font-semibold text-text mb-2">{item.raw.title}</div>}
            {item.raw?.body}
          </div>
          <div className="mt-2 text-[11px] text-muted">
            Source: {item.raw?.source} · Author: {item.raw?.author || "Anonymous"}
          </div>
          {item.translated_body && item.translated_body !== item.raw?.body && (
            <div className="mt-2.5 pt-2.5 border-t border-border">
              <div className="text-[11px] text-accent mb-1 font-semibold">🌐 Translated (English)</div>
              <div className="text-xs text-textDim leading-relaxed">{item.translated_body}</div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          {[
            ["Category", item.category, CATEGORY_COLORS[item.category]],
            ["Priority", item.priority, PRIORITY_COLORS[item.priority]],
            ["Sentiment", item.sentiment, SENTIMENT_COLORS[item.sentiment]],
            ["Confidence", `${Math.round(item.confidence * 100)}%`, COLORS.accent],
          ].map(([label, val, color]) => (
            <div key={label} className="bg-surfaceAlt rounded-md p-3">
              <div className="text-[11px] text-muted mb-1">{label}</div>
              <div className="text-sm font-semibold" style={{ color: color || COLORS.text }}>{val}</div>
            </div>
          ))}
        </div>

        {item.emotion_tags?.length > 0 && (
          <div>
            <div className="text-xs text-muted mb-2">Emotions</div>
            <div className="flex gap-1.5 flex-wrap">
              {item.emotion_tags.map(t => <Badge key={t} label={t} color={COLORS.warning} small />)}
            </div>
          </div>
        )}

        {item.impact_summary && (
          <div>
            <div className="text-xs text-muted mb-1.5 font-semibold">Impact Summary</div>
            <div className="text-[13px] text-textDim leading-relaxed bg-surfaceAlt p-3 rounded-md">
              {item.impact_summary}
            </div>
          </div>
        )}

        {item.suggested_resolution && (
          <div>
            <div className="text-xs text-muted mb-1.5 font-semibold">Suggested Resolution</div>
            <div className="text-[13px] text-textDim leading-relaxed bg-surfaceAlt p-3 rounded-md border-l-[3px] border-l-success">
              {item.suggested_resolution}
            </div>
          </div>
        )}

        {item.is_duplicate && (
          <div className="bg-[#d2992222] border border-[#d2992244] rounded-md p-3">
            <div className="text-warning font-semibold text-[13px]">⚠ Duplicate Detected</div>
            <div className="text-xs text-muted mt-1">
              Similarity: {Math.round((item.similarity_score || 0) * 100)}%
            </div>
          </div>
        )}

        {item.review_status === "pending" && (
          <div className="border-t border-border pt-5">
            <div className="text-sm font-semibold text-text mb-3">Human Review</div>

            <div className="bg-surfaceAlt rounded-lg p-3.5 mb-3.5">
              <div className="text-xs text-accent font-semibold mb-2.5">✏ Override AI Classification (optional)</div>
              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="text-[11px] text-muted block mb-1">Category</label>
                  <select value={overrideCategory} onChange={e => setOverrideCategory(e.target.value)}
                    className="w-full bg-surfaceAlt border border-border rounded-md px-3 py-2 text-text text-[13px] cursor-pointer">
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] text-muted block mb-1">Priority</label>
                  <select value={overridePriority} onChange={e => setOverridePriority(e.target.value)}
                    className="w-full bg-surfaceAlt border border-border rounded-md px-3 py-2 text-text text-[13px] cursor-pointer">
                    {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] text-muted block mb-1">Sentiment</label>
                  <select value={overrideSentiment} onChange={e => setOverrideSentiment(e.target.value)}
                    className="w-full bg-surfaceAlt border border-border rounded-md px-3 py-2 text-text text-[13px] cursor-pointer">
                    {SENTIMENTS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-[11px] text-muted block mb-1">Confidence: {overrideConfidence}%</label>
                  <input
                    type="range" min={0} max={100} value={overrideConfidence}
                    onChange={e => setOverrideConfidence(Number(e.target.value))}
                    className="w-full accent-accent"
                  />
                </div>
              </div>
            </div>

            <div className="mb-2.5">
              <label className="text-xs text-muted block mb-1">Reviewer</label>
              <input value={reviewer} onChange={e => setReviewer(e.target.value)}
                className="w-full bg-surfaceAlt border border-border rounded-md px-3 py-2 text-text text-[13px]" />
            </div>
            <div className="mb-3.5">
              <label className="text-xs text-muted block mb-1">Notes (optional)</label>
              <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3}
                className="w-full bg-surfaceAlt border border-border rounded-md px-3 py-2 text-text text-[13px] resize-y" />
            </div>
            <div className="flex gap-2">
              <Btn onClick={() => handleReview("approve")} variant="success" loading={reviewing}>✓ Approve</Btn>
              <Btn onClick={() => handleReview("reject")} variant="danger" loading={reviewing}>✕ Reject</Btn>
              <Btn onClick={() => handleReview("modify")} variant="secondary" loading={reviewing}>✎ Modify</Btn>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
