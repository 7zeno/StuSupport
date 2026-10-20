import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { ErrorBox } from "../components/ui";
import { homeFor, useAuth } from "../lib/auth";

const DEMO = [
  ["Faculty", "faculty@stusupport.dev"],
  ["Student (high risk)", "student.high@stusupport.dev"],
  ["Student (low risk)", "student.low@stusupport.dev"],
];

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homeFor(user)} replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await login(email, password);
      navigate(location.state?.from?.pathname ?? homeFor(u), { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-brand-700 p-12 text-white lg:flex">
        <div className="text-lg font-bold">StuSupport</div>
        <div>
          <h1 className="text-4xl font-bold leading-tight">Notice early.<br />Support sooner.</h1>
          <p className="mt-4 max-w-md text-brand-100">
            Dropout risk prediction for faculty, and a counseling assistant grounded in your institution's own policies for students.
          </p>
        </div>
        <p className="text-xs text-brand-100/70">For academic and educational use.</p>
      </div>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4">
          <div>
            <h2 className="text-2xl font-bold">Sign in</h2>
            <p className="text-sm text-ink-500">Use your institutional account.</p>
          </div>
          <ErrorBox error={error} />
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input id="email" type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </div>
          <div>
            <label className="label" htmlFor="password">Password</label>
            <input id="password" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>

          {import.meta.env.DEV && (
            <div className="rounded-xl border border-dashed border-ink-200 p-3 text-xs text-ink-500">
              <div className="mb-2 font-semibold">Demo accounts (password: password123)</div>
              <div className="flex flex-wrap gap-2">
                {DEMO.map(([label, e]) => (
                  <button type="button" key={e} className="rounded-lg bg-ink-100 px-2 py-1 hover:bg-ink-200"
                    onClick={() => { setEmail(e); setPassword("password123"); }}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
