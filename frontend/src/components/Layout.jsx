import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const STAFF_NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/students", label: "Students" },
  { to: "/model", label: "Model" },
];
const STUDENT_NAV = [
  { to: "/me", label: "My progress" },
  { to: "/counselor", label: "Counselor" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const nav = user.role === "student" ? STUDENT_NAV : STAFF_NAV;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-ink-100 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-sm font-bold text-white">S</div>
            <span className="font-bold tracking-tight">StuSupport</span>
          </div>
          <nav className="flex gap-1">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-1.5 text-sm font-medium ${isActive ? "bg-brand-50 text-brand-700" : "text-ink-500 hover:text-ink-900"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="hidden text-ink-500 sm:inline">
              {user.full_name} · <span className="capitalize">{user.role}</span>
            </span>
            <button
              className="btn-ghost py-1.5"
              onClick={() => {
                logout();
                navigate("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
