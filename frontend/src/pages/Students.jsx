import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ErrorBox, RiskBadge, Spinner } from "../components/ui";
import { api } from "../lib/api";

const EMPTY = {
  roll_no: "", name: "", email: "", department: "", program: "", current_semester: 1,
  record: { semester: 1, sgpa: "", cgpa: "", attendance_pct: "", backlogs: 0, fee_paid: true },
};

function AddStudent({ onClose }) {
  const navigate = useNavigate();
  const [f, setF] = useState(EMPTY);
  const [error, setError] = useState(null);
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const setR = (k, v) => setF((x) => ({ ...x, record: { ...x.record, [k]: v } }));
  const hasRecord = f.record.sgpa !== "" && f.record.cgpa !== "" && f.record.attendance_pct !== "";

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const { record, ...rest } = f;
      const body = {
        ...rest,
        email: rest.email || null,
        current_semester: Number(rest.current_semester),
        initial_record: hasRecord
          ? { ...record, semester: Number(record.semester), sgpa: Number(record.sgpa), cgpa: Number(record.cgpa), attendance_pct: Number(record.attendance_pct), backlogs: Number(record.backlogs) }
          : null,
      };
      const s = await api("/api/students", { method: "POST", body });
      navigate(`/students/${s.id}`);
    } catch (err) {
      setError(err);
    }
  };

  const field = (label, k, props = {}) => (
    <div>
      <label className="label">{label}</label>
      <input className="input" value={f[k]} onChange={(e) => set(k, e.target.value)} {...props} />
    </div>
  );
  const rfield = (label, k, props = {}) => (
    <div>
      <label className="label">{label}</label>
      <input className="input" type="number" value={f.record[k]} onChange={(e) => setR(k, e.target.value)} {...props} />
    </div>
  );

  return (
    <form onSubmit={submit} className="card space-y-4 p-5">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">Add student</h2>
        <button type="button" className="text-sm text-ink-500 hover:text-ink-900" onClick={onClose}>Cancel</button>
      </div>
      <ErrorBox error={error} />
      <div className="grid gap-3 sm:grid-cols-3">
        {field("Roll no.", "roll_no", { required: true })}
        {field("Name", "name", { required: true })}
        {field("Email", "email", { type: "email" })}
        {field("Department", "department")}
        {field("Program", "program")}
        {field("Current semester", "current_semester", { type: "number", min: 1, max: 12 })}
      </div>
      <div className="border-t border-ink-100 pt-4">
        <div className="mb-3 text-sm font-semibold">Latest semester record <span className="font-normal text-ink-500">(optional — needed for a risk score)</span></div>
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {rfield("Semester", "semester", { min: 1, max: 12 })}
          {rfield("SGPA", "sgpa", { step: 0.01, min: 0, max: 10 })}
          {rfield("CGPA", "cgpa", { step: 0.01, min: 0, max: 10 })}
          {rfield("Attendance %", "attendance_pct", { step: 0.1, min: 0, max: 100 })}
          {rfield("Backlogs", "backlogs", { min: 0 })}
          <div>
            <label className="label">Fees</label>
            <select className="input" value={String(f.record.fee_paid)} onChange={(e) => setR("fee_paid", e.target.value === "true")}>
              <option value="true">Paid</option>
              <option value="false">Pending</option>
            </select>
          </div>
        </div>
      </div>
      <button className="btn-primary">Save student</button>
    </form>
  );
}

export default function Students() {
  const [params, setParams] = useSearchParams();
  const [students, setStudents] = useState(null);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const q = params.get("q") ?? "";
  const risk = params.get("risk_level") ?? "";

  useEffect(() => {
    const t = setTimeout(() => {
      api("/api/students", { params: { q, risk_level: risk } }).then(setStudents).catch(setError);
    }, 200);
    return () => clearTimeout(t);
  }, [q, risk]);

  const update = (k, v) => {
    const next = new URLSearchParams(params);
    v ? next.set(k, v) : next.delete(k);
    setParams(next, { replace: true });
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-bold">Students</h1>
        {!adding && <button className="btn-primary" onClick={() => setAdding(true)}>Add student</button>}
      </div>
      {adding && <AddStudent onClose={() => setAdding(false)} />}

      <div className="flex flex-wrap gap-3">
        <input className="input max-w-xs" placeholder="Search name or roll no." value={q} onChange={(e) => update("q", e.target.value)} />
        <select className="input w-auto" value={risk} onChange={(e) => update("risk_level", e.target.value)}>
          <option value="">All risk levels</option>
          <option>High</option>
          <option>Medium</option>
          <option>Low</option>
        </select>
      </div>

      <ErrorBox error={error} />
      {!students ? <Spinner /> : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-ink-100 text-left text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-4 py-3">Student</th><th>Department</th><th>Sem</th><th>CGPA</th><th>SGPA</th>
                <th>Attendance</th><th>Backlogs</th><th>Fees</th><th className="pr-4">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {students.map((s) => {
                const r = s.latest_record;
                return (
                  <tr key={s.id} className="hover:bg-ink-50">
                    <td className="px-4 py-2.5">
                      <Link to={`/students/${s.id}`} className="font-medium hover:text-brand-700">{s.name}</Link>
                      <div className="text-xs text-ink-500">{s.roll_no}</div>
                    </td>
                    <td>{s.department}</td>
                    <td>{s.current_semester}</td>
                    <td>{r?.cgpa.toFixed(2) ?? "—"}</td>
                    <td>{r?.sgpa.toFixed(2) ?? "—"}</td>
                    <td className={r && r.attendance_pct < 75 ? "font-semibold text-rose-600" : ""}>{r ? `${r.attendance_pct}%` : "—"}</td>
                    <td>{r?.backlogs ?? "—"}</td>
                    <td>{r ? (r.fee_paid ? "Paid" : <span className="font-semibold text-rose-600">Pending</span>) : "—"}</td>
                    <td className="pr-4"><RiskBadge level={s.latest_prediction?.risk_level} probability={s.latest_prediction?.probability} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {students.length === 0 && <p className="py-10 text-center text-sm text-ink-500">No students match.</p>}
        </div>
      )}
    </div>
  );
}
