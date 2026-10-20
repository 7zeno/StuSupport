import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./index.css";
import Layout from "./components/Layout";
import { AuthProvider, RequireAuth, homeFor, useAuth } from "./lib/auth";
import Counselor from "./pages/Counselor";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import ModelInfo from "./pages/ModelInfo";
import StudentDetail from "./pages/StudentDetail";
import StudentHome from "./pages/StudentHome";
import Students from "./pages/Students";

const STAFF = ["faculty", "admin"];

function Home() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Navigate to={user ? homeFor(user) : "/login"} replace />;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            element={
              <RequireAuth>
                <Layout />
              </RequireAuth>
            }
          >
            <Route path="/dashboard" element={<RequireAuth roles={STAFF}><Dashboard /></RequireAuth>} />
            <Route path="/students" element={<RequireAuth roles={STAFF}><Students /></RequireAuth>} />
            <Route path="/students/:id" element={<RequireAuth roles={STAFF}><StudentDetail /></RequireAuth>} />
            <Route path="/model" element={<RequireAuth roles={STAFF}><ModelInfo /></RequireAuth>} />
            <Route path="/me" element={<RequireAuth roles={["student"]}><StudentHome /></RequireAuth>} />
            <Route path="/counselor" element={<RequireAuth roles={["student"]}><Counselor /></RequireAuth>} />
          </Route>
          <Route path="*" element={<Home />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
