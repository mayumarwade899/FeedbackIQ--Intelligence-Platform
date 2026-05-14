import { useLocation } from "react-router-dom";

const PAGE_TITLES = {
  "/": "Overview",
  "/feedback": "Feedback",
  "/tickets": "Tickets",
  "/analytics": "Analytics",
  "/monitoring": "Monitoring",
};

export default function TopBar() {
  const location = useLocation();
  const title = PAGE_TITLES[location.pathname] || "Overview";

  return (
    <div className="px-7 py-3.5 border-b border-border bg-surface flex items-center justify-between sticky top-0 z-50">
      <div>
        <h1 className="m-0 text-lg font-bold text-text">{title}</h1>
      </div>
      <div className="text-xs text-muted">
        {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
      </div>
    </div>
  );
}
