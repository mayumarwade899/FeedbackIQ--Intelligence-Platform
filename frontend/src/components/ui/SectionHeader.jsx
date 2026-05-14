export default function SectionHeader({ title, action }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="m-0 text-base font-semibold text-text">{title}</h2>
      {action}
    </div>
  );
}
