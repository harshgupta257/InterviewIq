import { ArrowLeft, ChevronDown, Eye, EyeOff, PlayCircle, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { AnswerReview } from "@/components/AnswerReview";
import { DemoLabel, ScorePill, ScoreRing } from "@/components/evaluation";
import { SessionStatusBadge } from "@/components/SessionStatusBadge";
import { ErrorState, FullPageLoader } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Badge, Card, CardContent, Progress } from "@/components/ui/primitives";
import { useSessionDetail } from "@/hooks/queries";
import { CATEGORY_LABELS, DIMENSIONS } from "@/lib/constants";
import { cn, formatDate } from "@/lib/utils";

function Collapsible({ title, children, defaultOpen = false, sensitive = false }: { title: string; children: string; defaultOpen?: boolean; sensitive?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const Icon = sensitive ? (open ? EyeOff : Eye) : ChevronDown;
  return (
    <div className="rounded-md border bg-card">
      <button className="flex w-full items-center justify-between px-5 py-3.5 text-left text-sm font-medium" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {title}
        <span className="flex items-center gap-1.5 text-xs font-normal text-muted-foreground">
          {sensitive && (open ? "Hide" : "Show")}
          <Icon className={cn("size-4 transition-transform", !sensitive && open && "rotate-180")} aria-hidden />
        </span>
      </button>
      {open && <pre className="max-h-80 overflow-auto whitespace-pre-wrap border-t px-4 py-3 font-sans text-sm leading-relaxed text-muted-foreground">{children}</pre>}
    </div>
  );
}

export default function SessionDetailPage() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const { data: s, isLoading, error, refetch } = useSessionDetail(sessionId);
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());

  const questions = useMemo(() => [...(s?.questions ?? [])].sort((a, b) => a.order_index - b.order_index), [s]);
  const answersByQ = useMemo(() => new Map(s?.answers.map((a) => [a.question_id, a])), [s]);

  if (isLoading) return <FullPageLoader label="Loading session" />;
  if (error || !s)
    return (
      <ErrorState
        error={error}
        onRetry={() => refetch()}
        action={
          <Button asChild variant="ghost" size="sm">
            <Link to="/history">Back to history</Link>
          </Button>
        }
      />
    );

  const toggle = (id: string) =>
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const allOpen = openIds.size === questions.length;

  const practiceAgain = () =>
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

  // Per-dimension averages for this session, from the saved evaluations.
  const evaluated = s.answers.filter((a) => a.evaluation);
  const dimAvg = DIMENSIONS.map((d) => ({
    ...d,
    value: evaluated.length ? evaluated.reduce((sum, a) => sum + (a.evaluation?.[d.key].score ?? 0), 0) / evaluated.length : null,
  }));

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <Link to="/history" className="inline-flex items-center gap-2 text-[13px] text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All sessions
      </Link>

      <header className="space-y-3 border-b pb-8">
        <div className="flex flex-wrap items-center gap-2">
          <p className="eyebrow">Session results</p>
          <SessionStatusBadge status={s.status} />
          <DemoLabel show={s.is_demo} text="Sample / demo content" />
        </div>
        <h1 className="display text-[2.6rem] leading-[1.05] sm:text-[3.2rem]">
          {s.job_title}
          {s.company && <span className="text-muted-foreground"> at {s.company}</span>}
        </h1>
        <p className="text-sm text-muted-foreground">
          {s.role_label}
          {s.seniority_level && ` · ${s.seniority_level}`} · {formatDate(s.created_at, { dateStyle: "medium", timeStyle: "short" })} · Model:{" "}
          {s.is_demo ? "demo heuristic" : s.ai_model}
        </p>
      </header>

      {/* Results summary */}
      <section className="grid overflow-hidden rounded-lg border bg-card md:grid-cols-[auto_1fr_auto]" aria-label="Results summary">
        <div className="flex items-center gap-5 border-b p-7 md:border-b-0 md:border-r">
          {s.average_score !== null ? <ScoreRing pct={s.average_score} label="Session average" /> : <div className="grid size-28 place-items-center border text-sm text-muted-foreground">No score</div>}
          <div className="space-y-1">
            <p className="eyebrow">Session average</p>
            <p className="text-sm text-muted-foreground">
              {s.evaluated_count} of {s.total_questions} answers evaluated
            </p>
            <p className="text-sm text-muted-foreground">
              {s.answered_count} of {s.total_questions} answered
            </p>
          </div>
        </div>
        <div className="space-y-4 p-7">
          <p className="eyebrow">By dimension</p>
          {evaluated.length ? (
            <ul className="space-y-3.5">
              {dimAvg.map((d) => (
                <li key={d.key} className="space-y-1.5 text-sm">
                  <div className="flex items-baseline justify-between gap-3">
                    <span title={d.description}>{d.label}</span>
                    <span className="tabular-nums">
                      {d.value?.toFixed(1)}
                      <span className="text-muted-foreground">/5</span>
                    </span>
                  </div>
                  <Progress value={((d.value ?? 0) / 5) * 100} label={`${d.label} average`} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">Scores appear here once answers are evaluated.</p>
          )}
        </div>
        <div className="flex flex-col justify-center gap-2 border-t p-7 md:border-l md:border-t-0">
          {s.status !== "completed" && (
            <Button asChild>
              <Link to={`/interviews/${s.id}`}>
                <PlayCircle /> Continue interview
              </Link>
            </Button>
          )}
          <Button variant={s.status === "completed" ? "default" : "outline"} onClick={practiceAgain}>
            <RotateCcw /> Practice again
          </Button>
          <Button asChild variant="ghost">
            <Link to="/interviews/new">Start a new interview</Link>
          </Button>
        </div>
      </section>

      <section className="space-y-3" aria-label="Context">
        <p className="eyebrow">Context</p>
        <Collapsible title="Job description">{s.jd_text}</Collapsible>
        <Collapsible title="Resume (hidden by default)" sensitive>
          {s.resume_text}
        </Collapsible>
      </section>

      <section className="space-y-3" aria-labelledby="questions-heading">
        <div className="flex items-center justify-between">
          <h2 id="questions-heading" className="display text-[2rem]">
            Questions & answers
          </h2>
          <Button variant="ghost" size="sm" onClick={() => setOpenIds(allOpen ? new Set() : new Set(questions.map((q) => q.id)))}>
            {allOpen ? "Collapse all" : "Expand all"}
          </Button>
        </div>
        {questions.map((q, i) => {
          const a = answersByQ.get(q.id);
          const open = openIds.has(q.id);
          return (
            <Card key={q.id}>
              <button className="flex w-full items-start gap-4 p-4 text-left sm:p-5" onClick={() => toggle(q.id)} aria-expanded={open}>
                <span className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-md bg-secondary text-xs font-semibold tabular-nums">{i + 1}</span>
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="primary">{CATEGORY_LABELS[q.category] ?? q.category}</Badge>
                    {!a && <Badge tone="outline">Not answered</Badge>}
                    {a?.evaluation_status === "failed" && <Badge tone="destructive">Evaluation failed</Badge>}
                    {a?.rewrite && <Badge tone="accent">Example saved</Badge>}
                  </div>
                  <p className={cn("text-sm font-medium leading-relaxed", !open && "line-clamp-2")}>{q.question_text}</p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {a?.evaluation && <ScorePill pct={a.evaluation.percentage} />}
                  <ChevronDown className={cn("size-4 text-muted-foreground transition-transform", open && "rotate-180")} aria-hidden />
                </div>
              </button>
              {open && (
                <CardContent className="space-y-4 border-t pt-4">
                  <p className="text-xs text-muted-foreground">
                    <span className="font-medium">Why this question:</span> {q.why_this_question}
                  </p>
                  {a ? (
                    <>
                      <div className="space-y-1.5">
                        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Your answer · {formatDate(a.answered_at)}</p>
                        {!a.rewrite && <p className="whitespace-pre-wrap rounded-md border bg-background/50 p-3.5 text-sm leading-relaxed">{a.answer_text}</p>}
                      </div>
                      <AnswerReview answer={a} sessionId={s.id} />
                    </>
                  ) : (
                    <p className="text-sm text-muted-foreground">This question hasn't been answered yet.</p>
                  )}
                </CardContent>
              )}
            </Card>
          );
        })}
      </section>
    </div>
  );
}
