import { AlertCircle, ArrowRightLeft, FlaskConical, Info, Lightbulb, Loader2, PenLine, RefreshCw } from "lucide-react";
import { DIMENSIONS } from "@/lib/constants";
import type { Answer, Evaluation, Rewrite } from "@/lib/types";
import { cn, formatPct, scoreBand } from "@/lib/utils";
import { Button } from "./ui/button";
import { Alert, Badge } from "./ui/primitives";

const toneClass = { good: "text-success", ok: "text-foreground", low: "text-warning" } as const;

export function ScorePill({ pct, className }: { pct: number | null | undefined; className?: string }) {
  if (pct === null || pct === undefined) return <span className={cn("text-sm text-muted-foreground", className)}>—</span>;
  const band = scoreBand(pct);
  return (
    <span className={cn("inline-flex items-baseline gap-1.5 tabular-nums", className)}>
      <span className={cn("font-medium", toneClass[band.tone])}>{formatPct(pct)}</span>
      <span className="text-xs text-muted-foreground">{band.label}</span>
    </span>
  );
}

/** Swiss score block: a large figure over a 10-cell bar. The number is always printed. */
export function ScoreRing({ pct, size = 112, label = "Overall score" }: { pct: number; size?: number; label?: string }) {
  const v = Math.max(0, Math.min(100, pct));
  const filled = Math.round(v / 10);
  return (
    <div className="shrink-0" style={{ width: size }} role="img" aria-label={`${label}: ${formatPct(pct)}`}>
      <p className="display text-[3.4rem] leading-none tabular-nums">
        {Math.round(v)}
        <span className="text-2xl font-normal">%</span>
      </p>
      <div className="mt-3 grid grid-cols-10 gap-[3px]" aria-hidden>
        {Array.from({ length: 10 }).map((_, i) => (
          <span key={i} className={cn("h-2", i < filled ? "bg-foreground" : "bg-secondary")} />
        ))}
      </div>
    </div>
  );
}

/** Five-segment meter with the numeric score beside it. */
export function ScoreMeter({ score, label }: { score: number; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex gap-1" role="img" aria-label={`${label}: ${score} out of 5`}>
        {[1, 2, 3, 4, 5].map((i) => (
          <span key={i} className={cn("h-2 w-5 sm:w-6", i <= score ? "bg-foreground" : "bg-secondary")} />
        ))}
      </div>
      <span className="w-8 text-right text-sm font-medium tabular-nums">
        {score}
        <span className="font-normal text-muted-foreground">/5</span>
      </span>
    </div>
  );
}

export function DemoLabel({ show, text = "Demo heuristic — not an AI evaluation" }: { show: boolean; text?: string }) {
  if (!show) return null;
  return (
    <Badge tone="accent">
      <FlaskConical aria-hidden /> {text}
    </Badge>
  );
}

export function EvaluationPanel({ evaluation }: { evaluation: Evaluation }) {
  const band = scoreBand(evaluation.percentage);
  const dims = DIMENSIONS.map((d) => ({ ...d, ...evaluation[d.key] }));
  const strengths = dims.filter((d) => d.score >= 4);
  const improvements = dims.filter((d) => d.score <= 3);

  return (
    <section className="overflow-hidden rounded-lg border bg-card" aria-label="Evaluation">
      <header className="flex flex-col gap-6 border-b p-6 sm:flex-row sm:items-end sm:justify-between sm:p-7">
        <div className="flex items-center gap-6">
          <ScoreRing pct={evaluation.percentage} />
          <div className="space-y-1.5">
            <p className="eyebrow">Evaluation</p>
            <p className="display text-3xl">{band.label}</p>
            <p className="text-xs text-muted-foreground">
              Average {evaluation.average.toFixed(2)} / 5 · four equally weighted dimensions
            </p>
          </div>
        </div>
        <DemoLabel show={evaluation.is_demo} />
      </header>

      <div className="grid sm:grid-cols-2">
        {dims.map((d, i) => (
          <div key={d.key} className={cn("space-y-2.5 p-6 sm:p-7", i % 2 === 0 && "sm:border-r", i < 2 && "border-b", i === 2 && "max-sm:border-b")}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-[14px] font-medium" title={d.description}>
                {d.label}
              </p>
              <ScoreMeter score={d.score} label={d.label} />
            </div>
            <p className="text-[13.5px] leading-relaxed text-muted-foreground">{d.reason}</p>
          </div>
        ))}
      </div>

      <div className="grid border-t md:grid-cols-3">
        <div className="space-y-3 p-6 sm:p-7 md:border-r">
          <p className="eyebrow text-foreground">Strengths</p>
          {strengths.length ? (
            <ul className="space-y-2 text-[13.5px] leading-relaxed">
              {strengths.map((d) => (
                <li key={d.key}>
                  <span className="font-medium">{d.label}</span> <span className="text-muted-foreground">· {d.score}/5</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[13.5px] text-muted-foreground">No dimension scored 4 or higher yet.</p>
          )}
        </div>
        <div className="space-y-3 border-t p-6 sm:p-7 md:border-r md:border-t-0">
          <p className="eyebrow text-accent-foreground">Areas to improve</p>
          {improvements.length ? (
            <ul className="space-y-2 text-[13.5px] leading-relaxed">
              {improvements.map((d) => (
                <li key={d.key}>
                  <span className="font-medium">{d.label}</span> <span className="text-muted-foreground">· {d.score}/5</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[13.5px] text-muted-foreground">Every dimension scored 4 or higher.</p>
          )}
        </div>
        <div className="space-y-3 border-t bg-foreground p-6 text-background sm:p-7 md:border-t-0">
          <p className="eyebrow text-background/70">Recommended next step</p>
          <p className="text-[14px] font-medium leading-relaxed">{evaluation.one_thing_to_fix}</p>
        </div>
      </div>

      <div className="border-t p-6 sm:p-7">
        <p className="eyebrow">Overall feedback</p>
        <p className="mt-2.5 max-w-3xl text-[14.5px] leading-relaxed">{evaluation.overall_feedback}</p>
      </div>
    </section>
  );
}

export function EvaluationFailed({ answer, onRetry, retrying }: { answer: Answer; onRetry: () => void; retrying: boolean }) {
  return (
    <Alert
      tone="error"
      icon={<AlertCircle className="text-destructive" />}
      title="Your answer is saved, but evaluation failed"
      action={
        <Button size="sm" variant="outline" onClick={onRetry} loading={retrying}>
          {!retrying && <RefreshCw />} Retry evaluation
        </Button>
      }
    >
      {answer.evaluation_error ?? "The AI service did not return a valid evaluation."} You can retry now or continue and retry later.
    </Alert>
  );
}

export function EvaluatingState() {
  return (
    <div className="flex items-center gap-4 rounded-lg border bg-card p-6" role="status" aria-live="polite">
      <Loader2 className="size-5 animate-spin text-accent-foreground" aria-hidden />
      <div>
        <p className="text-[14px] font-medium">Evaluating your answer</p>
        <p className="text-[13px] text-muted-foreground">This can take up to a minute. Your answer is already saved.</p>
      </div>
    </div>
  );
}

export function RewritePanel({
  original,
  rewrite,
  onRegenerate,
  regenerating,
}: {
  original: string;
  rewrite: Rewrite;
  onRegenerate?: () => void;
  regenerating?: boolean;
}) {
  return (
    <section className="overflow-hidden rounded-lg border bg-card" aria-label="Compare with a stronger example">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b p-6 sm:px-7">
        <div className="flex items-center gap-2.5">
          <ArrowRightLeft className="size-4 text-muted-foreground" aria-hidden />
          <h3 className="text-[15px] font-medium">Compare with a stronger example</h3>
        </div>
        <div className="flex items-center gap-2">
          <DemoLabel show={rewrite.is_demo} text="Demo template — not AI-written" />
          {onRegenerate && (
            <Button size="sm" variant="ghost" onClick={onRegenerate} loading={regenerating}>
              {!regenerating && <RefreshCw />} Regenerate
            </Button>
          )}
        </div>
      </header>
      <div className="space-y-6 p-6 sm:p-7">
        <Alert tone="info" icon={<Info />}>
          An illustrative example for learning, not a verified statement about your experience. Replace any
          [bracketed placeholders] with real details, and never claim anything you didn't do.
        </Alert>
        <div className="grid gap-5 lg:grid-cols-2">
          <section className="space-y-2.5" aria-labelledby="your-answer">
            <h4 id="your-answer" className="eyebrow">
              Your answer
            </h4>
            <div className="whitespace-pre-wrap border bg-secondary p-4 text-[14px] leading-relaxed">{original}</div>
          </section>
          <section className="space-y-2.5" aria-labelledby="example-answer">
            <h4 id="example-answer" className="eyebrow flex items-center gap-1.5 text-foreground">
              <PenLine className="size-3.5" aria-hidden /> Example of a stronger answer
            </h4>
            <div className="whitespace-pre-wrap border border-foreground bg-card p-4 text-[14px] leading-relaxed">
              {rewrite.improved_answer}
            </div>
          </section>
        </div>
        <div className="grid gap-6 border-t pt-6 md:grid-cols-2">
          <section className="space-y-3">
            <h4 className="eyebrow">What changed</h4>
            <ul className="space-y-2 text-[13.5px] leading-relaxed text-muted-foreground">
              {rewrite.improvements.map((item, i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="mt-2 h-px w-3 shrink-0 bg-foreground" aria-hidden />
                  {item}
                </li>
              ))}
            </ul>
          </section>
          {rewrite.missing_information.length > 0 && (
            <section className="space-y-3">
              <h4 className="eyebrow">Details only you can add</h4>
              <ul className="space-y-2 text-[13.5px] leading-relaxed text-muted-foreground">
                {rewrite.missing_information.map((item, i) => (
                  <li key={i} className="flex gap-2.5">
                    <span className="mt-2 h-px w-3 shrink-0 bg-taupe" aria-hidden />
                    {item}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
        {rewrite.suggested_follow_up && (
          <div className="flex gap-3 rounded-md bg-secondary/70 p-4 text-[13.5px]">
            <Lightbulb className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
            <p>
              <span className="font-medium">Likely follow-up: </span>
              <span className="text-muted-foreground">{rewrite.suggested_follow_up}</span>
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
