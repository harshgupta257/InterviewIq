import { ArrowRight, ArrowUpRight, ChevronDown, FlaskConical, PlayCircle } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/primitives";
import { formatSalary, LEVEL_LABELS, WORK_MODE_LABELS } from "@/lib/jobs";
import type { JobResult } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

function Meta({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="min-w-0">
      <dt className="text-[11px] font-semibold uppercase tracking-eyebrow text-muted-foreground">{label}</dt>
      <dd className={cn("mt-1 break-words text-sm leading-snug", !value && "text-muted-foreground")}>{value ?? "Not listed"}</dd>
    </div>
  );
}

/** "Adzuna" attribution required on each listing (min. 116 x 23 px, linking to Adzuna). */
export function SourceAttribution({ label, url }: { label: string; url: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex min-h-[23px] min-w-[116px] items-center justify-center border border-foreground px-2 text-[11px] font-semibold uppercase tracking-[0.06em] transition-all duration-200 hover:bg-foreground hover:text-background"
    >
      {label}
    </a>
  );
}

export function JobCard({
  job,
  attribution,
  onPrepare,
  onRescore,
}: {
  job: JobResult;
  attribution: { label: string; url: string } | null;
  onPrepare: (job: JobResult) => void;
  onRescore: (job: JobResult) => void;
}) {
  const [open, setOpen] = useState(false);
  const m = job.match;
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency);

  return (
    <article className="grid border border-foreground lg:grid-cols-12" aria-labelledby={`job-${job.id}`}>
      {/* Listing data (from the source) */}
      <div className="space-y-5 p-6 lg:col-span-7 lg:border-r lg:border-foreground">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h3 id={`job-${job.id}`} className="text-xl font-bold leading-tight tracking-[-0.02em]">
              {job.title}
            </h3>
            <p className="mt-1 text-[15px]">{job.company ?? <span className="text-muted-foreground">Company not listed</span>}</p>
          </div>
          {attribution && <SourceAttribution {...attribution} />}
        </div>

        <dl className="grid grid-cols-2 gap-4 border-y py-4 sm:grid-cols-4">
          <Meta label="Location" value={job.location} />
          <Meta label="Arrangement" value={job.work_mode ? WORK_MODE_LABELS[job.work_mode] : null} />
          <Meta label="Type" value={job.employment_type} />
          <Meta label="Salary" value={salary} />
        </dl>

        <div className="space-y-2">
          <p className="eyebrow">
            {job.description_source === "user_provided" ? "Full description (added by you)" : `Listing summary from ${job.source}`}
          </p>
          <p className={cn("text-[14px] leading-relaxed text-muted-foreground", !open && "line-clamp-3")}>
            {job.description ?? "This listing has no description. Open the job to read it."}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
          <span>
            {job.posted_at ? `Posted ${formatDate(job.posted_at)}` : "Posting date not listed"} · Found {formatDate(job.retrieved_at)}
            {job.experience_level && ` · Title suggests ${LEVEL_LABELS[job.experience_level] ?? job.experience_level}`}
          </span>
          <span>Listing status not confirmed — check the job page.</span>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <a href={job.url} target="_blank" rel="noopener noreferrer">
              View job <ArrowUpRight />
            </a>
          </Button>
          {job.interview_session_id ? (
            <Button asChild>
              <Link to={`/interviews/${job.interview_session_id}`}>
                <PlayCircle /> Open interview
              </Link>
            </Button>
          ) : (
            <Button onClick={() => onPrepare(job)}>
              Prepare for interview <ArrowRight />
            </Button>
          )}
        </div>
      </div>

      {/* AI analysis */}
      <div className="flex flex-col border-t border-foreground bg-secondary/60 p-6 lg:col-span-5 lg:border-t-0">
        <div className="flex items-center justify-between gap-2">
          <p className="eyebrow text-foreground">AI match analysis</p>
          {m?.is_demo && (
            <Badge tone="accent">
              <FlaskConical aria-hidden /> Demo heuristic
            </Badge>
          )}
        </div>
        {m ? (
          <>
            <div className="mt-4 flex items-end justify-between gap-4">
              <p className="display text-6xl tabular-nums" aria-label={`Match score ${m.score} out of 100`}>
                {m.score}
              </p>
              <div className="text-right">
                <p className="text-[15px] font-bold">{m.label}</p>
                <p className="text-xs text-muted-foreground">
                  {m.confidence === "full" ? "Based on the full description" : "Provisional — based on a listing summary"}
                </p>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-10 gap-[3px]" aria-hidden>
              {Array.from({ length: 10 }).map((_, i) => (
                <span key={i} className={cn("h-2", i < Math.round(m.score / 10) ? "bg-foreground" : "bg-background")} />
              ))}
            </div>

            <div className="mt-5 space-y-3">
              <div>
                <p className="text-xs font-semibold">Matching skills</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {m.matched_skills.length ? m.matched_skills.map((s) => <Badge key={s} tone="success">{s}</Badge>) : <span className="text-xs text-muted-foreground">None identified</span>}
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold">Gaps — not shown on your resume</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {m.missing_skills.length ? m.missing_skills.map((s) => <Badge key={s} tone="warning">{s}</Badge>) : <span className="text-xs text-muted-foreground">None identified</span>}
                </div>
              </div>
              <p className="text-[13.5px] leading-relaxed">{m.reasons[0]}</p>
            </div>

            <button
              onClick={() => setOpen((o) => !o)}
              aria-expanded={open}
              className="mt-4 inline-flex items-center gap-1.5 self-start text-sm font-semibold underline-offset-4 transition-all duration-200 hover:underline"
            >
              {open ? "Hide full analysis" : "Full analysis"}
              <ChevronDown className={cn("size-4 transition-transform duration-200", open && "rotate-180")} aria-hidden />
            </button>
            {open && (
              <div className="mt-4 space-y-4 border-t border-foreground pt-4 text-[13.5px] leading-relaxed">
                {m.reasons.length > 1 && (
                  <section>
                    <p className="text-xs font-semibold">Why it matches</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4">{m.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
                  </section>
                )}
                {m.relevant_experience.length > 0 && (
                  <section>
                    <p className="text-xs font-semibold">Relevant experience</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4">{m.relevant_experience.map((r) => <li key={r}>{r}</li>)}</ul>
                  </section>
                )}
                {m.improvements.length > 0 && (
                  <section>
                    <p className="text-xs font-semibold">Suggested improvements</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4">{m.improvements.map((r) => <li key={r}>{r}</li>)}</ul>
                  </section>
                )}
                {m.gaps.length > 0 && (
                  <section>
                    <p className="text-xs font-semibold">Gaps and uncertainties</p>
                    <ul className="mt-1 list-disc space-y-1 pl-4">{m.gaps.map((r) => <li key={r}>{r}</li>)}</ul>
                  </section>
                )}
                <p className="text-xs text-muted-foreground">
                  Score = 40% skill coverage + 25% experience + 20% role alignment + 15% responsibilities. It estimates how
                  well your resume aligns with this listing — not your chance of being hired.
                </p>
                {m.confidence === "provisional" && (
                  <Button variant="outline" size="sm" onClick={() => onRescore(job)}>
                    Re-score with the full description
                  </Button>
                )}
              </div>
            )}
          </>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">Not scored yet. Run the match evaluation to see how well your resume fits.</p>
        )}
      </div>
    </article>
  );
}
