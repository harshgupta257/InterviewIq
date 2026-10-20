import { Navigate, Outlet, useLocation } from "react-router-dom";
import { FullPageLoader } from "@/components/states";
import { safeRedirectPath } from "@/lib/utils";
import { useAuth } from "./AuthProvider";

/** Client-side guard for UX only. The backend independently verifies every request. */
export function RequireAuth() {
  const { user, loading, sessionExpired } = useAuth();
  const location = useLocation();
  if (loading) return <FullPageLoader label="Checking your session" />;
  if (!user) {
    const params = new URLSearchParams({ next: location.pathname + location.search });
    if (sessionExpired) params.set("expired", "1");
    return <Navigate to={`/login?${params.toString()}`} replace />;
  }
  return <Outlet />;
}

export function RedirectIfAuthed() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullPageLoader label="Checking your session" />;
  if (user) {
    const next = new URLSearchParams(location.search).get("next");
    const safe = safeRedirectPath(next) ?? "/dashboard";
    return <Navigate to={safe} replace />;
  }
  return <Outlet />;
}
