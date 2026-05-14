import { COLORS } from "../../utils/constants";

export default function Sparkline({ points, color = COLORS.accent, height = 40 }) {
  if (!points || points.length < 2) return null;
  const max = Math.max(...points, 1);
  const w = 160, h = height;
  const pts = points.map((v, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - (v / max) * (h - 4) - 2;
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg width={w} height={h} className="block">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <polyline points={`0,${h} ${pts} ${w},${h}`} fill={color + "22"} stroke="none" />
    </svg>
  );
}
