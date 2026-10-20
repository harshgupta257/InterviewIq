import type { Session } from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, configureApiAuth } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { storage } from "@/lib/utils";

const DEMO_KEY = "iq_demo_session";

interface DemoSession {
  token: string;
  expiresAt: string;
  userId: string;
}

export interface AuthUser {
  id: string;
  email: string | null;
  isDemo: boolean;
  displayName: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  /** Set when the session ended because the token expired or was rejected. */
  sessionExpired: boolean;
  signIn(email: string, password: string): Promise<void>;
  signUp(email: string, password: string, displayName?: string): Promise<{ needsConfirmation: boolean }>;
  requestPasswordReset(email: string): Promise<void>;
  updatePassword(password: string): Promise<void>;
  startDemo(): Promise<void>;
  /** `local`: end only this browser's session (used after account deletion, when the server-side session is already gone; supabase-js ignores the resulting 403). */
  signOut(opts?: { local?: boolean }): Promise<void>;
  clearExpired(): void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readDemo(): DemoSession | null {
  const raw = storage.get(DEMO_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DemoSession;
    if (new Date(parsed.expiresAt).getTime() > Date.now() + 30_000) return parsed;
  } catch {
    /* corrupted value */
  }
  storage.remove(DEMO_KEY);
  return null;
}

function userFromSupabase(session: Session | null): AuthUser | null {
  if (!session) return null;
  const meta = session.user.user_metadata as { display_name?: string } | undefined;
  return { id: session.user.id, email: session.user.email ?? null, isDemo: false, displayName: meta?.display_name ?? null };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);
  const userRef = useRef<AuthUser | null>(null);
  userRef.current = user;

  const resetClientState = useCallback(() => {
    queryClient.clear();
    try {
      // Remove saved answer drafts so the next person on this browser cannot see them.
      Object.keys(window.localStorage)
        .filter((k) => k.startsWith("iq_draft_"))
        .forEach((k) => storage.remove(k));
    } catch {
      /* storage unavailable */
    }
  }, [queryClient]);

  const handleUnauthorized = useCallback(() => {
    if (!userRef.current) return;
    setSessionExpired(true);
    storage.remove(DEMO_KEY);
    void supabase?.auth.signOut({ scope: "local" });
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  // Initial session restore + Supabase auth events.
  useEffect(() => {
    const demo = readDemo();
    if (demo) {
      setUser({ id: demo.userId, email: null, isDemo: true, displayName: "Demo user" });
      setLoading(false);
      return;
    }
    if (!supabase) {
      setLoading(false);
      return;
    }
    supabase.auth.getSession().then(({ data }) => {
      setUser(userFromSupabase(data.session));
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      if (readDemo()) return;
      setUser(userFromSupabase(session));
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  // Give the API client a token source.
  useEffect(() => {
    configureApiAuth(async () => {
      const demo = readDemo();
      if (demo) return demo.token;
      if (!supabase) return null;
      const { data } = await supabase.auth.getSession(); // refreshes if needed
      return data.session?.access_token ?? null;
    }, handleUnauthorized);
  }, [handleUnauthorized]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      sessionExpired,
      clearExpired: () => setSessionExpired(false),
      async signIn(email, password) {
        if (!supabase) throw new Error("Email sign-in is not configured on this deployment.");
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw new Error(error.message === "Invalid login credentials" ? "Incorrect email or password." : error.message);
        setSessionExpired(false);
      },
      async signUp(email, password, displayName) {
        if (!supabase) throw new Error("Sign-up is not configured on this deployment.");
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/login?confirmed=1`,
            data: displayName ? { display_name: displayName } : undefined,
          },
        });
        if (error) throw new Error(error.message);
        return { needsConfirmation: !data.session };
      },
      async requestPasswordReset(email) {
        if (!supabase) throw new Error("Password reset is not configured on this deployment.");
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        });
        if (error) throw new Error(error.message);
      },
      async updatePassword(password) {
        if (!supabase) throw new Error("Password reset is not configured on this deployment.");
        const { error } = await supabase.auth.updateUser({ password });
        if (error) throw new Error(error.message);
      },
      async startDemo() {
        const res = await api.startDemo();
        const demo: DemoSession = { token: res.access_token, expiresAt: res.expires_at, userId: res.user_id };
        storage.set(DEMO_KEY, JSON.stringify(demo));
        resetClientState();
        setSessionExpired(false);
        setUser({ id: demo.userId, email: null, isDemo: true, displayName: "Demo user" });
      },
      async signOut(opts) {
        storage.remove(DEMO_KEY);
        if (supabase) await supabase.auth.signOut(opts?.local ? { scope: "local" } : undefined);
        setUser(null);
        resetClientState();
      },
    }),
    [user, loading, sessionExpired, resetClientState],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
