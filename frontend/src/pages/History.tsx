import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, History as HistoryIcon, Plus, Search, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ScorePill } from "@/components/evaluation";
import { PageHeader } from "@/components/layout";
import { SessionStatusBadge } from "@/components/SessionStatusBadge";
import { EmptyState, ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Badge, Card, Input, Progress, Select, Skeleton } from "@/components/ui/primitives";
import { useSessions } from "@/hooks/queries";
import { api, errorMessage } from "@/lib/api";
import { ROLE_OPTIONS } from "@/lib/constants";
import type { SessionSort, SessionSummary } from "@/lib/types";
import { formatDate } from "@/lib/utils";

const PAGE_SIZE = 10;

export default function History() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const role = params.get("role") ?? "";
  const sort = (params.get("sort") as SessionSort) || "date_desc";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [search, setSearch] = useState(q);
  const [toDelete, setToDelete] = useState<SessionSummary | null>(null);
  const qc = useQueryClient();

  const update = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!("page" in patch)) next.delete("page");
    setParams(next, { replace: true });
  };

  // Debounce search input into the URL.
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (search !== q) update({ q: search.trim() });
    }, 300);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const list = useSessions({ q: q || undefined, role_type: role || undefined, sort, page, page_size: PAGE_SIZE });
  const filtered = Boolean(q || role);

  const del = useMutation({
    mutationFn: (id: string) => api.deleteSession(id),
    onSuccess: (_, id) => {
      toast.success("Session deleted");
      setToDelete(null);
      qc.removeQueries({ queryKey: ["session", id] });
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      void qc.invalidateQueries({ queryKey: ["analytics"] });
    },
  });

  const totalPages = list.data ? Math.max(1, Math.ceil(list.data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <PageHeader
        eyebrow="History"
        title="Session history"
        description="Every interview you've practised, with scores and progress."
        actions={
          <Button asChild>
            <Link to="/interviews/new">
              <Plus /> New interview
            </Link>
          </Button>
        }
      />

      <div className="mb-4 grid gap-2 sm:grid-cols-[1fr_220px_180px]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search job title or company"
            className="pl-9"
            aria-label="Search sessions"
            maxLength={100}
          />
        </div>
        <Select value={role} onChange={(e) => update({ role: e.target.value })} aria-label="Filter by role">
          <option value="">All roles</option>
          {ROLE_OPTIONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </Select>
        <Select value={sort} onChange={(e) => update({ sort: e.target.value })} aria-label="Sort sessions">
          <option value="date_desc">Newest first</option>
          <option value="date_asc">Oldest first</option>
          <option value="score_desc">Highest score</option>
          <option value="score_asc">Lowest score</option>
        </Select>
      </div>

      {list.isLoading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}</div>
      ) : list.isError ? (
        <ErrorState error={list.error} onRetry={() => list.refetch()} />
      ) : list.data && list.data.items.length === 0 ? (
        filtered ? (
          <EmptyState icon={<Search />} title="No matching sessions" description="Try a different search or role filter." action={<Button variant="outline" size="sm" onClick={() => { setSearch(""); setParams({}); }}>Clear filters</Button>} />
        ) : (
          <EmptyState
            icon={<HistoryIcon />}
            title="No sessions yet"
            description="You haven't practiced an interview yet. Create your first session to get started."
            action={
              <Button asChild size="sm">
                <Link to="/interviews/new">
                  <Plus /> New interview
                </Link>
              </Button>
            }
          />
        )
      ) : (
        <>
          <ul className={`space-y-2 transition-opacity ${list.isPlaceholderData ? "opacity-60" : ""}`}>
            {list.data?.items.map((s) => (
              <li key={s.id}>
                <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
                  <Link to={`/history/${s.id}`} className="min-w-0 flex-1 rounded-sm">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate font-medium">{s.job_title}</p>
                      {s.company && <span className="truncate text-sm text-muted-foreground">· {s.company}</span>}
                      {s.is_demo && <Badge tone="accent">Demo</Badge>}
                    </div>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {formatDate(s.created_at)} · {s.role_label} · {s.answered_count}/{s.total_questions} answered
                    </p>
                    <div className="mt-2 flex max-w-xs items-center gap-2">
                      <Progress value={s.completion_pct} label={`${s.completion_pct}% complete`} />
                      <span className="text-xs tabular-nums text-muted-foreground">{Math.round(s.completion_pct)}%</span>
                    </div>
                  </Link>
                  <div className="flex items-center justify-between gap-3 sm:justify-end">
                    <SessionStatusBadge status={s.status} />
                    <ScorePill pct={s.average_score} className="w-28 justify-end" />
                    <div className="flex gap-1">
                      {s.status !== "completed" && (
                        <Button asChild size="sm" variant="outline">
                          <Link to={`/interviews/${s.id}`}>Resume</Link>
                        </Button>
                      )}
                      <Button size="icon" variant="ghost" aria-label={`Delete ${s.job_title} session`} onClick={() => { del.reset(); setToDelete(s); }}>
                        <Trash2 className="text-muted-foreground" />
                      </Button>
                    </div>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
          {totalPages > 1 && (
            <nav className="mt-4 flex items-center justify-between" aria-label="Pagination">
              <p className="text-sm text-muted-foreground">
                Page {page} of {totalPages} · {list.data?.total} sessions
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => update({ page: String(page - 1) })}>
                  <ChevronLeft /> Previous
                </Button>
                <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => update({ page: String(page + 1) })}>
                  Next <ChevronRight />
                </Button>
              </div>
            </nav>
          )}
        </>
      )}

      <ConfirmDialog
        open={!!toDelete}
        onOpenChange={(o) => !o && setToDelete(null)}
        title="Delete this session?"
        description={
          <>
            <span className="font-medium text-foreground">{toDelete?.job_title}</span> and all of its questions, answers and
            feedback will be permanently deleted. This can't be undone.
          </>
        }
        confirmLabel="Delete session"
        pending={del.isPending}
        error={del.isError ? errorMessage(del.error) : null}
        onConfirm={() => toDelete && del.mutate(toDelete.id)}
      />
    </div>
  );
}
