import { COLORS } from "../../utils/constants";

export default function DistributionBar({ data, colorMap }) {
  if (!data || !Object.keys(data).length) return <div className="text-muted text-[13px]">No data</div>;
  const total = Object.values(data).reduce((a, b) => a + b, 0);

  return (
    <div className="flex flex-col gap-2">
      {Object.entries(data).sort((a, b) => b[1] - a[1]).map(([key, val]) => {
        const pct = total > 0 ? Math.round((val / total) * 100) : 0;
        const color = (colorMap && colorMap[key]) || COLORS.accent;
        return (
          <div key={key}>
            <div className="flex justify-between mb-1 text-xs">
              <span className="text-textDim">{key}</span>
              <span className="text-text font-mono">
                {val} <span className="text-muted">({pct}%)</span>
              </span>
            </div>
            <div className="bg-border rounded-[3px] h-1.5 overflow-hidden">
              <div
                className="h-full rounded-[3px] transition-[width] duration-500 ease-in-out"
                style={{ width: `${pct}%`, background: color }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
