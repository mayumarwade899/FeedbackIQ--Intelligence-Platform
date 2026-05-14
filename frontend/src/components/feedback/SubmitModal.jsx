import { useState } from "react";
import Btn from "../ui/Btn";
import { api } from "../../api/client";
import { showToast } from "../../utils/toast";

export default function SubmitModal({ onClose, onSuccess }) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [loading, setLoading] = useState(false);

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
    <div
      className="fixed inset-0 z-[200] bg-black/80 flex items-center justify-center"
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="w-[500px] bg-surface rounded-xl border border-border p-7"
      >
        <div className="flex justify-between items-center mb-5">
          <h3 className="m-0 text-text">Submit Feedback</h3>
          <button onClick={onClose} className="bg-transparent border-none text-muted text-xl cursor-pointer">✕</button>
        </div>

        {[
          ["Title (optional)", title, setTitle],
          ["Author (optional)", author, setAuthor],
        ].map(([label, val, setter]) => (
          <div key={label} className="mb-3.5">
            <label className="text-xs text-muted block mb-1">{label}</label>
            <input
              value={val}
              onChange={e => setter(e.target.value)}
              className="w-full bg-surfaceAlt border border-border rounded-md px-3 py-2 text-text text-[13px]"
            />
          </div>
        ))}

        <div className="mb-5">
          <label className="text-xs text-muted block mb-1">
            Feedback <span className="text-danger">*</span>
          </label>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            rows={5}
            placeholder="Describe the issue, feature request, or feedback..."
            className="w-full bg-surfaceAlt border border-border rounded-md px-3 py-2 text-text text-[13px] resize-y"
          />
        </div>

        <div className="flex justify-end gap-2.5">
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn onClick={submit} loading={loading} disabled={!text.trim()}>Submit & Process</Btn>
        </div>
      </div>
    </div>
  );
}
