import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorBox, RISK_STYLES, RiskBadge, Spinner, StatCard } from "../components/ui";
import { api } from "../lib/api";

const LEVELS = ["High", "Medium", "Low"];

function RiskDistribution({ byLevel, total }) {
  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full bg-ink-100">
        {LEVELS.map((l) => (
          <div key={l} className={RISK_STYLES[l].bar} style={{ width: `${total ? (byLevel[l] / total) * 100 : 0}%` }} />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-sm">
        {LEVELS.map((l) => (
          <span key={l} className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${RISK_STYLES[l].dot}`} />
            {l} <span className="font-semibold">{byLevel[l]}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [atRisk, setAtRisk] = useState([]);
  const [error, setError] = useState(null);
  const [rescoring, setRescoring] = useState(false);

  const load = () =>
    Promise.all([api("/api/dashboard/summary"), api("/api/students", { params: { risk_level: "High" } })])
      .then(([s, high]) => {
        setSummary(s);
        setAtRisk(high.sort((a, b) => b.latest_prediction.probability - a.latest_prediction.probability));
      })
      .catch(setError);

  useEffect(() => {
    load();
  }, []);

  const rescore = async () => {
    setRescoring(true);
    try {
      await api("/api/predictions/run-all", { method: "POST" });
      await load();
    } catch (e) {
      setError(e);
    } finally {
      setRescoring(false);
    }
  };

  if (error) return <ErrorBox error={error} />;
  if (!summary) return <Spinner />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-ink-500">
            {summary.assessed} of {summary.total_students} students assessed
            {summary.model && <> · model <code className="text-xs">{summary.model.model_version}</code></>}
          </p>
        </div>
        <button className="btn-ghost" onClick={rescore} disabled={rescoring}>
          {rescoring ? "Re-scoring…" : "Re-score all students"}
        </button>
      </div>

      {summary.safety_alerts?.length > 0 && (
        <div className="rounded-2xl border-2 border-rose-300 bg-rose-50 p-4">
          <div className="font-semibold text-rose-800">
            Safety alerts — follow up today ({summary.safety_alerts.length})
          </div>
          <p className="mb-3 text-sm text-rose-800/80">
            These students wrote something to the counseling assistant suggesting possible risk of self-harm. They were shown
            crisis contacts. Mark the alert resolved on the student's page once someone has reached them.
          </p>
          <ul className="flex flex-wrap gap-2">
            {summary.safety_alerts.map((a) => (
              <li key={`${a.student_id}-${a.created_at}`}>
                <Link to={`/students/${a.student_id}`} className="inline-block rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-rose-800 ring-1 ring-rose-200 hover:bg-rose-100">
                  {a.name} · {a.roll_no} · {new Date(a.created_at + (a.created_at.endsWith("Z") || a.created_at.includes("+") ? "" : "Z")).toLocaleString()}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!summary.model && (
        <ErrorBox error="No trained model found. Run `python ml/train.py --source synthetic` and restart the API." />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="High risk" value={summary.by_level.High} accent="text-rose-600" hint="Need outreach this week" />
        <StatCard label="Avg attendance" value={summary.avg_attendance != null ? `${summary.avg_attendance}%` : null} hint="Latest semester" />
        <StatCard label="Fee pending" value={summary.fee_defaulters} hint="Students with dues" />
        <StatCard label="Open interventions" value={summary.open_interventions} hint="Not yet resolved" />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Highest-risk students</h2>
            <Link to="/students?risk_level=High" className="text-sm font-medium text-brand-600 hover:underline">View all</Link>
          </div>
          {atRisk.length === 0 ? (
            <p className="py-6 text-center text-sm text-ink-500">No high-risk students right now.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase tracking-wide text-ink-500">
                  <tr><th className="pb-2">Student</th><th className="pb-2">Attendance</th><th className="pb-2">CGPA</th><th className="pb-2">Backlogs</th><th className="pb-2">Risk</th></tr>
                </thead>
                <tbody className="divide-y divide-ink-100">
                  {atRisk.slice(0, 8).map((s) => (
                    <tr key={s.id} className="hover:bg-ink-50">
                      <td className="py-2.5">
                        <Link to={`/students/${s.id}`} className="font-medium hover:text-brand-700">{s.name}</Link>
                        <div className="text-xs text-ink-500">{s.roll_no} · {s.department}</div>
                      </td>
                      <td>{s.latest_record?.attendance_pct}%</td>
                      <td>{s.latest_record?.cgpa.toFixed(2)}</td>
                      <td>{s.latest_record?.backlogs}</td>
                      <td><RiskBadge level={s.latest_prediction.risk_level} probability={s.latest_prediction.probability} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="card p-5">
            <h2 className="mb-4 font-semibold">Risk distribution</h2>
            <RiskDistribution byLevel={summary.by_level} total={summary.assessed} />
          </div>
          <div className="card p-5">
            <h2 className="mb-4 font-semibold">By department</h2>
            <div className="space-y-3">
              {summary.by_department.map((d) => (
                <div key={d.department}>
                  <div className="mb-1 flex justify-between text-sm">
                    <span>{d.department}</span>
                    <span className="text-ink-500">{d.High} high / {d.total}</span>
                  </div>
                  <div className="flex h-2 overflow-hidden rounded-full bg-ink-100">
                    {LEVELS.map((l) => (
                      <div key={l} className={RISK_STYLES[l].bar} style={{ width: `${(d[l] / d.total) * 100}%` }} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
