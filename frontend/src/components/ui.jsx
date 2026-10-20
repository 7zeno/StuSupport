export const RISK_STYLES = {
  High: { badge: "bg-rose-50 text-rose-700 ring-rose-200", bar: "bg-rose-500", dot: "bg-rose-500" },
  Medium: { badge: "bg-amber-50 text-amber-800 ring-amber-200", bar: "bg-amber-400", dot: "bg-amber-400" },
  Low: { badge: "bg-emerald-50 text-emerald-700 ring-emerald-200", bar: "bg-emerald-500", dot: "bg-emerald-500" },
};

export function RiskBadge({ level, probability }) {
  if (!level) return <span className="text-xs text-ink-400">Not assessed</span>;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${RISK_STYLES[level].badge}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${RISK_STYLES[level].dot}`} />
      {level}
      {probability !== undefined && <span className="font-medium opacity-70">{Math.round(probability * 100)}%</span>}
    </span>
  );
}

export function StatCard({ label, value, hint, accent }) {
  return (
    <div className="card p-5">
      <div className="label">{label}</div>
      <div className={`mt-1 text-3xl font-bold ${accent ?? ""}`}>{value ?? "—"}</div>
      {hint && <div className="mt-1 text-xs text-ink-500">{hint}</div>}
    </div>
  );
}

const SEVERITY = {
  concern: "border-rose-200 bg-rose-50 text-rose-800",
  watch: "border-amber-200 bg-amber-50 text-amber-900",
  ok: "border-ink-100 bg-ink-50 text-ink-700",
};

export function FactorList({ factors }) {
  if (!factors?.length) return null;
  return (
    <ul className="space-y-2">
      {factors.map((f) => (
        <li key={f.feature} className={`rounded-xl border px-3 py-2 text-sm ${SEVERITY[f.severity]}`}>
          <span className="font-semibold">{f.label}:</span> {f.detail}
        </li>
      ))}
    </ul>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">{String(error.message ?? error)}</div>;
}

export function Spinner({ label = "Loading…" }) {
  return <div className="py-12 text-center text-sm text-ink-500">{label}</div>;
}

export const fmtDate = (d) => new Date(d).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
