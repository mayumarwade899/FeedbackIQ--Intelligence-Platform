import { useState, useEffect } from "react";
import { COLORS } from "../../utils/constants";
import { setAddToast, clearAddToast } from "../../utils/toast";

const TOAST_COLORS = { success: COLORS.success, error: COLORS.danger, info: COLORS.accent, warning: COLORS.warning };
const TOAST_ICONS = { success: "✓", error: "✕", info: "ℹ", warning: "⚠" };

export default function ToastContainer() {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    setAddToast((msg, type) => {
      const id = Date.now() + Math.random();
      setToasts(t => [...t, { id, msg, type }]);
      setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4000);
    });
    return () => clearAddToast();
  }, []);

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2.5 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.id}
          className="flex items-start gap-3 px-4 py-3 rounded-[10px] min-w-[280px] max-w-[420px] bg-surface animate-slideUp pointer-events-auto"
          style={{
            border: `1px solid ${TOAST_COLORS[t.type] || COLORS.border}44`,
            boxShadow: `0 4px 24px rgba(0,0,0,0.5), 0 0 0 1px ${TOAST_COLORS[t.type] || COLORS.border}22`,
          }}
        >
          <span
            className="text-base leading-[1.4] shrink-0"
            style={{ color: TOAST_COLORS[t.type] || COLORS.accent }}
          >
            {TOAST_ICONS[t.type] || "ℹ"}
          </span>
          <span className="text-[13px] text-text leading-normal">{t.msg}</span>
        </div>
      ))}
    </div>
  );
}
