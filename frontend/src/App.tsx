import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { RedirectIfAuthed, RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./components/layout";
import { FullPageLoader } from "./components/states";
import { ForgotPasswordPage, LoginPage, ResetPasswordPage, SignupPage } from "./pages/Auth";
import Landing from "./pages/Landing";
import { ContactPage, PrivacyPage, TermsPage } from "./pages/Legal";
import NotFound from "./pages/NotFound";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const NewInterview = lazy(() => import("./pages/NewInterview"));
const InterviewWorkspace = lazy(() => import("./pages/InterviewWorkspace"));
const History = lazy(() => import("./pages/History"));
const SessionDetail = lazy(() => import("./pages/SessionDetail"));
const Settings = lazy(() => import("./pages/Settings"));
const JobFinder = lazy(() => import("./pages/JobFinder"));

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<FullPageLoader />}>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route element={<RedirectIfAuthed />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          </Route>
          {/* Not guarded: the recovery link signs the user in temporarily. */}
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route element={<RequireAuth />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/interviews/new" element={<NewInterview />} />
              <Route path="/interviews/:sessionId" element={<InterviewWorkspace />} />
              <Route path="/jobs" element={<JobFinder />} />
              <Route path="/jobs/:searchId" element={<JobFinder />} />
              <Route path="/history" element={<History />} />
              <Route path="/history/:sessionId" element={<SessionDetail />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
