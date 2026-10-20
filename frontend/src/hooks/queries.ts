import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthProvider";
import { api, type ListParams } from "@/lib/api";
import type { SessionDetail } from "@/lib/types";

export const keys = {
  config: ["config"] as const,
  me: (uid?: string) => ["me", uid] as const,
  sessions: (params: ListParams) => ["sessions", params] as const,
  session: (id: string) => ["session", id] as const,
  overview: ["analytics", "overview"] as const,
  progress: ["analytics", "progress"] as const,
};

export function useConfig() {
  return useQuery({ queryKey: keys.config, queryFn: api.config, staleTime: 5 * 60_000, retry: 1 });
}

export function useMe() {
  const { user } = useAuth();
  return useQuery({ queryKey: keys.me(user?.id), queryFn: api.me, enabled: !!user });
}

export function useSessions(params: ListParams) {
  return useQuery({ queryKey: keys.sessions(params), queryFn: () => api.listSessions(params), placeholderData: keepPreviousData });
}

function hasPendingEvaluation(s: SessionDetail | undefined) {
  return !!s?.answers.some((a) => a.evaluation_status === "evaluating" || a.evaluation_status === "pending");
}

export function useSessionDetail(id: string) {
  return useQuery({
    queryKey: keys.session(id),
    queryFn: () => api.getSession(id),
    enabled: Boolean(id),
    // Another tab may be evaluating an answer: poll until it settles.
    refetchInterval: (q) => (hasPendingEvaluation(q.state.data) ? 3000 : false),
  });
}

export function useOverview() {
  return useQuery({ queryKey: keys.overview, queryFn: api.overview });
}

export function useProgress() {
  return useQuery({ queryKey: keys.progress, queryFn: api.progress });
}
