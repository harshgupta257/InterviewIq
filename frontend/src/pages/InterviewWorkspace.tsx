import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, ChevronDown, ChevronLeft, CircleHelp, LogOut, Save, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { AnswerReview } from "@/components/AnswerReview";
import { useMergeAnswer } from "@/hooks/useMergeAnswer";
import { DemoLabel } from "@/components/evaluation";
import { ErrorState, FullPageLoader } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Label, Progress, Textarea } from "@/components/ui/primitives";
import { keys, useConfig, useSessionDetail } from "@/hooks/queries";
import { api, ApiError, errorMessage } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";
import type { Question, SessionDetail } from "@/lib/types";
import { cn, storage } from "@/lib/utils";

const draftKey = (sessionId: string, questionId: string) => `iq_draft_${sessionId}_${questionId}`;

function AnswerEditor({ session, question }: { session: SessionDetail; question: Question }) {
  const config = useConfig();
  const min = config.data?.limits.answer_min ?? 20;
  const max = config.data?.limits.answer_max ?? 6000;
  const key = draftKey(session.id, question.id);
  const [text, setText] = useState(() => storage.get(key) ?? "");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const merge = useMergeAnswer(session.id);
  const qc = useQueryClient();

  // Debounced local draft autosave: survives refreshes, crashes and network loss.
  useEffect(() => {
    const t = window.setTimeout(() => {
      if (text.trim()) {
        storage.set(key, text);
        setSavedAt(new Date());
      } else storage.remove(key);
    }, 600);
    return () => window.clearTimeout(t);
  }, [text, key]);

  const submit = useMutation({
    mutationFn: () => api.submitAnswer(session.id, question.id, text.trim()),
    onSuccess: (answer) => {
      storage.remove(key);
      merge(answer);
      if (answer.evaluation_status === "failed") toast.warning("Answer saved, but evaluation failed. You can retry.");
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        // Another tab already answered; reload authoritative state.
        void qc.invalidateQueries({ queryKey: keys.session(session.id) });
      }
    },
  });

  const len = text.trim().length;
  const tooShort = len < min;
  const tooLong = len > max;
  const disabled = submit.isPending || tooShort || tooLong;

  return (
    <section className="rounded-lg border bg-card focus-within:border-foreground/25" aria-label="Your answer">
      <div className="flex items-center justify-between border-b px-6 py-3.5">
        <Label htmlFor="answer" className="eyebrow">
          Your answer
        </Label>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground" aria-live="polite">
          {savedAt && (
            <>
              <Save className="size-3" aria-hidden /> Draft saved on this device
            </>
          )}
        </span>
      </div>
      <Textarea
        id="answer"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={submit.isPending}
        className="min-h-[300px] resize-y rounded-none border-0 bg-transparent px-6 py-5 text-[16px] leading-[1.75] focus-visible:ring-0 focus-visible:ring-offset-0"
        placeholder="Answer as you would in the interview. Be specific: what you did, why, and what happened."
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !disabled) submit.mutate();
        }}
        aria-describedby="answer-count"
      />
      <div className="flex flex-col gap-3 border-t px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <p id="answer-count" className={cn("text-xs tabular-nums", tooLong ? "text-destructive" : "text-muted-foreground")}>
          {len.toLocaleString()} / {max.toLocaleString()} characters
          {tooShort && len > 0 && ` · at least ${min} needed`}
          <span className="hidden sm:inline"> · Ctrl/⌘ + Enter to submit</span>
        </p>
        <Button onClick={() => submit.mutate()} disabled={disabled} loading={submit.isPending}>
          {!submit.isPending && <Send />}
          {submit.isPending ? "Saving & evaluating…" : "Submit answer"}
        </Button>
      </div>
      {submit.isError && (
        <div className="border-t p-4">
          <Alert tone="error" title="Your answer was not submitted">
            {errorMessage(submit.error)} Your draft is still saved on this device.
          </Alert>
        </div>
      )}
    </section>
  );
}

function QuestionCard({ question, index, total }: { question: Question; index: number; total: number }) {
  return (
    <section className="space-y-6" aria-label={`Question ${index + 1} of ${total}`}>
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="eyebrow">
          Question {index + 1} of {total}
        </span>
        <span className="text-border" aria-hidden>
          /
        </span>
        <Badge tone="primary">{CATEGORY_LABELS[question.category] ?? question.category}</Badge>
        {question.difficulty && <Badge tone="outline">{question.difficulty}</Badge>}
      </div>
      <h2 className="display text-[2rem] leading-[1.15] sm:text-[2.5rem]">{question.question_text}</h2>
      <details className="group rounded-md border bg-card/60 px-5 py-3.5 text-sm">
        <summary className="flex cursor-pointer list-none items-center gap-2 text-muted-foreground [&::-webkit-details-marker]:hidden">
          <CircleHelp className="size-4" aria-hidden /> Why this question?
          <ChevronDown className="ml-auto size-4 transition-transform group-open:rotate-180" aria-hidden />
        </summary>
        <div className="mt-3 space-y-2.5 border-t pt-3 leading-relaxed">
          <p>{question.why_this_question}</p>
          {question.source_context.length > 0 && (
            <p className="text-xs text-muted-foreground">Based on: {question.source_context.join(" · ")}</p>
          )}
          {question.evaluation_focus.length > 0 && (
            <p className="text-xs text-muted-foreground">A strong answer shows: {question.evaluation_focus.join(", ")}</p>
          )}
        </div>
      </details>
    </section>
  );
}

export default function InterviewWorkspace() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const { data: session, isLoading, error, refetch } = useSessionDetail(sessionId);
  const [active, setActive] = useState<number | null>(null);

  const questions = useMemo(() => [...(session?.questions ?? [])].sort((a, b) => a.order_index - b.order_index), [session]);
  const answersByQ = useMemo(() => new Map(session?.answers.map((a) => [a.question_id, a])), [session]);
  const nextIndex = session?.progress.current_question_index ?? 0;

  // Restore position from the database (source of truth) on first load.
  useEffect(() => {
    if (session && active === null) setActive(Math.min(nextIndex, questions.length - 1));
  }, [session, active, nextIndex, questions.length]);

  if (isLoading) return <FullPageLoader label="Loading your interview" />;
  if (error || !session)
    return (
      <ErrorState
        error={error}
        onRetry={() => refetch()}
        action={
          <Button asChild variant="ghost" size="sm">
            <Link to="/dashboard">Back to dashboard</Link>
          </Button>
        }
      />
    );

  const idx = active ?? 0;
  const question = questions[idx];
  const answer = question ? answersByQ.get(question.id) : undefined;
  const isNext = idx === nextIndex;
  const allAnswered = nextIndex >= questions.length;
  const pct = (session.progress.answered_count / Math.max(1, questions.length)) * 100;

  return (
    <div className="mx-auto max-w-3xl">
      {/* Session header + progress rail */}
      <div className="space-y-5 border-b pb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="eyebrow">Interview session</p>
            <p className="mt-1.5 truncate text-[17px] font-medium">{session.job_title}</p>
            <p className="truncate text-sm text-muted-foreground">
              {session.company ?? "Company not specified"} · {session.role_label}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <DemoLabel show={session.is_demo} text="Demo content" />
            <Button variant="outline" size="sm" onClick={() => navigate("/dashboard")}>
              <LogOut /> Save & exit
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Progress value={pct} label="Interview progress" />
          <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
            {session.progress.answered_count} of {questions.length} answered
          </span>
        </div>
        <nav aria-label="Questions" className="flex flex-wrap gap-1.5">
          {questions.map((q, i) => {
            const a = answersByQ.get(q.id);
            const reachable = i <= nextIndex;
            return (
              <button
                key={q.id}
                onClick={() => reachable && setActive(i)}
                disabled={!reachable}
                aria-current={i === idx ? "step" : undefined}
                aria-label={`Question ${i + 1}${a ? ", answered" : reachable ? ", current" : ", locked"}`}
                className={cn(
                  "grid size-8 place-items-center rounded-md border bg-card text-xs tabular-nums transition-colors hover:border-foreground/30",
                  i === idx && "border-primary bg-primary text-primary-foreground hover:border-primary",
                  i !== idx && a?.evaluation_status === "completed" && "border-accent-foreground/20 bg-accent text-accent-foreground",
                  i !== idx && a?.evaluation_status === "failed" && "border-destructive/30 bg-destructive/10 text-destructive",
                  !reachable && "cursor-not-allowed opacity-40 hover:border-border",
                )}
              >
                {i + 1}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="space-y-6 py-8">
        {session.progress.failed_evaluations > 0 && (
          <Alert tone="warning" title={`${session.progress.failed_evaluations} answer(s) still need evaluation`}>
            Open the highlighted question(s) and choose “Retry evaluation”.
          </Alert>
        )}

        {question && <QuestionCard question={question} index={idx} total={questions.length} />}

        {question && !answer && isNext && <AnswerEditor key={question.id} session={session} question={question} />}

        {answer && (
          <>
            <section className="rounded-lg border bg-card p-6">
              <p className="eyebrow">Your submitted answer</p>
              <p className="mt-3 whitespace-pre-wrap text-[15px] leading-relaxed">{answer.answer_text}</p>
            </section>
            <AnswerReview answer={answer} sessionId={session.id} />
          </>
        )}

        {answer && idx === questions.length - 1 && allAnswered && (
          <section className="rounded-lg bg-ink p-8 text-paper">
            <p className="eyebrow text-taupe-light">Interview complete</p>
            <h2 className="display mt-3 text-[2.2rem] text-paper">You've answered all {questions.length} questions.</h2>
            <p className="mt-2 max-w-lg text-[14px] leading-relaxed text-paper/70">
              Review every answer alongside its evaluation, or start another interview.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Button asChild variant="inverse">
                <Link to={`/history/${session.id}`}>
                  <CheckCircle2 /> Review session results
                </Link>
              </Button>
              <Button asChild variant="outline-light">
                <Link to="/interviews/new">Start another interview</Link>
              </Button>
            </div>
          </section>
        )}
      </div>

      <div className="flex items-center justify-between gap-3 border-t pt-6">
        <Button variant="ghost" onClick={() => setActive(Math.max(0, idx - 1))} disabled={idx === 0}>
          <ChevronLeft /> Previous
        </Button>
        {answer && idx < questions.length - 1 && (
          <Button onClick={() => setActive(idx + 1)}>
            Continue to next question <ArrowRight />
          </Button>
        )}
        {!answer && !isNext && (
          <Button variant="outline" onClick={() => setActive(nextIndex)}>
            Go to current question <ArrowRight />
          </Button>
        )}
      </div>
    </div>
  );
}
