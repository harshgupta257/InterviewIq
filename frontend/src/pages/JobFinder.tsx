import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Check, Info, Loader2, RefreshCw, Search, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { Step } from "@/components/FormStep";
import { JobActionDialog } from "@/components/jobs/JobActionDialog";
import { JobCard, SourceAttribution } from "@/components/jobs/JobCard";
import { ResumeInput } from "@/components/jobs/ResumeInput";
import { PageHeader } from "@/components/layout";
import { EmptyState, ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Alert, Badge, Input, Label, Select, Skeleton } from "@/components/ui/primitives";
import { keys, useConfig } from "@/hooks/queries";
import { api, ApiError, errorMessage } from "@/lib/api";
import { EMPLOYMENT_LABELS, LEVEL_LABELS, resumeMemory, WORK_MODE_LABELS } from "@/lib/jobs";
import type { EmploymentFilter, JobProfile, JobResult, JobSearch, ProfileLevel, RoleType, WorkMode } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

type Stage = "profile" | "search" | "match";
const STAGES: { key: Stage; label: string; detail: string }[] = [
  { key: "profile", label: "Analysing resume", detail: "Extracting skills, experience and suggested roles" },
  { key: "search", label: "Discovering listings", detail: "Querying the job-search service with role keywords and location" },
  { key: "match", label: "Evaluating matches", detail: "Comparing each listing with your resume" },
];

function stageError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "job_search_quota_exceeded") return "The job-search service's usage limit has been reached. Try again later.";
    if (err.code === "rate_limited") return err.message;
  }
  return errorMessage(err);
}

function Checks<T extends string>({ name, options, value, onChange }: { name: string; options: Record<string, string>; value: T[]; onChange: (v: T[]) => void }) {
  return (
    <fieldset className="flex flex-wrap gap-2">
      <legend className="sr-only">{name}</legend>
      {Object.entries(options).map(([k, label]) => {
        const on = value.includes(k as T);
        return (
          <label
            key={k}
            className={cn(
              "inline-flex cursor-pointer items-center gap-2 border px-3 py-2 text-sm transition-all duration-200 focus-within:ring-2 focus-within:ring-ring",
              on ? "border-foreground bg-foreground text-background" : "border-border hover:border-foreground",
            )}
          >
            <input type="checkbox" className="sr-only" checked={on} onChange={() => onChange(on ? value.filter((x) => x !== k) : [...value, k as T])} />
            {on && <Check className="size-3.5" aria-hidden />}
            {label}
          </label>
        );
      })}
    </fieldset>
  );
}

function ProfileSummary({ profile, onAddRole }: { profile: JobProfile; onAddRole: (r: string) => void }) {
  return (
    <div className="space-y-4 border border-foreground p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="eyebrow text-foreground">Extracted profile</p>
        <span className="text-xs text-muted-foreground">Generated automatically — check it, and adjust your preferences below.</span>
      </div>
      <p className="text-[14px] leading-relaxed">{profile.summary}</p>
      <dl className="grid gap-4 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs font-semibold">Level</dt>
          <dd className="mt-1">{LEVEL_LABELS[profile.experience_level] ?? profile.experience_level}{profile.years_experience ? ` · ~${profile.years_experience} yrs` : ""}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-xs font-semibold">Skills and tools</dt>
          <dd className="mt-1 flex flex-wrap gap-1.5">
            {[...profile.skills, ...profile.tools.filter((t) => !profile.skills.includes(t))].slice(0, 18).map((s) => (
              <Badge key={s} tone="outline">{s}</Badge>
            ))}
          </dd>
        </div>
      </dl>
      {profile.suggested_roles.length > 0 && (
        <div>
          <p className="text-xs font-semibold">Suggested roles — click to add</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {profile.suggested_roles.map((r) => (
              <button key={r} type="button" onClick={() => onAddRole(r)} className="border border-foreground px-3 py-1.5 text-sm transition-all duration-200 hover:bg-foreground hover:text-background">
                + {r}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Progress({ stage, skipProfile, onCancel }: { stage: Stage; skipProfile: boolean; onCancel: () => void }) {
  const order: Stage[] = ["profile", "search", "match"];
  const current = order.indexOf(stage);
  return (
    <section className="border border-foreground" aria-live="polite" aria-label="Search progress">
      <ol className="grid md:grid-cols-3">
        {STAGES.map((s, i) => {
          const skipped = s.key === "profile" && skipProfile;
          const done = i < current || skipped;
          const active = i === current;
          return (
            <li key={s.key} className={cn("border-b border-foreground p-5 md:border-b-0", i < 2 && "md:border-r", active && "bg-foreground text-background")}>
              <div className="flex items-center gap-2 text-sm font-bold">
                {active ? <Loader2 className="size-4 animate-spin" aria-hidden /> : done ? <Check className="size-4" aria-hidden /> : <span className="size-4 text-center text-xs">{i + 1}</span>}
                {s.label}
              </div>
              <p className={cn("mt-1 text-xs", active ? "text-background/80" : "text-muted-foreground")}>{skipped ? "Using the profile already extracted" : s.detail}</p>
            </li>
          );
        })}
      </ol>
      <div className="flex items-center justify-between border-t border-foreground px-5 py-3 text-xs text-muted-foreground">
        <span>AI steps can take up to a minute when the service is busy.</span>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          <X /> Cancel
        </Button>
      </div>
    </section>
  );
}

export default function JobFinder() {
  const { searchId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const config = useConfig();
  const enabled = config.data?.job_search.enabled ?? false;
  const minResume = config.data?.limits.resume_min ?? 150;

  const [resume, setResumeState] = useState(resumeMemory.get());
  const setResume = (t: string) => {
    setResumeState(t);
    resumeMemory.set(t);
  };
  const [profile, setProfile] = useState<JobProfile | null>(null);
  const [profileFor, setProfileFor] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [roleInput, setRoleInput] = useState("");
  const [location, setLocation] = useState("");
  const [level, setLevel] = useState<ProfileLevel | "">("");
  const [workModes, setWorkModes] = useState<WorkMode[]>([]);
  const [employment, setEmployment] = useState<EmploymentFilter[]>([]);
  const [resumeError, setResumeError] = useState<string | undefined>();
  const [stage, setStage] = useState<Stage | null>(null);
  const [skipProfile, setSkipProfile] = useState(false);
  const [runError, setRunError] = useState<{ stage: Stage; message: string } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const saved = useQuery({ queryKey: ["job-search", searchId], queryFn: () => api.getJobSearch(searchId!), enabled: Boolean(searchId) });
  const recent = useQuery({ queryKey: ["job-searches"], queryFn: api.listJobSearches });
  const search = saved.data ?? null;

  // When opening a saved search, restore its preferences into the form.
  useEffect(() => {
    if (!search) return;
    setRoles(search.params.target_roles);
    setLocation(search.params.location ?? "");
    setLevel((search.params.experience_level as ProfileLevel) ?? "");
    setWorkModes(search.params.work_modes as WorkMode[]);
    setEmployment(search.params.employment_types as EmploymentFilter[]);
    if (!profile) setProfile(search.profile);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search?.id]);

  const addRole = (r: string) => {
    const v = r.trim();
    if (v.length >= 2 && roles.length < 3 && !roles.some((x) => x.toLowerCase() === v.toLowerCase())) setRoles([...roles, v]);
    setRoleInput("");
  };

  const putSearch = (s: JobSearch) => {
    qc.setQueryData(["job-search", s.id], s);
    void qc.invalidateQueries({ queryKey: ["job-searches"] });
  };

  const analyse = async (signal: AbortSignal): Promise<JobProfile> => {
    if (profile && profileFor === resume) return profile;
    setStage("profile");
    const p = await api.jobProfile(resume, signal);
    setProfile(p);
    setProfileFor(resume);
    if (!level && p.experience_level !== "unknown") setLevel(p.experience_level);
    return p;
  };

  const runMatch = async (s: JobSearch, signal: AbortSignal) => {
    if (s.results.length === 0 || s.status === "matched") return s;
    setStage("match");
    const matched = await api.matchJobs(s.id, resume, signal);
    putSearch(matched);
    return matched;
  };

  const run = async (refresh = false) => {
    setRunError(null);
    if (resume.trim().length < minResume) {
      setResumeError(`Add your resume first — at least ${minResume} characters.`);
      return;
    }
    setResumeError(undefined);
    const controller = new AbortController();
    abortRef.current = controller;
    setSkipProfile(Boolean(profile && profileFor === resume));
    let current: Stage = "profile";
    try {
      const p = await analyse(controller.signal);
      current = "search";
      setStage("search");
      const s = await api.searchJobs(
        {
          profile: p,
          target_roles: roles,
          location: location.trim() || null,
          experience_level: level || null,
          work_modes: workModes,
          employment_types: employment,
          refresh,
        },
        controller.signal,
      );
      putSearch(s);
      if (s.id !== searchId) navigate(`/jobs/${s.id}`, { replace: Boolean(searchId) });
      current = "match";
      await runMatch(s, controller.signal);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setRunError({ stage: current, message: stageError(err) });
    } finally {
      setStage(null);
      abortRef.current = null;
    }
  };

  const retryMatch = async () => {
    if (!search) return;
    if (resume.trim().length < minResume) {
      setResumeError(`Add your resume in step 01 to evaluate matches.`);
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setRunError(null);
    setSkipProfile(true);
    try {
      await runMatch({ ...search, status: "discovered" }, controller.signal);
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) setRunError({ stage: "match", message: stageError(err) });
    } finally {
      setStage(null);
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
    setStage(null);
    toast.info("Cancelled. Any step the server had already finished is kept.");
  };

  // ---- dialogs
  const [dialog, setDialog] = useState<{ job: JobResult; mode: "prepare" | "rescore" } | null>(null);
  const prepare = useMutation({
    mutationFn: (v: { job: JobResult; role_type: RoleType; description: string; descriptionChanged: boolean }) =>
      api.prepareInterview(v.job.id, {
        resume_text: resume,
        role_type: v.role_type,
        ...(v.descriptionChanged ? { description: v.description } : {}),
      }),
    onSuccess: (out) => {
      qc.setQueryData(keys.session(out.session.id), out.session);
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      void qc.invalidateQueries({ queryKey: ["job-search", searchId] });
      setDialog(null);
      navigate(`/interviews/${out.session.id}`);
    },
  });
  const rescore = useMutation({
    mutationFn: (v: { job: JobResult; description: string }) => api.rematchJob(v.job.id, resume, v.description),
    onSuccess: (job) => {
      if (search) qc.setQueryData(["job-search", search.id], { ...search, results: search.results.map((r) => (r.id === job.id ? job : r)) });
      setDialog(null);
      toast.success("Re-scored with the full description");
    },
  });
  const removeSearch = useMutation({
    mutationFn: api.deleteJobSearch,
    onSuccess: (_, id) => {
      void qc.invalidateQueries({ queryKey: ["job-searches"] });
      if (id === searchId) navigate("/jobs");
    },
  });

  // ---- filters
  const [minScore, setMinScore] = useState(0);
  const [fMode, setFMode] = useState("");
  const [fType, setFType] = useState("");
  const [fLevel, setFLevel] = useState("");
  const [fLoc, setFLoc] = useState("");
  const [salaryOnly, setSalaryOnly] = useState(false);
  const [sort, setSort] = useState<"score" | "date" | "company">("score");

  const visible = useMemo(() => {
    if (!search) return [];
    const list = search.results.filter((r) => {
      if (minScore && (r.match?.score ?? -1) < minScore) return false;
      if (fMode && r.work_mode !== fMode) return false;
      if (fType && !(r.employment_type ?? "").toLowerCase().includes(fType)) return false;
      if (fLevel && r.experience_level !== fLevel) return false;
      if (fLoc && !(r.location ?? "").toLowerCase().includes(fLoc.toLowerCase())) return false;
      if (salaryOnly && r.salary_min === null && r.salary_max === null) return false;
      return true;
    });
    return [...list].sort((a, b) => {
      if (sort === "date") return (b.posted_at ?? "").localeCompare(a.posted_at ?? "");
      if (sort === "company") return (a.company ?? "~").localeCompare(b.company ?? "~");
      return (b.match?.score ?? -1) - (a.match?.score ?? -1) || a.rank - b.rank;
    });
  }, [search, minScore, fMode, fType, fLevel, fLoc, salaryOnly, sort]);

  const busy = stage !== null;
  const needsResume = resume.trim().length < minResume;

  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        eyebrow="Job finder"
        title="Find roles that fit your resume."
        description="Upload your resume, set your preferences, and see real listings scored against your experience. Then prepare for any of them in one click."
      />

      {config.data && !enabled && (
        <Alert tone="warning" icon={<Info />} title="Live job search isn't set up on this server yet" className="mb-8">
          Listings come from a licensed job-search service, and its credentials haven't been configured. Nothing is shown
          rather than invented listings. Administrators: add ADZUNA_APP_ID and ADZUNA_APP_KEY to the backend configuration.
        </Alert>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void run(false);
        }}
        noValidate
      >
        <Step n="01" title="Your resume" hint="Upload a PDF or DOCX, paste the text, or reuse the resume from your latest interview.">
          <ResumeInput value={resume} onChange={setResume} error={resumeError} />
        </Step>

        <Step n="02" title="Your profile" hint="Extracted from the resume to suggest roles. Optional — searching runs this automatically.">
          {profile ? (
            <div className="space-y-3">
              <ProfileSummary profile={profile} onAddRole={addRole} />
              {profileFor && profileFor !== resume && (
                <p className="text-xs text-muted-foreground">Your resume has changed since this profile was extracted; it will be refreshed when you search.</p>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted-foreground">No profile yet. Analyse your resume to see suggested roles before you search.</p>
              <Button
                type="button"
                variant="outline"
                disabled={busy || needsResume}
                onClick={async () => {
                  const c = new AbortController();
                  abortRef.current = c;
                  setRunError(null);
                  setSkipProfile(false);
                  try {
                    await analyse(c.signal);
                  } catch (err) {
                    if (!(err instanceof DOMException && err.name === "AbortError")) setRunError({ stage: "profile", message: stageError(err) });
                  } finally {
                    setStage(null);
                  }
                }}
              >
                Analyse resume
              </Button>
            </div>
          )}
        </Step>

        <Step n="03" title="Preferences" hint="Leave target roles empty to use the suggested roles. Only these keywords and your location are sent to the job-search service.">
          <div className="grid gap-6 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="jf-role">Target roles (up to 3)</Label>
              <div className="flex flex-wrap items-center gap-2 border border-input bg-card p-2 focus-within:ring-2 focus-within:ring-ring">
                {roles.map((r) => (
                  <span key={r} className="inline-flex items-center gap-1.5 bg-foreground px-2.5 py-1 text-sm text-background">
                    {r}
                    <button type="button" onClick={() => setRoles(roles.filter((x) => x !== r))} aria-label={`Remove ${r}`} className="opacity-80 transition-opacity hover:opacity-100">
                      <X className="size-3.5" />
                    </button>
                  </span>
                ))}
                {roles.length < 3 && (
                  <input
                    id="jf-role"
                    value={roleInput}
                    onChange={(e) => setRoleInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === ",") {
                        e.preventDefault();
                        addRole(roleInput);
                      }
                    }}
                    onBlur={() => roleInput && addRole(roleInput)}
                    placeholder={roles.length ? "Add another" : "e.g. Junior Data Engineer — press Enter"}
                    maxLength={80}
                    className="min-w-[12rem] flex-1 bg-transparent px-2 py-1.5 text-sm outline-none"
                  />
                )}
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="jf-loc">Location</Label>
              <Input id="jf-loc" value={location} onChange={(e) => setLocation(e.target.value)} placeholder="e.g. Noida" maxLength={100} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jf-level">Experience level</Label>
              <Select id="jf-level" value={level} onChange={(e) => setLevel(e.target.value as ProfileLevel | "")}>
                <option value="">Any</option>
                {Object.entries(LEVEL_LABELS)
                  .filter(([k]) => k !== "unknown")
                  .map(([k, l]) => (
                    <option key={k} value={k}>
                      {l}
                    </option>
                  ))}
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Work arrangement</Label>
              <Checks name="Work arrangement" options={WORK_MODE_LABELS} value={workModes} onChange={setWorkModes} />
            </div>
            <div className="space-y-2">
              <Label>Employment type (optional)</Label>
              <Checks name="Employment type" options={EMPLOYMENT_LABELS} value={employment} onChange={setEmployment} />
            </div>
          </div>
        </Step>

        <div className="flex flex-col gap-4 border-t border-foreground pt-8 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-xl text-xs text-muted-foreground">
            Listings come from a third-party job-search service and don't cover every job board. Match scores are AI estimates
            of how your resume aligns with each listing — not your chance of being hired.
          </p>
          <Button type="submit" size="lg" disabled={busy || !enabled}>
            <Search /> Find jobs
          </Button>
        </div>
      </form>

      <div className="mt-10 space-y-6">
        {stage && <Progress stage={stage} skipProfile={skipProfile} onCancel={cancel} />}

        {runError && (
          <Alert
            tone="error"
            icon={<AlertCircle className="text-destructive" />}
            title={`${STAGES.find((s) => s.key === runError.stage)?.label} failed`}
            action={
              <Button size="sm" variant="outline" onClick={() => (runError.stage === "match" && search ? retryMatch() : run(false))}>
                Try again
              </Button>
            }
          >
            {runError.message} Your inputs are still here.
          </Alert>
        )}

        {searchId && saved.isLoading && <Skeleton className="h-64" />}
        {searchId && saved.isError && <ErrorState error={saved.error} onRetry={() => saved.refetch()} action={<Button asChild variant="ghost" size="sm"><Link to="/jobs">Start a new search</Link></Button>} />}

        {search && (
          <section aria-labelledby="results-heading" className="space-y-6">
            <div className="flex flex-col gap-4 border-t border-foreground pt-6 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <p className="eyebrow text-foreground">Results</p>
                <h2 id="results-heading" className="display mt-3 text-[2.4rem]">
                  {search.results.length} {search.results.length === 1 ? "listing" : "listings"}
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Searched “{search.queries.join("”, “")}”{search.params.location ? ` in ${search.params.location}` : ""} ·{" "}
                  {formatDate(search.created_at, { dateStyle: "medium", timeStyle: "short" })}
                  {search.rejected > 0 && ` · ${search.rejected} listing(s) skipped for invalid links`}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                {search.attribution && <SourceAttribution {...search.attribution} />}
                <Button variant="outline" size="sm" onClick={() => run(true)} disabled={busy || !enabled}>
                  <RefreshCw /> Search again
                </Button>
              </div>
            </div>

            {search.cached && <Alert tone="info">Showing saved results from {formatDate(search.created_at, { timeStyle: "short", dateStyle: "medium" })} to avoid repeating the same search. Use “Search again” for fresh listings.</Alert>}
            {search.warnings.map((w) => (
              <Alert key={w} tone="warning">{w}</Alert>
            ))}
            {search.status === "match_failed" && !stage && (
              <Alert tone="error" title="Match evaluation failed" action={<Button size="sm" variant="outline" onClick={retryMatch}>Retry evaluation</Button>}>
                {search.match_error} The listings below are still available.
              </Alert>
            )}
            {search.status === "discovered" && search.results.length > 0 && !stage && (
              <Alert tone="info" title="Not scored yet" action={<Button size="sm" variant="outline" onClick={retryMatch}>Evaluate matches</Button>}>
                {needsResume ? "Add your resume in step 01 to score these listings." : "Score these listings against your resume."}
              </Alert>
            )}

            {search.results.length === 0 ? (
              <EmptyState
                icon={<Search />}
                title="No listings found"
                description="Try a broader role title, a nearby city, or fewer filters. The job-search service may not cover every role or location."
              />
            ) : (
              <>
                <div className="grid gap-3 border border-foreground p-4 sm:grid-cols-2 lg:grid-cols-4" role="group" aria-label="Filter and sort results">
                  <Select aria-label="Minimum match score" value={minScore} onChange={(e) => setMinScore(Number(e.target.value))}>
                    <option value={0}>Any score</option>
                    <option value={35}>35+ Partial</option>
                    <option value={55}>55+ Good</option>
                    <option value={75}>75+ Strong</option>
                  </Select>
                  <Input aria-label="Filter by location" placeholder="Location" value={fLoc} onChange={(e) => setFLoc(e.target.value)} />
                  <Select aria-label="Filter by level" value={fLevel} onChange={(e) => setFLevel(e.target.value)}>
                    <option value="">Any level</option>
                    {["intern", "junior", "mid", "senior", "lead"].map((l) => (
                      <option key={l} value={l}>{LEVEL_LABELS[l]}</option>
                    ))}
                  </Select>
                  <Select aria-label="Filter by employment type" value={fType} onChange={(e) => setFType(e.target.value)}>
                    <option value="">Any type</option>
                    <option value="full-time">Full-time</option>
                    <option value="part-time">Part-time</option>
                    <option value="contract">Contract</option>
                    <option value="permanent">Permanent</option>
                  </Select>
                  <Select aria-label="Filter by work arrangement" value={fMode} onChange={(e) => setFMode(e.target.value)}>
                    <option value="">Any arrangement</option>
                    {Object.entries(WORK_MODE_LABELS).map(([k, l]) => (
                      <option key={k} value={k}>{l}</option>
                    ))}
                  </Select>
                  <label className="flex h-11 cursor-pointer items-center gap-2 border border-input px-3 text-sm">
                    <input type="checkbox" checked={salaryOnly} onChange={(e) => setSalaryOnly(e.target.checked)} className="accent-foreground" />
                    Salary listed
                  </label>
                  <Select aria-label="Sort results" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
                    <option value="score">Best match</option>
                    <option value="date">Newest</option>
                    <option value="company">Company A–Z</option>
                  </Select>
                </div>
                <p className="text-xs text-muted-foreground">
                  Left of each card: data from the listing. Right: AI analysis. Level and arrangement are read from the listing
                  text; listings that don't state them are hidden when you filter by them.
                </p>
                {visible.length === 0 ? (
                  <EmptyState title="No listings match these filters" description="Clear a filter to see more results." />
                ) : (
                  <div className="space-y-6">
                    {visible.map((job) => (
                      <JobCard key={job.id} job={job} attribution={search.attribution} onPrepare={(j) => { prepare.reset(); setDialog({ job: j, mode: "prepare" }); }} onRescore={(j) => { rescore.reset(); setDialog({ job: j, mode: "rescore" }); }} />
                    ))}
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {!searchId && (recent.data?.length ?? 0) > 0 && (
          <section className="border-t border-foreground pt-6" aria-labelledby="recent-heading">
            <p id="recent-heading" className="eyebrow text-foreground">Recent searches</p>
            <ul className="mt-4 divide-y border-y">
              {recent.data!.slice(0, 8).map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-4 py-3">
                  <Link to={`/jobs/${s.id}`} className="min-w-0 flex-1 transition-all duration-200 hover:underline">
                    <span className="block truncate text-[15px] font-semibold">{s.queries.join(" · ")}</span>
                    <span className="text-xs text-muted-foreground">
                      {s.params.location ?? "Any location"} · {s.result_count} listings · {formatDate(s.created_at)}
                    </span>
                  </Link>
                  <Button variant="ghost" size="icon" aria-label={`Delete search ${s.queries.join(", ")}`} onClick={() => removeSearch.mutate(s.id)}>
                    <Trash2 />
                  </Button>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <JobActionDialog
        job={dialog?.job ?? null}
        mode={dialog?.mode ?? "prepare"}
        open={Boolean(dialog)}
        onOpenChange={(o) => !o && setDialog(null)}
        needsResume={needsResume}
        pending={prepare.isPending || rescore.isPending}
        error={prepare.isError ? errorMessage(prepare.error) : rescore.isError ? errorMessage(rescore.error) : null}
        onSubmit={(v) => {
          if (!dialog) return;
          if (dialog.mode === "prepare") prepare.mutate({ job: dialog.job, ...v });
          else rescore.mutate({ job: dialog.job, description: v.description });
        }}
      />
    </div>
  );
}
