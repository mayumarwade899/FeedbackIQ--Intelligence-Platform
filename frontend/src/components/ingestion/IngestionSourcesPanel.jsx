import { useState, useEffect, useRef } from "react";
import Card from "../ui/Card";
import SectionHeader from "../ui/SectionHeader";
import Btn from "../ui/Btn";
import { api } from "../../api/client";
import { showToast } from "../../utils/toast";

const SOURCES = [
  { id: "github", label: "GitHub Issues", icon: "⚙", desc: "Fetches open issues from configured repository" },
  { id: "reddit", label: "Reddit", icon: "💬", desc: "Monitors configured subreddits for relevant posts" },
  { id: "google_play", label: "Google Play Reviews", icon: "▶", desc: "Fetches newest reviews for com.spotify.music" },
  { id: "manual", label: "Manual / API", icon: "📥", desc: "Direct submission via dashboard or REST API" },
];

export default function IngestionSourcesPanel({ onTrigger }) {
  const [triggering, setTriggering] = useState(false);
  const [triggeringGP, setTriggeringGP] = useState(false);
  const pendingAtStartRef = useRef(0);

  // Poll the processed feedback list for real completion after Fetch Now.
  useEffect(() => {
    if (!triggeringGP) return;

    let staleCount = 0;

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

        staleCount++;
        if (staleCount >= 10) {
          setTriggeringGP(false);
          onTrigger?.();
        }
      } catch {
      }
    };

    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, [triggeringGP, onTrigger]);

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
      <div className="flex flex-col gap-2.5">
        {SOURCES.map(src => (
          <div key={src.id} className="flex items-center gap-3 px-3.5 py-2.5 bg-surfaceAlt rounded-md">
            <span className="text-xl">{src.icon}</span>
            <div className="flex-1">
              <div className="text-[13px] font-semibold text-text">{src.label}</div>
              <div className="text-[11px] text-muted mt-0.5">{src.desc}</div>
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
