import { useState, useEffect, useCallback, useRef } from "react";

// ── API Client ────────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:8000/api";

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

// ── Global State ──────────────────────────────────────────────────────────────
let _addToast = null;
function showToast(msg, type = "success") { _addToast?.(msg, type); }
const _cache = new Map();

// ── Date Formatting ───────────────────────────────────────────────────────────
// Backend returns ISO strings without 'Z', so we must append it to tell the
// browser these are UTC timestamps, which it will then convert to local time.
function fmtDate(ts, opts = {}) {
  if (!ts) return "—";
  const utc = ts.endsWith("Z") ? ts : ts + "Z";
  return new Date(utc).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
    ...opts,
  });
}
function fmtDateOnly(ts) {
  if (!ts) return "—";
  const utc = ts.endsWith("Z") ? ts : ts + "Z";
  return new Date(utc).toLocaleDateString("en-IN");
}

function useData(fetcher, deps = [], interval = 0) {
  const baseKey = JSON.stringify(deps) + (interval || 0);
  const cacheKey = baseKey + fetcher.toString().slice(0, 80);

  const [state, setState] = useState(() => ({
    cacheKey,
    data: _cache.get(cacheKey) ?? null,
    loading: !_cache.has(cacheKey),
    error: null
  }));

  if (state.cacheKey !== cacheKey) {
    setState({
      cacheKey,
      data: _cache.get(cacheKey) ?? null,
      loading: !_cache.has(cacheKey),
      error: null
    });
  }

  const load = useCallback(async () => {
    try {
      const result = await fetcher();
      _cache.set(cacheKey, result);
      setState(prev => ({ ...prev, data: result, loading: false, error: null }));
    } catch (e) {
      setState(prev => ({ ...prev, error: e.message, loading: false }));
    }
  }, deps);

  useEffect(() => {
    load();
    if (interval > 0) {
      const id = setInterval(load, interval);
      return () => clearInterval(id);
    }
  }, [load]);

  return { data: state.data, loading: state.loading, error: state.error, reload: load };
}

// ── Toast Component ───────────────────────────────────────────────────────────
function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    _addToast = (msg, type) => {
      const id = Date.now() + Math.random();
      setToasts(t => [...t, { id, msg, type }]);
      setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
    };
    return () => { _addToast = null; };
  }, []);

  const TOAST_COLORS = { success: COLORS.success, error: COLORS.danger, info: COLORS.accent, warning: COLORS.warning };
  const TOAST_ICONS  = { success: "✓", error: "✕", info: "ℹ", warning: "⚠" };

  return (
    <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999, display: "flex", flexDirection: "column", gap: 10, pointerEvents: "none" }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          display: "flex", alignItems: "flex-start", gap: 12,
          padding: "12px 16px", borderRadius: 10, minWidth: 280, maxWidth: 420,
          background: COLORS.surface, border: `1px solid ${TOAST_COLORS[t.type] || COLORS.border}44`,
          boxShadow: `0 4px 24px rgba(0,0,0,0.5), 0 0 0 1px ${TOAST_COLORS[t.type] || COLORS.border}22`,
          animation: "slideUp 0.25s ease", pointerEvents: "auto",
        }}>
          <span style={{ color: TOAST_COLORS[t.type] || COLORS.accent, fontSize: 16, lineHeight: 1.4, flexShrink: 0 }}>{TOAST_ICONS[t.type] || "ℹ"}</span>
          <span style={{ fontSize: 13, color: COLORS.text, lineHeight: 1.5 }}>{t.msg}</span>
        </div>
      ))}
      <style>{`@keyframes slideUp { from { opacity:0; transform:translateY(12px);} to { opacity:1; transform:translateY(0); } }`}</style>
    </div>
  );
}

// ── Design Tokens ─────────────────────────────────────────────────────────────
const COLORS = {
  bg: "#0a0c10",
  surface: "#111318",
  surfaceAlt: "#161b22",
  border: "#21262d",
  borderLight: "#30363d",
  accent: "#58a6ff",
  accentGlow: "rgba(88,166,255,0.15)",
  success: "#3fb950",
  warning: "#d29922",
  danger: "#f85149",
  muted: "#8b949e",
  text: "#e6edf3",
  textDim: "#b1bac4",
};

const PRIORITY_COLORS = {
  Critical: "#f85149",
  High: "#d29922",
  Medium: "#58a6ff",
  Low: "#3fb950",
};

const CATEGORY_COLORS = {
  Bug: "#f85149",
  "Feature Request": "#a371f7",
  Complaint: "#d29922",
  Praise: "#3fb950",
  Spam: "#8b949e",
  Question: "#58a6ff",
};

const SENTIMENT_COLORS = {
  positive: "#3fb950",
  negative: "#f85149",
  neutral: "#8b949e",
  mixed: "#d29922",
};

// ── Utility Components ────────────────────────────────────────────────────────
function Badge({ label, color, small }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: small ? "2px 6px" : "3px 10px",
      borderRadius: 4,
      fontSize: small ? 10 : 11,
      fontWeight: 600,
      letterSpacing: "0.04em",
      textTransform: "uppercase",
      background: color + "22",
      color: color,
      border: `1px solid ${color}44`,
      whiteSpace: "nowrap",
    }}>
      {label}
    </span>
  );
}

function Spinner({ size = 20 }) {
  return (
    <div style={{
      width: size, height: size,
      border: `2px solid ${COLORS.border}`,
      borderTop: `2px solid ${COLORS.accent}`,
      borderRadius: "50%",
      animation: "spin 0.8s linear infinite",
    }} />
  );
}

function Card({ children, style, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: COLORS.surface,
      border: `1px solid ${COLORS.border}`,
      borderRadius: 8,
      padding: 20,
      cursor: onClick ? "pointer" : "default",
      transition: "border-color 0.15s",
      ...style,
    }}
      onMouseEnter={e => onClick && (e.currentTarget.style.borderColor = COLORS.borderLight)}
      onMouseLeave={e => onClick && (e.currentTarget.style.borderColor = COLORS.border)}
    >
      {children}
    </div>
  );
}

function MetricCard({ label, value, sub, accent }) {
  return (
    <Card>
      <div style={{ fontSize: 12, color: COLORS.muted, fontWeight: 500, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontSize: 32, fontWeight: 700, color: accent || COLORS.text, lineHeight: 1, fontFamily: "'JetBrains Mono', monospace" }}>
        {value ?? "—"}
      </div>
      {sub && <div style={{ fontSize: 12, color: COLORS.muted, marginTop: 6 }}>{sub}</div>}
    </Card>
  );
}

function SectionHeader({ title, action }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
      <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: COLORS.text }}>{title}</h2>
      {action}
    </div>
  );
}

function Btn({ children, onClick, variant = "primary", small, loading: isLoading, disabled }) {
  const variants = {
    primary: { background: COLORS.accent, color: "#0a0c10", border: "none" },
    secondary: { background: "transparent", color: COLORS.textDim, border: `1px solid ${COLORS.border}` },
    danger: { background: "transparent", color: COLORS.danger, border: `1px solid ${COLORS.danger}44` },
    success: { background: "transparent", color: COLORS.success, border: `1px solid ${COLORS.success}44` },
  };
  const v = variants[variant] || variants.primary;
  return (
    <button onClick={onClick} disabled={disabled || isLoading} style={{
      ...v, padding: small ? "5px 12px" : "8px 16px",
      borderRadius: 6, fontSize: small ? 12 : 13, fontWeight: 600,
      cursor: disabled || isLoading ? "not-allowed" : "pointer",
      opacity: disabled ? 0.5 : 1,
      display: "inline-flex", alignItems: "center", gap: 6,
      transition: "opacity 0.15s",
    }}>
      {isLoading && <Spinner size={12} />}
      {children}
    </button>
  );
}

// ── Inline bar chart ─────────────────────────────────────────────────────────
function DistributionBar({ data, colorMap }) {
  if (!data || !Object.keys(data).length) return <div style={{ color: COLORS.muted, fontSize: 13 }}>No data</div>;
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {Object.entries(data).sort((a, b) => b[1] - a[1]).map(([key, val]) => {
        const pct = total > 0 ? Math.round((val / total) * 100) : 0;
        const color = (colorMap && colorMap[key]) || COLORS.accent;
        return (
          <div key={key}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12 }}>
              <span style={{ color: COLORS.textDim }}>{key}</span>
              <span style={{ color: COLORS.text, fontFamily: "monospace" }}>{val} <span style={{ color: COLORS.muted }}>({pct}%)</span></span>
            </div>
            <div style={{ background: COLORS.border, borderRadius: 3, height: 6, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3, transition: "width 0.5s ease" }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Mini sparkline ────────────────────────────────────────────────────────────
function Sparkline({ points, color = COLORS.accent, height = 40 }) {
  if (!points || points.length < 2) return null;
  const max = Math.max(...points, 1);
  const w = 160, h = height;
  const pts = points.map((v, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - (v / max) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={`0,${h} ${pts} ${w},${h}`} fill={color + "22"} stroke="none" />
    </svg>
  );
}

// ── Pipeline diagram ──────────────────────────────────────────────────────────
function PipelineFlow() {
  const agents = [
    { name: "Ingestion", icon: "⬇", color: "#58a6ff" },
    { name: "Classification", icon: "🏷", color: "#a371f7" },
    { name: "Sentiment", icon: "💬", color: "#3fb950" },
    { name: "Dedup", icon: "🔍", color: "#d29922" },
    { name: "Insights", icon: "💡", color: "#f0883e" },
    { name: "Ticket Gen", icon: "🎫", color: "#ec6547" },
  ];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 0, overflowX: "auto", paddingBottom: 4 }}>
      {agents.map((a, i) => (
        <div key={a.name} style={{ display: "flex", alignItems: "center" }}>
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center",
            padding: "10px 14px",
            background: a.color + "15",
            border: `1px solid ${a.color}44`,
            borderRadius: 8, minWidth: 80, gap: 4,
          }}>
            <span style={{ fontSize: 18 }}>{a.icon}</span>
            <span style={{ fontSize: 11, fontWeight: 600, color: a.color, whiteSpace: "nowrap" }}>{a.name}</span>
          </div>
          {i < agents.length - 1 && (
            <div style={{ color: COLORS.muted, fontSize: 16, padding: "0 4px" }}>→</div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Pending Feedback Table Row ────────────────────────────────────────────────
function PendingFeedbackRow({ item }) {
  return (
    <tr style={{ background: COLORS.surfaceAlt, borderBottom: `1px solid ${COLORS.border}`, opacity: 0.8 }}>
      <td style={{ padding: "12px 16px", maxWidth: 280 }}>
        <div style={{ fontSize: 13, color: COLORS.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {item.title || item.body?.slice(0, 60) || "—"}
        </div>
        <div style={{ fontSize: 11, color: COLORS.muted, marginTop: 2 }}>
          {item.source} · {fmtDateOnly(item.ingested_at)}
        </div>
      </td>
      <td colSpan={5} style={{ padding: "12px 16px", color: COLORS.accent }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Spinner size={14} />
          <span style={{ fontSize: 12, fontWeight: 500, color: item.processing_status === 'processing' ? COLORS.success : COLORS.textMuted }}>
            {item.processing_status === 'processing' ? '● AI Processing Pipeline Active...' : '○ Waiting in Queue...'}
          </span>
        </div>
      </td>
    </tr>
  );
}



// ── Feedback Table Row ────────────────────────────────────────────────────────
function FeedbackRow({ item, onSelect }) {
  const catColor = CATEGORY_COLORS[item.category] || COLORS.accent;
  const priColor = PRIORITY_COLORS[item.priority] || COLORS.accent;
  const sentColor = SENTIMENT_COLORS[item.sentiment] || COLORS.muted;

  return (
    <tr
      onClick={() => onSelect(item)}
      style={{ cursor: "pointer", borderBottom: `1px solid ${COLORS.border}` }}
      onMouseEnter={e => e.currentTarget.style.background = COLORS.surfaceAlt}
      onMouseLeave={e => e.currentTarget.style.background = "transparent"}
    >
      <td style={{ padding: "12px 16px", maxWidth: 280 }}>
        <div style={{ fontSize: 13, color: COLORS.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {item.raw?.title || item.raw?.body?.slice(0, 60) || "—"}
        </div>
        <div style={{ fontSize: 11, color: COLORS.muted, marginTop: 2 }}>
          {item.raw?.source} · {fmtDateOnly(item.processed_at)}
        </div>
      </td>
      <td style={{ padding: "12px 8px" }}><Badge label={item.category} color={catColor} small /></td>
      <td style={{ padding: "12px 8px" }}><Badge label={item.priority} color={priColor} small /></td>
      <td style={{ padding: "12px 8px" }}><Badge label={item.sentiment} color={sentColor} small /></td>
      <td style={{ padding: "12px 8px" }}>
        <Badge
          label={item.review_status}
          color={item.review_status === "pending" ? COLORS.warning : item.review_status === "approved" ? COLORS.success : COLORS.muted}
          small
        />
      </td>
      <td style={{ padding: "12px 8px", fontFamily: "monospace", fontSize: 12, color: COLORS.muted }}>
        {Math.round(item.confidence * 100)}%
      </td>
    </tr>
  );
}

// ── Feedback Detail Drawer ────────────────────────────────────────────────────
function FeedbackDrawer({ item, onClose, onReview }) {
  const [reviewing, setReviewing] = useState(false);
  const [reviewer, setReviewer] = useState("analyst");
  const [notes, setNotes] = useState("");
  const [overrideCategory, setOverrideCategory] = useState(item?.category || "");
  const [overridePriority, setOverridePriority] = useState(item?.priority || "");
  const [overrideSentiment, setOverrideSentiment] = useState(item?.sentiment || "");
  const [overrideConfidence, setOverrideConfidence] = useState(item ? Math.round(item.confidence * 100) : 100);

  if (!item) return null;

  const selectStyle = {
    width: "100%", background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`,
    borderRadius: 6, padding: "8px 12px", color: COLORS.text, fontSize: 13,
    boxSizing: "border-box", cursor: "pointer",
  };

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
    <div style={{
      position: "fixed", inset: 0, zIndex: 100,
      background: "rgba(0,0,0,0.7)", display: "flex", justifyContent: "flex-end",
    }} onClick={onClose}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 520, background: COLORS.surface, height: "100%",
          overflowY: "auto", borderLeft: `1px solid ${COLORS.border}`,
          padding: 24, display: "flex", flexDirection: "column", gap: 20,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <h3 style={{ margin: 0, fontSize: 16, color: COLORS.text }}>Feedback Detail</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: COLORS.muted, fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>

        <div style={{ background: COLORS.surfaceAlt, borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: 13, color: COLORS.textDim, lineHeight: 1.6 }}>
            {item.raw?.title && <div style={{ fontWeight: 600, color: COLORS.text, marginBottom: 8 }}>{item.raw.title}</div>}
            {item.raw?.body}
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: COLORS.muted }}>
            Source: {item.raw?.source} · Author: {item.raw?.author || "Anonymous"}
          </div>
          {item.translated_body && item.translated_body !== item.raw?.body && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${COLORS.border}` }}>
              <div style={{ fontSize: 11, color: COLORS.accent, marginBottom: 4, fontWeight: 600 }}>🌐 Translated (English)</div>
              <div style={{ fontSize: 12, color: COLORS.textDim, lineHeight: 1.6 }}>{item.translated_body}</div>
            </div>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {[
            ["Category", item.category, CATEGORY_COLORS[item.category]],
            ["Priority", item.priority, PRIORITY_COLORS[item.priority]],
            ["Sentiment", item.sentiment, SENTIMENT_COLORS[item.sentiment]],
            ["Confidence", `${Math.round(item.confidence * 100)}%`, COLORS.accent],
          ].map(([label, val, color]) => (
            <div key={label} style={{ background: COLORS.surfaceAlt, borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 11, color: COLORS.muted, marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: color || COLORS.text }}>{val}</div>
            </div>
          ))}
        </div>

        {item.emotion_tags?.length > 0 && (
          <div>
            <div style={{ fontSize: 12, color: COLORS.muted, marginBottom: 8 }}>Emotions</div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {item.emotion_tags.map(t => <Badge key={t} label={t} color={COLORS.warning} small />)}
            </div>
          </div>
        )}

        {item.impact_summary && (
          <div>
            <div style={{ fontSize: 12, color: COLORS.muted, marginBottom: 6, fontWeight: 600 }}>Impact Summary</div>
            <div style={{ fontSize: 13, color: COLORS.textDim, lineHeight: 1.6, background: COLORS.surfaceAlt, padding: 12, borderRadius: 6 }}>
              {item.impact_summary}
            </div>
          </div>
        )}

        {item.suggested_resolution && (
          <div>
            <div style={{ fontSize: 12, color: COLORS.muted, marginBottom: 6, fontWeight: 600 }}>Suggested Resolution</div>
            <div style={{ fontSize: 13, color: COLORS.textDim, lineHeight: 1.6, background: COLORS.surfaceAlt, padding: 12, borderRadius: 6, borderLeft: `3px solid ${COLORS.success}` }}>
              {item.suggested_resolution}
            </div>
          </div>
        )}

        {item.is_duplicate && (
          <div style={{ background: "#d2992222", border: `1px solid ${COLORS.warning}44`, borderRadius: 6, padding: 12 }}>
            <div style={{ color: COLORS.warning, fontWeight: 600, fontSize: 13 }}>⚠ Duplicate Detected</div>
            <div style={{ fontSize: 12, color: COLORS.muted, marginTop: 4 }}>
              Similarity: {Math.round((item.similarity_score || 0) * 100)}%
            </div>
          </div>
        )}

        {item.review_status === "pending" && (
          <div style={{ borderTop: `1px solid ${COLORS.border}`, paddingTop: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text, marginBottom: 12 }}>Human Review</div>

            {/* ── Override Classification Fields ── */}
            <div style={{ background: COLORS.surfaceAlt, borderRadius: 8, padding: 14, marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: COLORS.accent, fontWeight: 600, marginBottom: 10 }}>✏ Override AI Classification (optional)</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, color: COLORS.muted, display: "block", marginBottom: 4 }}>Category</label>
                  <select value={overrideCategory} onChange={e => setOverrideCategory(e.target.value)} style={selectStyle}>
                    {["Bug", "Feature Request", "Complaint", "Praise", "Spam", "Question"].map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, color: COLORS.muted, display: "block", marginBottom: 4 }}>Priority</label>
                  <select value={overridePriority} onChange={e => setOverridePriority(e.target.value)} style={selectStyle}>
                    {["Critical", "High", "Medium", "Low"].map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, color: COLORS.muted, display: "block", marginBottom: 4 }}>Sentiment</label>
                  <select value={overrideSentiment} onChange={e => setOverrideSentiment(e.target.value)} style={selectStyle}>
                    {["positive", "negative", "neutral", "mixed"].map(s => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: 11, color: COLORS.muted, display: "block", marginBottom: 4 }}>Confidence: {overrideConfidence}%</label>
                  <input
                    type="range" min={0} max={100} value={overrideConfidence}
                    onChange={e => setOverrideConfidence(Number(e.target.value))}
                    style={{ width: "100%", accentColor: COLORS.accent }}
                  />
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 10 }}>
              <label style={{ fontSize: 12, color: COLORS.muted, display: "block", marginBottom: 4 }}>Reviewer</label>
              <input
                value={reviewer} onChange={e => setReviewer(e.target.value)}
                style={{ width: "100%", background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 6, padding: "8px 12px", color: COLORS.text, fontSize: 13, boxSizing: "border-box" }}
              />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: COLORS.muted, display: "block", marginBottom: 4 }}>Notes (optional)</label>
              <textarea
                value={notes} onChange={e => setNotes(e.target.value)} rows={3}
                style={{ width: "100%", background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 6, padding: "8px 12px", color: COLORS.text, fontSize: 13, resize: "vertical", boxSizing: "border-box" }}
              />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
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

// ── Submit Feedback Modal ─────────────────────────────────────────────────────
function SubmitModal({ onClose, onSuccess }) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async () => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      await api("/feedback/submit", {
        method: "POST",
        body: JSON.stringify({ text, title, author, source: "manual" }),
      });
      onSuccess();
      onClose();
    } catch (e) {
      showToast("Submission failed: " + e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.8)", display: "flex", alignItems: "center", justifyContent: "center" }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ width: 500, background: COLORS.surface, borderRadius: 12, border: `1px solid ${COLORS.border}`, padding: 28 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <h3 style={{ margin: 0, color: COLORS.text }}>Submit Feedback</h3>
          <button onClick={onClose} style={{ background: "none", border: "none", color: COLORS.muted, fontSize: 20, cursor: "pointer" }}>✕</button>
        </div>
        <>
          {[
            ["Title (optional)", title, setTitle, "text", 1],
            ["Author (optional)", author, setAuthor, "text", 1],
          ].map(([label, val, setter, type, rows]) => (
            <div key={label} style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, color: COLORS.muted, display: "block", marginBottom: 4 }}>{label}</label>
              <input value={val} onChange={e => setter(e.target.value)}
                style={{ width: "100%", background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 6, padding: "8px 12px", color: COLORS.text, fontSize: 13, boxSizing: "border-box" }} />
            </div>
          ))}
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 12, color: COLORS.muted, display: "block", marginBottom: 4 }}>Feedback <span style={{ color: COLORS.danger }}>*</span></label>
            <textarea value={text} onChange={e => setText(e.target.value)} rows={5}
              placeholder="Describe the issue, feature request, or feedback..."
              style={{ width: "100%", background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 6, padding: "8px 12px", color: COLORS.text, fontSize: 13, resize: "vertical", boxSizing: "border-box" }} />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
            <Btn onClick={submit} loading={loading} disabled={!text.trim()}>Submit & Process</Btn>
          </div>
        </>
      </div>
    </div>
  );
}

// ── Ticket Card ───────────────────────────────────────────────────────────────
function TicketCard({ ticket, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState(ticket.status);
  const [saving, setSaving] = useState(false);

  const statuses = ["open", "in_progress", "resolved", "closed"];
  const priColor = PRIORITY_COLORS[ticket.priority] || COLORS.accent;
  const catColor = CATEGORY_COLORS[ticket.category] || COLORS.accent;

  const save = async () => {
    setSaving(true);
    try {
      await api(`/tickets/${ticket.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      onUpdate();
      setEditing(false);
    } catch (e) {
      showToast("Ticket update failed: " + e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div style={{ fontSize: 11, fontFamily: "monospace", color: COLORS.muted }}>{ticket.ticket_number}</div>
        <div style={{ display: "flex", gap: 6 }}>
          <Badge label={ticket.priority} color={priColor} small />
          <Badge label={ticket.category} color={catColor} small />
        </div>
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color: COLORS.text, marginBottom: 8, lineHeight: 1.4 }}>
        {ticket.title}
      </div>
      {ticket.impact_summary && (
        <div style={{ fontSize: 12, color: COLORS.textDim, marginBottom: 10, lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          {ticket.impact_summary}
        </div>
      )}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
        {editing ? (
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <select value={status} onChange={e => setStatus(e.target.value)}
              style={{ background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 4, color: COLORS.text, padding: "4px 8px", fontSize: 12 }}>
              {statuses.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <Btn small onClick={save} loading={saving}>Save</Btn>
            <Btn small variant="secondary" onClick={() => setEditing(false)}>Cancel</Btn>
          </div>
        ) : (
          <Badge
            label={ticket.status}
            color={ticket.status === "open" ? COLORS.danger : ticket.status === "resolved" ? COLORS.success : ticket.status === "in_progress" ? COLORS.warning : COLORS.muted}
            small
          />
        )}
        {!editing && <Btn small variant="secondary" onClick={() => setEditing(true)}>Edit</Btn>}
      </div>
      {ticket.labels?.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", gap: 4, flexWrap: "wrap" }}>
          {ticket.labels.map(l => (
            <span key={l} style={{ fontSize: 10, background: COLORS.border, color: COLORS.muted, padding: "2px 6px", borderRadius: 3 }}>{l}</span>
          ))}
        </div>
      )}
    </Card>
  );
}

// ── Monitoring Panel ──────────────────────────────────────────────────────────
function MonitoringPanel() {
  const { data: metrics } = useData(() => api("/monitoring/metrics"), [], 15000);

  if (!metrics) return <div style={{ color: COLORS.muted, textAlign: "center", padding: 40, fontSize: 13 }}>Loading metrics…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <MetricCard label="Total Runs (7d)" value={metrics?.total_runs_24h ?? 0} />
        <MetricCard label="Total Tokens (7d)" value={metrics?.total_tokens_24h?.toLocaleString() ?? 0} />
        <MetricCard label="Estimated Cost" value={`$${metrics?.total_cost_24h_usd ?? 0}`} accent={COLORS.success} />
        <MetricCard label="Last Ingestion" value={metrics?.last_ingestion ? fmtDate(metrics.last_ingestion, { hour: "2-digit", minute: "2-digit", second: undefined }) : "Never"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <SectionHeader title="Agent Success Rate" />
          {metrics?.agent_success_rate && Object.keys(metrics.agent_success_rate).length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(metrics.agent_success_rate).map(([name, rate]) => (
                <div key={name}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                    <span style={{ color: COLORS.textDim }}>{name.replace(/_/g, " ")}</span>
                    <span style={{ color: rate > 0.9 ? COLORS.success : rate > 0.7 ? COLORS.warning : COLORS.danger, fontFamily: "monospace" }}>
                      {Math.round(rate * 100)}%
                    </span>
                  </div>
                  <div style={{ background: COLORS.border, borderRadius: 3, height: 4 }}>
                    <div style={{ width: `${rate * 100}%`, height: "100%", background: rate > 0.9 ? COLORS.success : rate > 0.7 ? COLORS.warning : COLORS.danger, borderRadius: 3 }} />
                  </div>
                </div>
              ))}
            </div>
          ) : <div style={{ color: COLORS.muted, fontSize: 13 }}>No agent data yet</div>}
        </Card>

        <Card>
          <SectionHeader title="Avg Latency (ms)" />
          {metrics?.agent_avg_latency && Object.keys(metrics.agent_avg_latency).length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(metrics.agent_avg_latency).map(([name, lat]) => (
                <div key={name} style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span style={{ color: COLORS.textDim }}>{name.replace(/_/g, " ")}</span>
                  <span style={{ fontFamily: "monospace", color: lat < 500 ? COLORS.success : lat < 2000 ? COLORS.warning : COLORS.danger }}>{Math.round(lat)}ms</span>
                </div>
              ))}
            </div>
          ) : <div style={{ color: COLORS.muted, fontSize: 13 }}>No latency data yet</div>}
        </Card>
      </div>

      <Card>
        <SectionHeader title="Recent Agent Runs" />
        <RecentAgentRunsTable />
      </Card>
    </div>
  );
}

function RecentAgentRunsTable() {
  const { data: runs } = useData(() => api("/monitoring/agent-runs?limit=20"), [], 15000);
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${COLORS.border}` }}>
            {["Agent", "Status", "Latency", "Tokens", "Cost", "Started At"].map(h => (
              <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: COLORS.muted, fontWeight: 500 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {(runs || []).map(run => (
            <tr key={run.id} style={{ borderBottom: `1px solid ${COLORS.border}` }}>
              <td style={{ padding: "8px 12px", color: COLORS.textDim }}>{run.agent_name.replace(/_/g, " ")}</td>
              <td style={{ padding: "8px 12px" }}>
                <Badge label={run.status} color={run.status === "success" ? COLORS.success : run.status === "failed" ? COLORS.danger : COLORS.muted} small />
              </td>
              <td style={{ padding: "8px 12px", fontFamily: "monospace", color: COLORS.muted }}>{run.latency_ms ? `${Math.round(run.latency_ms)}ms` : "—"}</td>
              <td style={{ padding: "8px 12px", fontFamily: "monospace", color: COLORS.muted }}>{run.tokens_used?.toLocaleString() ?? "—"}</td>
              <td style={{ padding: "8px 12px", fontFamily: "monospace", color: COLORS.success }}>${run.estimated_cost?.toFixed(5) ?? "0.00"}</td>
              <td style={{ padding: "8px 12px", color: COLORS.muted }}>{fmtDate(run.started_at)}</td>
            </tr>
          ))}
          {!runs?.length && (
            <tr><td colSpan={4} style={{ padding: 20, textAlign: "center", color: COLORS.muted }}>No agent runs recorded yet</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

// ── Ingestion Sources Status ──────────────────────────────────────────────────
function IngestionSourcesPanel({ onTrigger }) {
  const [triggering, setTriggering] = useState(false);
  const [triggeringGP, setTriggeringGP] = useState(false);

  // Track how many items were pending when fetch started so we can report
  // how many were actually processed when the run finishes.
  const pendingAtStartRef = useRef(0);

  // Poll the processed feedback list for real completion after Fetch Now.
  // Fires a single success toast when all newly-fetched items finish processing.
  useEffect(() => {
    if (!triggeringGP) return;

    let staleCount = 0; // guard against items stuck in "processing" forever

    const poll = async () => {
      try {
        const raw = await api("/feedback/raw?source=google_play&limit=200");
        const pending = raw.filter(r => !r.processed).length;

        if (pending === 0 && raw.length > 0) {
          const processed = raw.length - pendingAtStartRef.current;
          const count = Math.max(processed, raw.length);
          showToast(`✓ Successfully processed ${count} reviews.`, "success");
          setTriggeringGP(false);
          onTrigger?.();
          return;
        }

        // Safety exit: if pending count hasn't changed for 10 polls (~30 s),
        // stop polling silently (items may be stuck or were already processed).
        staleCount++;
        if (staleCount >= 10) {
          setTriggeringGP(false);
          onTrigger?.();
        }
      } catch {
        /* ignore transient network errors */
      }
    };

    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, [triggeringGP]);

  const sources = [
    { id: "github", label: "GitHub Issues", icon: "⚙", desc: "Fetches open issues from configured repository" },
    { id: "reddit", label: "Reddit", icon: "💬", desc: "Monitors configured subreddits for relevant posts" },
    { id: "google_play", label: "Google Play Reviews", icon: "▶", desc: "Fetches newest reviews for com.spotify.music" },
    { id: "manual", label: "Manual / API", icon: "📥", desc: "Direct submission via dashboard or REST API" },
  ];

  const trigger = async () => {
    setTriggering(true);
    try {
      await api("/ingestion/trigger", { method: "POST" });
      showToast("Ingestion cycle triggered successfully", "success");
      onTrigger?.();
    } catch (e) {
      showToast("Trigger failed: " + e.message, "error");
    } finally {
      setTriggering(false);
    }
  };

  const triggerGooglePlay = async () => {
    setTriggeringGP(true);
    try {
      // Record current pending count before fetching so we can compute delta
      const raw = await api("/feedback/raw?source=google_play&limit=200");
      pendingAtStartRef.current = raw.filter(r => !r.processed).length;

      await api("/ingestion/trigger-google-play", { method: "POST" });
      showToast(
        "Fetching reviews for Spotify. You can monitor real-time progress in the Feedback page.",
        "info"
      );
    } catch (e) {
      showToast("Failed: " + e.message, "error");
      setTriggeringGP(false);
    }
  };

  return (
    <Card>
      <SectionHeader
        title="Ingestion Sources"
        action={<Btn small onClick={trigger} loading={triggering}>▶ Trigger All</Btn>}
      />
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {sources.map(src => (
          <div key={src.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 14px", background: COLORS.surfaceAlt, borderRadius: 6 }}>
            <span style={{ fontSize: 20 }}>{src.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: COLORS.text }}>{src.label}</div>
              <div style={{ fontSize: 11, color: COLORS.muted, marginTop: 2 }}>{src.desc}</div>
            </div>
            {src.id === "google_play" && (
              <Btn small variant="secondary" onClick={triggerGooglePlay} loading={triggeringGP} disabled={triggeringGP}>
                {triggeringGP ? "Ingesting…" : "Fetch Now"}
              </Btn>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}



// ── Pages ─────────────────────────────────────────────────────────────────────
function OverviewPage() {
  const { data: overview, loading, reload } = useData(() => api("/analytics/overview"), [], 30000);
  const { data: topIssues } = useData(() => api("/analytics/top-issues"), []);

  if (!overview && !topIssues) return <div style={{ color: COLORS.muted, textAlign: "center", padding: 60, fontSize: 13 }}>Loading…</div>;

  const ov = overview || {};

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <MetricCard label="Total Feedback" value={ov.total_feedback ?? 0} />
        <MetricCard label="Processed Today" value={ov.processed_today ?? 0} accent={COLORS.accent} />
        <MetricCard label="Pending Review" value={ov.pending_review ?? 0} accent={ov.pending_review > 10 ? COLORS.warning : COLORS.text} />
        <MetricCard label="Open Tickets" value={ov.open_tickets ?? 0} accent={COLORS.success} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        <MetricCard label="Avg Confidence" value={`${Math.round((ov.avg_confidence ?? 0) * 100)}%`} />
        <MetricCard label="Success Rate" value={`${Math.round((ov.processing_success_rate ?? 0) * 100)}%`} accent={COLORS.success} />
        <MetricCard label="Avg Latency" value={`${Math.round(ov.avg_agent_latency_ms ?? 0)}ms`} />
        <MetricCard label="Total Tokens" value={ov.total_tokens?.toLocaleString() ?? 0} />
        <MetricCard label="Total Cost" value={`$${ov.total_cost_usd?.toFixed(4) ?? 0}`} accent={COLORS.success} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
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

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <SectionHeader title="By Source" />
          <DistributionBar data={ov.source_distribution} />
        </Card>
        <IngestionSourcesPanel onTrigger={reload} />
      </div>
    </div>
  );
}

function Pagination({ page, totalPages, setPage }) {
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
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 12, marginTop: 16 }}>
      <button 
        onClick={() => setPage(p => Math.max(1, p - 1))} 
        disabled={page === 1}
        style={{ background: "transparent", border: "none", color: page === 1 ? COLORS.muted : COLORS.accent, cursor: page === 1 ? "default" : "pointer", fontSize: 14, fontWeight: 500, padding: 0 }}
      >
        &lt; Previous
      </button>

      <div style={{ display: "flex", gap: 6 }}>
        {pages.map((p, i) => p === "..." ? (
          <span key={`dots-${i}`} style={{ padding: "4px 8px", color: COLORS.textDim, fontWeight: 600 }}>...</span>
        ) : (
          <button 
            key={`page-${p}-${i}`} 
            onClick={() => setPage(p)}
            style={{ 
              background: page === p ? COLORS.surfaceAlt : "transparent",
              border: page === p ? `1px solid ${COLORS.border}` : "1px solid transparent",
              color: page === p ? COLORS.text : COLORS.accent,
              borderRadius: 8, width: 32, height: 32,
              display: "flex", justifyContent: "center", alignItems: "center",
              cursor: "pointer", fontSize: 14, fontWeight: page === p ? 600 : 500, padding: 0
            }}
          >
            {p}
          </button>
        ))}
      </div>

      <button 
        onClick={() => setPage(p => Math.min(totalPages, p + 1))} 
        disabled={page === totalPages}
        style={{ background: "transparent", border: "none", color: page === totalPages ? COLORS.muted : COLORS.accent, cursor: page === totalPages ? "default" : "pointer", fontSize: 14, fontWeight: 500, padding: 0 }}
      >
        Next &gt;
      </button>
    </div>
  );
}

function FeedbackPage() {
  const [filters, setFilters] = useState({ category: "", priority: "", sentiment: "", review_status: "" });
  const [selected, setSelected] = useState(null);
  const [showSubmit, setShowSubmit] = useState(false);
  const [page, setPage] = useState(1);
  const limit = 25;

  const buildQuery = () => {
    const params = new URLSearchParams({ limit, offset: (page - 1) * limit });
    Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
    return `/feedback/processed?${params}`;
  };

  const { data, loading, reload } = useData(() => api(buildQuery()), [JSON.stringify(filters), page], 5000);
  const feedback = data?.items || [];
  const totalPages = data?.total ? Math.ceil(data.total / limit) : 1;
  const { data: pendingFeedback, reload: reloadPending } = useData(() => api("/feedback/raw?processed=false&limit=10"), [], 5000);

  const handleRefresh = () => { reload(); reloadPending && reloadPending(); };

  const FilterSelect = ({ field, options }) => (
    <select value={filters[field]} onChange={e => setFilters(f => ({ ...f, [field]: e.target.value }))}
      style={{ background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 6, color: COLORS.text, padding: "6px 10px", fontSize: 12, cursor: "pointer" }}>
      <option value="">All {field}s</option>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <FilterSelect field="category" options={["Bug", "Feature Request", "Complaint", "Praise", "Spam"]} />
          <FilterSelect field="priority" options={["Critical", "High", "Medium", "Low"]} />
          <FilterSelect field="sentiment" options={["positive", "negative", "neutral", "mixed"]} />
          <FilterSelect field="review_status" options={["pending", "approved", "rejected"]} />
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn variant="secondary" small onClick={handleRefresh}>↻ Refresh</Btn>
          <Btn small onClick={() => setShowSubmit(true)}>+ Submit</Btn>
        </div>
      </div>

      <Card style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: 40 }}><Spinner size={32} /></div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: COLORS.surfaceAlt, borderBottom: `1px solid ${COLORS.border}` }}>
                  {["Feedback", "Category", "Priority", "Sentiment", "Review", "Confidence"].map(h => (
                    <th key={h} style={{ padding: "10px 16px", textAlign: "left", color: COLORS.muted, fontSize: 12, fontWeight: 500, whiteSpace: "nowrap" }}>{h}</th>
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
                  <tr><td colSpan={6} style={{ padding: 40, textAlign: "center", color: COLORS.muted }}>
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

function TicketsPage() {
  const [filters, setFilters] = useState({ status: "", priority: "", category: "" });
  const [page, setPage] = useState(1);
  const limit = 25;

  const buildQuery = () => {
    const p = new URLSearchParams({ limit, offset: (page - 1) * limit });
    Object.entries(filters).forEach(([k, v]) => v && p.set(k, v));
    return `/tickets?${p}`;
  };
  const { data, loading, reload } = useData(() => api(buildQuery()), [JSON.stringify(filters), page], 30000);
  const tickets = data?.items || [];
  const totalPages = data?.total ? Math.ceil(data.total / limit) : 1;

  const FilterSelect = ({ field, options }) => (
    <select value={filters[field]} onChange={e => setFilters(f => ({ ...f, [field]: e.target.value }))}
      style={{ background: COLORS.surfaceAlt, border: `1px solid ${COLORS.border}`, borderRadius: 6, color: COLORS.text, padding: "6px 10px", fontSize: 12, cursor: "pointer" }}>
      <option value="">All {field}s</option>
      {options.map(o => <option key={o} value={o}>{o}</option>)}
    </select>
  );

  const grouped = {};
  (tickets || []).forEach(t => {
    if (!grouped[t.priority]) grouped[t.priority] = [];
    grouped[t.priority].push(t);
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 10 }}>
          <FilterSelect field="status" options={["open", "in_progress", "resolved", "closed"]} />
          <FilterSelect field="priority" options={["Critical", "High", "Medium", "Low"]} />
          <FilterSelect field="category" options={["Bug", "Feature Request", "Complaint", "Praise"]} />
        </div>
        <Btn variant="secondary" small onClick={reload}>↻ Refresh</Btn>
      </div>

      {loading ? (
        <div style={{ display: "flex", justifyContent: "center", padding: 60 }}><Spinner size={32} /></div>
      ) : !tickets?.length ? (
        <Card><div style={{ textAlign: "center", color: COLORS.muted, padding: 40 }}>No tickets yet. Process some feedback to generate tickets.</div></Card>
      ) : (
        ["Critical", "High", "Medium", "Low"].map(priority => {
          const items = grouped[priority];
          if (!items?.length) return null;
          return (
            <div key={priority}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <Badge label={priority} color={PRIORITY_COLORS[priority]} />
                <span style={{ fontSize: 12, color: COLORS.muted }}>{items.length} ticket{items.length !== 1 ? "s" : ""}</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 12 }}>
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

function AnalyticsPage() {
  const [dupePage, setDupePage] = useState(1);
  const dupeLimit = 10;
  
  const { data: trends } = useData(() => api("/analytics/trends?days=14&group_by=category"), []);
  const { data: dupesData } = useData(() => api(`/analytics/duplicates?limit=${dupeLimit}&offset=${(dupePage - 1) * dupeLimit}`), [dupePage]);
  const { data: topIssues } = useData(() => api("/analytics/top-issues?limit=8"), []);
  
  const dupes = dupesData?.items || [];
  const dupeTotalPages = dupesData?.total ? Math.ceil(dupesData.total / dupeLimit) : 1;

  // Build per-category trend sparklines
  const categoryTrends = {};
  (trends || []).forEach(p => {
    const cat = p.category || "unknown";
    if (!categoryTrends[cat]) categoryTrends[cat] = [];
    categoryTrends[cat].push(p.count);
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Card>
        <SectionHeader title="Category Trends (14 days)" />
        {Object.keys(categoryTrends).length > 0 ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 16 }}>
            {Object.entries(categoryTrends).map(([cat, points]) => (
              <div key={cat} style={{ padding: 12, background: COLORS.surfaceAlt, borderRadius: 8 }}>
                <div style={{ fontSize: 12, color: CATEGORY_COLORS[cat] || COLORS.accent, fontWeight: 600, marginBottom: 8 }}>{cat}</div>
                <Sparkline points={points} color={CATEGORY_COLORS[cat] || COLORS.accent} />
                <div style={{ fontSize: 11, color: COLORS.muted, marginTop: 4 }}>Total: {points.reduce((a, b) => a + b, 0)}</div>
              </div>
            ))}
          </div>
        ) : <div style={{ color: COLORS.muted, fontSize: 13 }}>No trend data yet — process some feedback to see trends</div>}
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <SectionHeader title="Top Issue Categories" />
          {topIssues?.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {topIssues.map((issue, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: COLORS.surfaceAlt, borderRadius: 6 }}>
                  <span style={{ fontSize: 13, color: CATEGORY_COLORS[issue.category] || COLORS.text }}>{issue.category}</span>
                  <span style={{ fontFamily: "monospace", fontSize: 13, color: COLORS.text, fontWeight: 600 }}>{issue.count}</span>
                </div>
              ))}
            </div>
          ) : <div style={{ color: COLORS.muted, fontSize: 13 }}>No data yet</div>}
        </Card>

        <Card>
          <SectionHeader title="Duplicate Groups" />
          {dupes?.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {dupes.map(d => (
                <div key={d.id} style={{ padding: "12px 14px", background: COLORS.surfaceAlt, borderRadius: 8, fontSize: 12, border: `1px solid ${COLORS.border}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <Badge label={d.category} color={CATEGORY_COLORS[d.category] || COLORS.accent} small />
                    <span style={{ color: COLORS.warning, fontFamily: "monospace", fontWeight: 600 }}>{Math.round((d.similarity_score || 0) * 100)}% similar</span>
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "stretch" }}>
                    <div style={{ flex: 1, padding: "8px 10px", background: COLORS.bg, borderRadius: 6, borderLeft: `3px solid ${COLORS.accent}` }}>
                      <div style={{ fontSize: 10, color: COLORS.muted, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>This item</div>
                      <div style={{ color: COLORS.text, lineHeight: 1.4 }}>{d.text || "—"}</div>
                    </div>
                    {d.original_text && (
                      <>
                        <div style={{ display: "flex", alignItems: "center", color: COLORS.muted, fontSize: 16, flexShrink: 0 }}>≈</div>
                        <div style={{ flex: 1, padding: "8px 10px", background: COLORS.bg, borderRadius: 6, borderLeft: `3px solid ${COLORS.warning}` }}>
                          <div style={{ fontSize: 10, color: COLORS.muted, marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Similar to</div>
                          <div style={{ color: COLORS.textDim, lineHeight: 1.4 }}>{d.original_text}</div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : <div style={{ color: COLORS.muted, fontSize: 13 }}>No duplicates detected</div>}
          <Pagination page={dupePage} totalPages={dupeTotalPages} setPage={setDupePage} />
        </Card>
      </div>
    </div>
  );
}

// ── App Shell ─────────────────────────────────────────────────────────────────
const PAGES = [
  { id: "overview", label: "Overview", icon: "◈" },
  { id: "feedback", label: "Feedback", icon: "≡" },
  { id: "tickets", label: "Tickets", icon: "⊞" },
  { id: "analytics", label: "Analytics", icon: "∿" },
  { id: "monitoring", label: "Monitoring", icon: "◉" },
];

export default function App() {
  const [page, setPage] = useState("overview");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api("/health").then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  const pageComponents = {
    overview: <OverviewPage />,
    feedback: <FeedbackPage />,
    tickets: <TicketsPage />,
    analytics: <AnalyticsPage />,
    monitoring: <MonitoringPanel />,
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: COLORS.bg, color: COLORS.text, fontFamily: "'IBM Plex Sans', system-ui, sans-serif" }}>
      <ToastContainer />
      <style>{`
        * { box-sizing: border-box; }
        body { margin: 0; background: ${COLORS.bg}; }
        @keyframes spin { to { transform: rotate(360deg); } }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: ${COLORS.bg}; }
        ::-webkit-scrollbar-thumb { background: ${COLORS.border}; border-radius: 3px; }
        select { cursor: pointer; }
        select option { background: ${COLORS.surfaceAlt}; }
        input:focus, textarea:focus, select:focus { outline: 1px solid ${COLORS.accent}; }
      `}</style>

      {/* Sidebar */}
      <div style={{
        width: 220, flexShrink: 0, background: COLORS.surface,
        borderRight: `1px solid ${COLORS.border}`,
        display: "flex", flexDirection: "column",
        position: "sticky", top: 0, height: "100vh",
      }}>
        {/* Logo */}
        <div style={{ padding: "20px 20px 16px", borderBottom: `1px solid ${COLORS.border}` }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: COLORS.accent, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            ◈ FeedbackIQ
          </div>
          <div style={{ fontSize: 11, color: COLORS.muted, marginTop: 3 }}>Intelligence Platform</div>
        </div>

        {/* Nav */}
        <nav style={{ padding: "12px 10px", flex: 1 }}>
          {PAGES.map(p => (
            <div key={p.id}
              onClick={() => setPage(p.id)}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "9px 12px", borderRadius: 6, marginBottom: 2,
                cursor: "pointer", fontSize: 13, fontWeight: 500,
                background: page === p.id ? COLORS.accentGlow : "transparent",
                color: page === p.id ? COLORS.accent : COLORS.textDim,
                transition: "all 0.12s",
              }}
              onMouseEnter={e => page !== p.id && (e.currentTarget.style.background = COLORS.surfaceAlt)}
              onMouseLeave={e => page !== p.id && (e.currentTarget.style.background = "transparent")}
            >
              <span style={{ fontSize: 15 }}>{p.icon}</span>
              {p.label}
            </div>
          ))}
        </nav>

        {/* Health indicator */}
        <div style={{ padding: "12px 16px", borderTop: `1px solid ${COLORS.border}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: health?.status === "healthy" ? COLORS.success : COLORS.danger,
              boxShadow: `0 0 6px ${health?.status === "healthy" ? COLORS.success : COLORS.danger}`,
            }} />
            <span style={{ fontSize: 11, color: COLORS.muted }}>
              {health?.status === "healthy" ? "API Connected" : "API Offline"}
            </span>
          </div>
          <div style={{ fontSize: 10, color: COLORS.border, marginTop: 4 }}>v{health?.version || "—"}</div>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* Top bar */}
        <div style={{
          padding: "14px 28px", borderBottom: `1px solid ${COLORS.border}`,
          background: COLORS.surface, display: "flex", alignItems: "center", justifyContent: "space-between",
          position: "sticky", top: 0, zIndex: 50,
        }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: COLORS.text }}>
              {PAGES.find(p => p.id === page)?.label}
            </h1>
          </div>
          <div style={{ fontSize: 12, color: COLORS.muted }}>
            {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, padding: 24, overflowY: "auto" }}>
          {pageComponents[page]}
        </div>
      </div>
    </div>
  );
}
