import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, Spinner } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { SgpaTrend } from "./StudentDetail";

// Students see their indicators and gentle prompts, not a dropout probability.
export default function StudentHome() {
  const { user } = useAuth();
  const [s, setS] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!user.student_id) return setError("Your account isn't linked to a student profile yet. Please contact the department office.");
    api(`/api/students/${user.student_id}`).then(setS).catch(setError);
  }, [user]);

  if (error) return <ErrorBox error={error} />;
  if (!s) return <Spinner />;

  const r = s.latest_record;
  const concerns = (s.latest_prediction?.factors ?? []).filter((f) => f.severity !== "ok");
  const tiles = r
    ? [
        ["CGPA", r.cgpa.toFixed(2), r.cgpa < 6.5],
        ["SGPA", r.sgpa.toFixed(2), r.sgpa < 6.5],
        ["Attendance", `${r.attendance_pct}%`, r.attendance_pct < 75],
        ["Backlogs", r.backlogs, r.backlogs > 0],
        ["Fees", r.fee_paid ? "Paid" : "Pending", !r.fee_paid],
      ]
    : [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Hi {s.name.split(" ")[0]} 👋</h1>
        <p className="text-sm text-ink-500">{s.program} · Semester {s.current_semester}</p>
      </div>

      {r ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {tiles.map(([label, value, flag]) => (
            <div key={label} className={`card p-4 ${flag ? "border-amber-200 bg-amber-50/60" : ""}`}>
              <div className="label">{label}</div>
              <div className="text-xl font-bold">{value}</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-ink-500">No academic records yet.</p>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-4 font-semibold">SGPA by semester</h2>
          {s.records.length > 1 ? <SgpaTrend records={s.records} /> : <p className="text-sm text-ink-500">Your trend appears after two semesters.</p>}
        </div>
        <div className="card flex flex-col p-5">
          <h2 className="mb-2 font-semibold">{concerns.length ? "Where support could help" : "You're on track"}</h2>
          {concerns.length ? (
            <ul className="mb-4 list-disc space-y-1 pl-5 text-sm text-ink-700">
              {concerns.map((c) => <li key={c.feature}>{c.detail}</li>)}
            </ul>
          ) : (
            <p className="mb-4 text-sm text-ink-500">Keep it up. If anything changes, support is always available.</p>
          )}
          <Link to="/counselor" className="btn-primary mt-auto self-start">Talk to the counselor</Link>
        </div>
      </div>
    </div>
  );
}
