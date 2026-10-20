import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ErrorBox, FactorList, RiskBadge, Spinner, fmtDate } from "../components/ui";
import { api } from "../lib/api";

export function SgpaTrend({ records }) {
  if (records.length < 2) return null;
  return (
    <div className="flex h-28 items-end gap-2">
      {records.map((r) => (
        <div key={r.semester} className="flex flex-1 flex-col items-center gap-1">
          <span className="text-[11px] font-semibold text-ink-700">{r.sgpa.toFixed(1)}</span>
          <div
            className={`w-full max-w-10 rounded-t-md ${r.sgpa < 5.5 ? "bg-rose-400" : r.sgpa < 6.5 ? "bg-amber-300" : "bg-brand-500"}`}
            style={{ height: `${(r.sgpa / 10) * 80}px` }}
          />
          <span className="text-[11px] text-ink-500">S{r.semester}</span>
        </div>
      ))}
    </div>
  );
}

function RecordForm({ student, onSaved }) {
  const next = (student.records.at(-1)?.semester ?? 0) + 1;
  const [r, setR] = useState({ semester: next, sgpa: "", cgpa: "", attendance_pct: "", backlogs: student.records.at(-1)?.backlogs ?? 0, fee_paid: true });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setR((x) => ({ ...x, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = { ...r, semester: +r.semester, sgpa: +r.sgpa, cgpa: +r.cgpa, attendance_pct: +r.attendance_pct, backlogs: +r.backlogs };
      onSaved(await api(`/api/students/${student.id}/records`, { method: "PUT", body }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const num = (label, k, props) => (
    <div>
      <label className="label">{label}</label>
      <input className="input" type="number" required value={r[k]} onChange={(e) => set(k, e.target.value)} {...props} />
    </div>
  );

  return (
    <form onSubmit={submit} className="space-y-3">
      <ErrorBox error={error} />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {num("Semester", "semester", { min: 1, max: 12 })}
        {num("SGPA", "sgpa", { step: 0.01, min: 0, max: 10 })}
        {num("CGPA", "cgpa", { step: 0.01, min: 0, max: 10 })}
        {num("Attendance %", "attendance_pct", { step: 0.1, min: 0, max: 100 })}
        {num("Backlogs", "backlogs", { min: 0 })}
        <div>
          <label className="label">Fees</label>
          <select className="input" value={String(r.fee_paid)} onChange={(e) => set("fee_paid", e.target.value === "true")}>
            <option value="true">Paid</option>
            <option value="false">Pending</option>
          </select>
        </div>
      </div>
      <p className="text-xs text-ink-500">Saving an existing semester number updates it. The student is re-scored automatically.</p>
      <button className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Save record & re-score"}</button>
    </form>
  );
}

function Notes({ student, onChange }) {
  const [text, setText] = useState("");
  const [error, setError] = useState(null);

  const add = async (e) => {
    e.preventDefault();
    try {
      await api(`/api/students/${student.id}/notes`, { method: "POST", body: { note: text } });
      setText("");
      onChange();
    } catch (err) {
      setError(err);
    }
  };
  const setStatus = async (n, status) => {
    await api(`/api/students/${student.id}/notes/${n.id}`, { method: "PATCH", body: { note: n.note, status } }).catch(setError);
    onChange();
  };

  return (
    <div className="space-y-4">
      <ErrorBox error={error} />
      <form onSubmit={add} className="space-y-2">
        <textarea className="input min-h-20" placeholder="Log an outreach, meeting or referral…" value={text} onChange={(e) => setText(e.target.value)} required />
        <button className="btn-primary">Add note</button>
      </form>
      <ul className="space-y-3">
        {student.notes.map((n) => (
          <li key={n.id} className={`rounded-xl border p-3 text-sm ${n.note.startsWith("Safety alert") && n.status !== "resolved" ? "border-rose-300 bg-rose-50" : "border-ink-100"}`}>
            <p>{n.note}</p>
            <div className="mt-2 flex items-center justify-between text-xs text-ink-500">
              <span>{n.author_name ?? "StuSupport (automatic)"} · {fmtDate(n.created_at)}</span>
              <select className="rounded-lg border border-ink-200 bg-white px-2 py-1" value={n.status} onChange={(e) => setStatus(n, e.target.value)}>
                <option value="open">Open</option>
                <option value="in_progress">In progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          </li>
        ))}
        {student.notes.length === 0 && <li className="text-sm text-ink-500">No interventions logged yet.</li>}
      </ul>
    </div>
  );
}

export default function StudentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [s, setS] = useState(null);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const load = () => api(`/api/students/${id}`).then(setS).catch(setError);
  useEffect(() => {
    load();
  }, [id]);

  const remove = async () => {
    if (!confirm(`Delete ${s.name} and all their records? This cannot be undone.`)) return;
    await api(`/api/students/${id}`, { method: "DELETE" }).catch(setError);
    navigate("/students");
  };

  if (error) return <ErrorBox error={error} />;
  if (!s) return <Spinner />;
  const p = s.latest_prediction;
  const history = s.predictions.slice(-6);

  return (
    <div className="space-y-6">
      <div>
        <Link to="/students" className="text-sm text-ink-500 hover:text-ink-900">← Students</Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">{s.name}</h1>
          <RiskBadge level={p?.risk_level} probability={p?.probability} />
        </div>
        <p className="text-sm text-ink-500">
          {s.roll_no} · {s.program ?? "—"} · {s.department ?? "—"} · Semester {s.current_semester}
          {s.email && <> · {s.email}</>}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <div className="card p-5">
            <h2 className="mb-1 font-semibold">Why this score</h2>
            <p className="mb-4 text-xs text-ink-500">
              Ordered by how much the model relies on each indicator. {p && <>Scored {fmtDate(p.created_at)} with {p.model_version}.</>}
            </p>
            {p ? <FactorList factors={p.factors} /> : <p className="text-sm text-ink-500">Add a semester record to score this student.</p>}
            {history.length > 1 && (
              <div className="mt-4 text-xs text-ink-500">
                Score history: {history.map((h) => `${Math.round(h.probability * 100)}%`).join(" → ")}
              </div>
            )}
          </div>

          <div className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">Academic record</h2>
              <button className="btn-ghost py-1.5" onClick={() => setShowForm((v) => !v)}>{showForm ? "Close" : "Add / update semester"}</button>
            </div>
            {showForm && (
              <div className="mb-5 rounded-xl bg-ink-50 p-4">
                <RecordForm student={s} onSaved={(d) => { setS(d); setShowForm(false); }} />
              </div>
            )}
            <SgpaTrend records={s.records} />
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-ink-500">
                  <tr><th className="pb-2">Sem</th><th>SGPA</th><th>CGPA</th><th>Attendance</th><th>Backlogs</th><th>Fees</th></tr>
                </thead>
                <tbody className="divide-y divide-ink-100">
                  {s.records.map((r) => (
                    <tr key={r.id}>
                      <td className="py-2">{r.semester}</td>
                      <td>{r.sgpa.toFixed(2)}</td>
                      <td>{r.cgpa.toFixed(2)}</td>
                      <td className={r.attendance_pct < 75 ? "font-semibold text-rose-600" : ""}>{r.attendance_pct}%</td>
                      <td>{r.backlogs}</td>
                      <td>{r.fee_paid ? "Paid" : <span className="font-semibold text-rose-600">Pending</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card p-5">
            <h2 className="mb-4 font-semibold">Interventions</h2>
            <Notes student={s} onChange={load} />
          </div>
          <button className="text-sm text-rose-600 hover:underline" onClick={remove}>Delete student</button>
        </div>
      </div>
    </div>
  );
}
