export default function FilterSelect({ field, value, options, onChange }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(field, e.target.value)}
      className="bg-surfaceAlt border border-border rounded-md text-text px-2.5 py-1.5 text-xs cursor-pointer"
    >
      <option value="">All {field}s</option>
      {options.map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );
}
