export default function Badge({ label, color, small }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded font-semibold uppercase tracking-wide ${
        small ? "px-1.5 py-0.5 text-[10px]" : "px-2.5 py-[3px] text-[11px]"
      }`}
      style={{
        background: color + "22",
        color: color,
        border: `1px solid ${color}44`,
      }}
    >
      {label}
    </span>
  );
}
