import { useState } from "react";

export default function Card({ children, style, onClick }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onClick={onClick}
      className="bg-surface border border-border rounded-lg p-5 transition-colors duration-150"
      style={{
        cursor: onClick ? "pointer" : "default",
        borderColor: onClick && hovered ? "#30363d" : undefined,
        ...style,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </div>
  );
}
