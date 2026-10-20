import { useEffect, useState } from "react";
import { ErrorBox, Spinner, StatCard } from "../components/ui";
import { api } from "../lib/api";

const LABELS = { cgpa: "CGPA", sgpa: "SGPA", attendance_pct: "Attendance %", backlogs: "Backlogs", fee_paid: "Fee paid" };
const pct = (v) => `${(v * 100).toFixed(1)}%`;

export default function ModelInfo() {
  const [m, setM] = useState(undefined);
  const [error, setError] = useState(null);
  useEffect(() => {
    api("/api/model").then(setM).catch(setError);
  }, []);

  if (error) return <ErrorBox error={error} />;
  if (m === undefined) return <Spinner />;
  if (!m) return <ErrorBox error="No trained model. Run `python ml/train.py --source synthetic`." />;

  const [[tn, fp], [fn, tp]] = m.test.confusion_matrix;
  const maxImp = Math.max(...Object.values(m.feature_importances));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Model</h1>
        <p className="text-sm text-ink-500">
          Random Forest · <code className="text-xs">{m.model_version}</code> · trained on {m.n_rows.toLocaleString()} records ({pct(m.dropout_rate)} dropout)
        </p>
      </div>
      {m.source === "synthetic" && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          This model was trained on <strong>synthetic demo data</strong>. Its predictions are for testing the app, not for real decisions.
          Train on the Martins et al. dataset or your institution's records before use.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {["accuracy", "precision", "recall", "f1", "roc_auc"].map((k) => (
          <StatCard key={k} label={k === "roc_auc" ? "ROC-AUC" : k === "f1" ? "F1" : k} value={pct(m.test[k])} hint={`5-fold CV: ${pct(m.cv_5fold_mean[k])}`} />
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="mb-4 font-semibold">Feature importance</h2>
          <div className="space-y-3">
            {Object.entries(m.feature_importances).map(([f, v]) => (
              <div key={f}>
                <div className="mb-1 flex justify-between text-sm"><span>{LABELS[f] ?? f}</span><span className="text-ink-500">{v.toFixed(3)}</span></div>
                <div className="h-2 rounded-full bg-ink-100"><div className="h-2 rounded-full bg-brand-500" style={{ width: `${(v / maxImp) * 100}%` }} /></div>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5">
          <h2 className="mb-1 font-semibold">Confusion matrix (test set, threshold 0.5)</h2>
          <p className="mb-4 text-xs text-ink-500">Recall matters most here: a missed at-risk student gets no outreach.</p>
          <div className="grid max-w-sm grid-cols-[auto_1fr_1fr] gap-2 text-center text-sm">
            <div />
            <div className="text-xs font-semibold text-ink-500">Predicted stay</div>
            <div className="text-xs font-semibold text-ink-500">Predicted dropout</div>
            <div className="self-center text-right text-xs font-semibold text-ink-500">Actual stay</div>
            <div className="rounded-lg bg-emerald-50 p-4 text-xl font-bold">{tn}</div>
            <div className="rounded-lg bg-amber-50 p-4 text-xl font-bold">{fp}</div>
            <div className="self-center text-right text-xs font-semibold text-ink-500">Actual dropout</div>
            <div className="rounded-lg bg-rose-50 p-4 text-xl font-bold">{fn}</div>
            <div className="rounded-lg bg-emerald-50 p-4 text-xl font-bold">{tp}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
