import { useState, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { api } from "./api/client";
import Sidebar from "./layout/Sidebar";
import TopBar from "./layout/TopBar";
import ToastContainer from "./components/ui/ToastContainer";
import OverviewPage from "./pages/OverviewPage";
import FeedbackPage from "./pages/FeedbackPage";
import TicketsPage from "./pages/TicketsPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import MonitoringPanel from "./components/monitoring/MonitoringPanel";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api("/health").then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  return (
    <div className="flex min-h-screen bg-bg text-text font-sans custom-scrollbar">
      <ToastContainer />

      <style>{`
        select { cursor: pointer; }
        select option { background: #161b22; }
        input:focus, textarea:focus, select:focus { outline: 1px solid #58a6ff; }
      `}</style>

      <Sidebar health={health} />

      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <div className="flex-1 p-6 overflow-y-auto">
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/feedback" element={<FeedbackPage />} />
            <Route path="/tickets" element={<TicketsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/monitoring" element={<MonitoringPanel />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
