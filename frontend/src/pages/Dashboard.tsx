import { ArrowRight, ArrowUpRight, Briefcase, FileText, PlayCircle, RotateCcw, TrendingUp } from "lucide-react";
import { useMemo, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { ScorePill } from "@/components/evaluation";
import { ProgressChart } from "@/components/ProgressChart";
import { SessionStatusBadge } from "@/components/SessionStatusBadge";
import { EmptyState, ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Badge, Progress, Skeleton } from "@/components/ui/primitives";
import { useMe, useOverview, useProgress, useSessionDetail, useSessions } from "@/hooks/queries";
import { CATEGORY_LABELS, DIMENSIONS } from "@/lib/constants";
import type { SessionDetail } from "@/lib/types";
import { formatDate, formatPct } from "@/lib/utils";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

function Panel({ title, eyebrow, action, children, className }: { title?: ReactNode; eyebrow?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border bg-card ${className ?? ""}`}>
      {(title || action) && (
        <header className="flex items-end justify-between gap-4 border-b px-6 py-5">
          <div className="space-y-1">
            {eyebrow && <p className="eyebrow">{eyebrow}</p>}
            {title && <h2 className="text-[15px] font-medium">{title}</h2>}
          </div>
          {action}
        </header>
      )}
      <div className="p-6">{children}</div>
    </section>
  );
}

/** The most recent evaluated answer in a session, with its question. */
function latestFeedback(s: SessionDetail | undefined) {
  if (!s) return null;
  const evaluated = s.answers
    .filter((a) => a.evaluation)
    .sort((a, b) => (b.evaluated_at ?? "").localeCompare(a.evaluated_at ?? ""));
  const a = evaluated[0];
  if (!a?.evaluation) return null;
  const q = s.questions.find((x) => x.id === a.question_id);
  return { answer: a, evaluation: a.evaluation, question: q };
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const me = useMe();
  const overview = useOverview();
  const progress = useProgress();
  const recent = useSessions({ page: 1, page_size: 5, sort: "date_desc" });
  const o = overview.data;
  const recentId = o?.most_recent_session_id ?? recent.data?.items[0]?.id ?? "";
  const recentDetail = useSessionDetail(recentId);
  const feedback = useMemo(() => latestFeedback(recentDetail.data), [recentDetail.data]);

  const name = me.data?.display_name || user?.displayName;
  const inProgress = recent.data?.items.find((s) => s.status === "in_progress");
  const isNew = o?.total_sessions === 0;

  const practiceAgain = () => {
    const s = recentDetail.data;
    if (!s) return navigate("/interviews/new");
    navigate("/interviews/new", {
      state: {
        prefill: {
          resume_text: s.resume_text,
          jd_text: s.jd_text,
          job_title: s.job_title,
          company: s.company ?? "",
          role_type: s.role_type,
          seniority_level: s.seniority_level ?? "",
        },
      },
    });
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-5 border-b pb-8 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <p className="eyebrow">{formatDate(new Date().toISOString(), { weekday: "long", day: "numeric", month: "long" })}</p>
          <h1 className="display text-[2.6rem] sm:text-[3.2rem]">
            {greeting()}
            {name ? <>, <em>{name}</em></> : null}.
          </h1>
          <p className="text-[15px] text-muted-foreground">Your interview practice at a glance.</p>
        </div>
        <Button asChild size="lg">
          <Link to="/interviews/new">
            Start New Interview <ArrowRight />
          </Link>
        </Button>
      </header>

      {/* Start + next action */}
      <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        <section className="relative isolate overflow-hidden rounded-lg bg-ink p-7 text-paper sm:p-8 dark:border dark:border-border">
          <span className="absolute right-7 top-7 size-14 rounded-full bg-taupe" aria-hidden />
          <p className="eyebrow text-taupe-light">{isNew ? "Get started" : "New session"}</p>
          <h2 className="display mt-3 max-w-md text-[2.1rem] leading-[1.05] text-paper">
            {isNew ? "Build your first tailored interview." : "Prepare for your next role."}
          </h2>
          <p className="mt-3 max-w-md text-[14px] leading-relaxed text-paper/70">
            Paste your resume and a job description. We'll generate eight questions grounded in both.
          </p>
          <div className="mt-7 grid max-w-lg gap-3 sm:grid-cols-2">
            <Link to="/interviews/new" className="group border border-paper/40 p-4 transition-all duration-200 hover:bg-paper hover:text-ink">
              <FileText className="size-4" aria-hidden />
              <p className="mt-3 text-[14px] font-medium">Paste your resume</p>
              <p className="mt-0.5 text-xs opacity-70">Roles, projects, tools and results</p>
            </Link>
            <Link to="/interviews/new" className="group border border-paper/40 p-4 transition-all duration-200 hover:bg-paper hover:text-ink">
              <Briefcase className="size-4" aria-hidden />
              <p className="mt-3 text-[14px] font-medium">Add a job description</p>
              <p className="mt-0.5 text-xs opacity-70">Responsibilities and requirements</p>
            </Link>
          </div>
          {recentDetail.data && (
            <button onClick={practiceAgain} className="mt-5 inline-flex items-center gap-2 text-[13px] text-paper/75 underline-offset-4 hover:text-paper hover:underline">
              <RotateCcw className="size-3.5" aria-hidden /> Reuse your last resume and job description ({recentDetail.data.job_title})
            </button>
          )}
        </section>

        <Panel eyebrow="Next action" title={inProgress ? "Continue where you left off" : "Keep your momentum"}>
          {recent.isLoading ? (
            <Skeleton className="h-28" />
          ) : inProgress ? (
            <div className="space-y-5">
              <div>
                <p className="text-[15px] font-medium">{inProgress.job_title}</p>
                <p className="text-sm text-muted-foreground">
                  {inProgress.company ?? "Company not specified"} · started {formatDate(inProgress.created_at)}
                </p>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Progress</span>
                  <span className="tabular-nums">
                    {inProgress.answered_count} of {inProgress.total_questions} answered
                  </span>
                </div>
                <Progress value={inProgress.completion_pct} label="Interview progress" />
              </div>
              <Button asChild className="w-full">
                <Link to={`/interviews/${inProgress.id}`}>
                  <PlayCircle /> Resume interview
                </Link>
              </Button>
            </div>
          ) : isNew ? (
            <p className="text-sm leading-relaxed text-muted-foreground">
              No interviews yet. Start one with your resume and a job you're interested in — it takes a couple of minutes.
            </p>
          ) : (
            <div className="space-y-4">
              <p className="text-sm leading-relaxed text-muted-foreground">
                All your interviews are complete. Practise a new role, or repeat a past one to measure improvement.
              </p>
              <Button asChild variant="outline" className="w-full">
                <Link to="/history">
                  Review past sessions <ArrowUpRight />
                </Link>
              </Button>
            </div>
          )}
        </Panel>
      </div>

      {/* Statistics strip */}
      {overview.isError ? (
        <ErrorState error={overview.error} onRetry={() => overview.refetch()} />
      ) : (
        <section aria-label="Statistics" className="grid grid-cols-2 overflow-hidden rounded-lg border bg-card lg:grid-cols-4">
          {overview.isLoading || !o
            ? Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="p-6">
                  <Skeleton className="h-16" />
                </div>
              ))
            : [
                ["Interviews completed", String(o.completed_interviews), `${o.total_sessions} started`],
                ["Questions answered", String(o.total_questions_answered), `${o.evaluated_answers} evaluated`],
                ["Average answer score", formatPct(o.average_score), o.average_score === null ? "No evaluations yet" : "All evaluated answers"],
                ["Most recent session", formatPct(o.most_recent_session_score), o.most_recent_session_score === null ? "No scored sessions yet" : "Session average"],
              ].map(([label, value, hint], i) => (
                <div key={label} className={`p-6 ${i % 2 === 0 ? "border-r" : ""} ${i < 2 ? "border-b lg:border-b-0" : ""} ${i === 1 ? "lg:border-r" : ""}`}>
                  <p className="eyebrow">{label}</p>
                  <p className="display mt-3 text-[2.6rem] tabular-nums leading-none">{value}</p>
                  <p className="mt-2 text-xs text-muted-foreground">{hint}</p>
                </div>
              ))}
        </section>
      )}
      {o?.includes_demo_data && (
        <p className="-mt-5 text-xs text-muted-foreground">
          Includes <Badge tone="accent">demo</Badge> data (fictional sample history and/or heuristic demo scores) — not real performance results.
        </p>
      )}

      {/* Performance */}
      <div className="grid gap-5 lg:grid-cols-[1.45fr_1fr]">
        <Panel eyebrow="Performance" title="Average score over time">
          {progress.isLoading ? (
            <Skeleton className="h-64" />
          ) : progress.isError ? (
            <ErrorState error={progress.error} onRetry={() => progress.refetch()} />
          ) : (progress.data?.points.length ?? 0) < 2 ? (
            <EmptyState
              icon={<TrendingUp />}
              title={(progress.data?.points.length ?? 0) === 0 ? "No scores yet" : "One session so far"}
              description="Your trend appears once you have evaluated answers in at least two sessions."
              className="h-64"
            />
          ) : (
            <ProgressChart points={progress.data!.points} />
          )}
        </Panel>
        <Panel eyebrow="Rubric" title="Average by dimension">
          {overview.isLoading ? (
            <Skeleton className="h-48" />
          ) : o && o.evaluated_answers > 0 ? (
            <ul className="space-y-5">
              {DIMENSIONS.map((d) => {
                const v = o.dimension_averages[d.key];
                return (
                  <li key={d.key} className="space-y-2">
                    <div className="flex items-baseline justify-between text-sm">
                      <span title={d.description}>{d.label}</span>
                      <span className="tabular-nums">
                        <span className="font-medium">{v?.toFixed(1) ?? "—"}</span>
                        <span className="text-muted-foreground">/5</span>
                      </span>
                    </div>
                    <Progress value={((v ?? 0) / 5) * 100} label={`${d.label} average`} />
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState title="No evaluations yet" description="Answer a question to see your rubric profile." className="border-0 py-8" />
          )}
        </Panel>
      </div>

      {/* Feedback + sessions */}
      <div className="grid gap-5 lg:grid-cols-[1fr_1.35fr]">
        <Panel eyebrow="Recent feedback" title="Your latest evaluated answer">
          {recentDetail.isLoading && recentId ? (
            <Skeleton className="h-36" />
          ) : feedback ? (
            <div className="space-y-5">
              <div className="flex items-start justify-between gap-4">
                <p className="line-clamp-3 text-[14px] leading-relaxed">{feedback.question?.question_text}</p>
                <ScorePill pct={feedback.evaluation.percentage} className="shrink-0" />
              </div>
              {feedback.question && <Badge tone="primary">{CATEGORY_LABELS[feedback.question.category] ?? feedback.question.category}</Badge>}
              <div className="border-l-2 border-primary/60 pl-4">
                <p className="eyebrow">Recommended next step</p>
                <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{feedback.evaluation.one_thing_to_fix}</p>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link to={`/history/${recentId}`}>
                  Review full feedback <ArrowUpRight />
                </Link>
              </Button>
            </div>
          ) : (
            <p className="text-sm leading-relaxed text-muted-foreground">
              Feedback on your answers will appear here once you've completed a question.
            </p>
          )}
        </Panel>

        <Panel
          eyebrow="History"
          title="Recent sessions"
          action={
            <Link to="/history" className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground">
              View all <ArrowRight className="size-3.5" />
            </Link>
          }
        >
          {recent.isLoading ? (
            <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : recent.isError ? (
            <ErrorState error={recent.error} onRetry={() => recent.refetch()} />
          ) : recent.data && recent.data.items.length > 0 ? (
            <ul className="-my-2 divide-y">
              {recent.data.items.map((s) => (
                <li key={s.id}>
                  <Link
                    to={s.status === "completed" ? `/history/${s.id}` : `/interviews/${s.id}`}
                    className="-mx-3 flex flex-col gap-2 rounded-md px-3 py-3.5 transition-colors hover:bg-secondary/50 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-[14px] font-medium">
                        {s.job_title}
                        {s.company && <span className="font-normal text-muted-foreground"> · {s.company}</span>}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(s.created_at)} · {s.answered_count}/{s.total_questions} answered
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      {s.is_demo && <Badge tone="accent">Demo</Badge>}
                      <SessionStatusBadge status={s.status} />
                      <ScorePill pct={s.average_score} className="w-28 justify-end" />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No sessions yet" description="Your interviews will be listed here." className="border-0 py-8" />
          )}
        </Panel>
      </div>
    </div>
  );
}
