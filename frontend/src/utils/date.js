export function fmtDate(ts, opts = {}) {
  if (!ts) return "—";
  const utc = ts.endsWith("Z") ? ts : ts + "Z";
  return new Date(utc).toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
    ...opts,
  });
}

export function fmtDateOnly(ts) {
  if (!ts) return "—";
  const utc = ts.endsWith("Z") ? ts : ts + "Z";
  return new Date(utc).toLocaleDateString("en-IN");
}
