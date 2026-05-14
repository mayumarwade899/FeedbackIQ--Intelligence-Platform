import { NavLink } from "react-router-dom";
import { COLORS } from "../utils/constants";

const NAV_ITEMS = [
  { path: "/", label: "Overview", icon: "◈" },
  { path: "/feedback", label: "Feedback", icon: "≡" },
  { path: "/tickets", label: "Tickets", icon: "⊞" },
  { path: "/analytics", label: "Analytics", icon: "∿" },
  { path: "/monitoring", label: "Monitoring", icon: "◉" },
];

export default function Sidebar({ health }) {
  return (
    <div className="w-[220px] shrink-0 bg-surface border-r border-border flex flex-col sticky top-0 h-screen">
      <div className="px-5 pt-5 pb-4 border-b border-border">
        <div className="text-[13px] font-bold text-accent tracking-wider uppercase">
          ◈ FeedbackIQ
        </div>
        <div className="text-[11px] text-muted mt-[3px]">Intelligence Platform</div>
      </div>

      <nav className="px-2.5 py-3 flex-1">
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-[9px] rounded-md mb-0.5 text-[13px] font-medium no-underline transition-all duration-[120ms] ${isActive
                ? "bg-accentGlow text-accent"
                : "text-textDim hover:bg-surfaceAlt"
              }`
            }
          >
            <span className="text-[15px]">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-border">
        <div className="flex items-center gap-2">
          <div
            className="w-[7px] h-[7px] rounded-full"
            style={{
              background: health?.status === "healthy" ? COLORS.success : COLORS.danger,
              boxShadow: `0 0 6px ${health?.status === "healthy" ? COLORS.success : COLORS.danger}`,
            }}
          />
          <span className="text-[11px] text-muted">
            {health?.status === "healthy" ? "API Connected" : "API Offline"}
          </span>
        </div>
        <div className="text-[10px] text-border mt-1">v{health?.version || "—"}</div>
      </div>
    </div>
  );
}
