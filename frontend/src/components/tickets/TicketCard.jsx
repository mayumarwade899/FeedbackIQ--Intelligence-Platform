import { useState } from "react";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import Btn from "../ui/Btn";
import { COLORS, PRIORITY_COLORS, CATEGORY_COLORS } from "../../utils/constants";
import { api } from "../../api/client";
import { showToast } from "../../utils/toast";

const STATUSES = ["open", "in_progress", "resolved", "closed"];

const STATUS_COLORS = {
  open: COLORS.danger,
  in_progress: COLORS.warning,
  resolved: COLORS.success,
  closed: COLORS.muted,
};

export default function TicketCard({ ticket, onUpdate }) {
  const [editing, setEditing] = useState(false);
  const [status, setStatus] = useState(ticket.status);
  const [saving, setSaving] = useState(false);

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
      <div className="flex justify-between items-start mb-2.5">
        <div className="text-[11px] font-mono text-muted">{ticket.ticket_number}</div>
        <div className="flex gap-1.5">
          <Badge label={ticket.priority} color={priColor} small />
          <Badge label={ticket.category} color={catColor} small />
        </div>
      </div>

      <div className="text-sm font-semibold text-text mb-2 leading-snug">
        {ticket.title}
      </div>

      {ticket.impact_summary && (
        <div className="text-xs text-textDim mb-2.5 leading-normal line-clamp-2">
          {ticket.impact_summary}
        </div>
      )}

      <div className="flex items-center justify-between mt-2">
        {editing ? (
          <div className="flex gap-1.5 items-center">
            <select
              value={status}
              onChange={e => setStatus(e.target.value)}
              className="bg-surfaceAlt border border-border rounded text-text px-2 py-1 text-xs"
            >
              {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <Btn small onClick={save} loading={saving}>Save</Btn>
            <Btn small variant="secondary" onClick={() => setEditing(false)}>Cancel</Btn>
          </div>
        ) : (
          <Badge label={ticket.status} color={STATUS_COLORS[ticket.status] || COLORS.muted} small />
        )}
        {!editing && <Btn small variant="secondary" onClick={() => setEditing(true)}>Edit</Btn>}
      </div>

      {ticket.labels?.length > 0 && (
        <div className="mt-2.5 flex gap-1 flex-wrap">
          {ticket.labels.map(l => (
            <span key={l} className="text-[10px] bg-border text-muted px-1.5 py-0.5 rounded-[3px]">{l}</span>
          ))}
        </div>
      )}
    </Card>
  );
}
