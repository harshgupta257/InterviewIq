import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Check, Info, ShieldCheck, Wand2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { Step } from "@/components/FormStep";
import { PageHeader } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Alert, FieldError, Input, Label, Select, Textarea } from "@/components/ui/primitives";
import { keys, useConfig } from "@/hooks/queries";
import { api, ApiError, errorMessage } from "@/lib/api";
import { DIFFICULTY_OPTIONS, ROLE_OPTIONS, SENIORITY_OPTIONS } from "@/lib/constants";
import type { RoleType, SessionCreate } from "@/lib/types";
import { cn } from "@/lib/utils";

const DEFAULT_LIMITS = { resume_min: 150, resume_max: 15000, jd_min: 100, jd_max: 12000 };

function buildSchema(l: typeof DEFAULT_LIMITS) {
  return z.object({
    resume_text: z
      .string()
      .trim()
      .min(l.resume_min, `Paste at least ${l.resume_min} characters of your resume.`)
      .max(l.resume_max, `Keep the resume under ${l.resume_max.toLocaleString()} characters.`),
    jd_text: z
      .string()
      .trim()
      .min(l.jd_min, `Paste at least ${l.jd_min} characters of the job description.`)
      .max(l.jd_max, `Keep the job description under ${l.jd_max.toLocaleString()} characters.`),
    job_title: z.string().trim().min(2, "Enter the job title.").max(200),
    company: z.string().trim().max(200).optional(),
    role_type: z.enum(ROLE_OPTIONS.map((r) => r.value) as [RoleType, ...RoleType[]], { message: "Choose a role category." }),
    seniority_level: z.string().optional(),
    difficulty: z.string().optional(),
  });
}
type FormValues = z.infer<ReturnType<typeof buildSchema>>;

const STAGES = ["Analysing your experience", "Matching it against the job requirements", "Writing your eight questions"];

/** The fixed interview structure the backend generates (see app/ai/schemas.py). */
function plannedCategories(role: RoleType | undefined) {
  const design =
    role === "data_science" || role === "data_analytics"
      ? "Case study"
      : role === "other" || !role
        ? "System design or case study"
        : "System design";
  return [
    ["2", "Technical depth"],
    ["2", "Project deep-dives"],
    ["2", "Behavioural"],
    ["1", design],
    ["1", "Motivation & fit"],
  ];
}

function GenerationProgress({ onCancel, title, company, role }: { onCancel: () => void; title: string; company?: string; role?: RoleType }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const t = window.setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => window.clearInterval(t);
  }, []);
  const stage = elapsed < 8 ? 0 : elapsed < 20 ? 1 : 2;
  const roleLabel = ROLE_OPTIONS.find((r) => r.value === role)?.label;

  return (
    <div className="mx-auto grid max-w-4xl overflow-hidden rounded-lg border bg-card md:grid-cols-[1.1fr_0.9fr]">
      <div className="p-8 sm:p-10" aria-live="polite">
        <p className="eyebrow">Preparing your interview</p>
        <h1 className="display mt-3 text-[2.4rem] leading-[1.05]">
          {title}
          {company && <span className="text-muted-foreground"> at {company}</span>}
        </h1>
        {roleLabel && <p className="mt-2 text-sm text-muted-foreground">{roleLabel}</p>}

        <ol className="mt-9 space-y-5">
          {STAGES.map((s, i) => (
            <li key={s} className="flex items-center gap-4">
              <span
                className={cn(
                  "grid size-7 shrink-0 place-items-center border text-xs tabular-nums transition-colors duration-500",
                  i < stage && "border-primary bg-primary text-primary-foreground",
                  i === stage && "border-primary text-primary",
                  i > stage && "text-muted-foreground",
                )}
              >
                {i < stage ? <Check className="size-3.5" aria-hidden /> : i + 1}
              </span>
              <span className={cn("text-[15px] transition-colors", i <= stage ? "text-foreground" : "text-muted-foreground")}>
                {s}
                {i === stage && "…"}
              </span>
            </li>
          ))}
        </ol>

        <div className="mt-9 h-px overflow-hidden bg-secondary">
          <div className="h-full w-1/4 animate-indeterminate bg-primary" />
        </div>
        <div className="mt-4 flex items-center justify-between gap-4 text-xs text-muted-foreground">
          <span>
            {elapsed}s elapsed · usually under a minute, up to ~2 minutes when the AI service is busy
          </span>
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </div>
      <aside className="bg-ink p-8 text-paper sm:p-10">
        <p className="eyebrow text-taupe-light">Interview structure</p>
        <ul className="mt-6 divide-y divide-paper/10 border-y border-paper/10">
          {plannedCategories(role).map(([n, label]) => (
            <li key={label} className="flex items-baseline justify-between py-3.5 text-[14px]">
              <span className="text-paper/85">{label}</span>
              <span className="display text-2xl text-paper">{n}</span>
            </li>
          ))}
        </ul>
        <p className="mt-6 text-[13px] leading-relaxed text-paper/60">
          Every question is grounded in a detail from your resume, a requirement from the job, or a gap between the two.
        </p>
      </aside>
    </div>
  );
}

function CharCount({ value, max }: { value: string; max: number }) {
  const n = value?.length ?? 0;
  return (
    <span className={cn("text-xs tabular-nums", n > max ? "text-destructive" : "text-muted-foreground")}>
      {n.toLocaleString()} / {max.toLocaleString()}
    </span>
  );
}

export default function NewInterview() {
  const navigate = useNavigate();
  const location = useLocation();
  const qc = useQueryClient();
  const config = useConfig();
  const limits = config.data?.limits ?? DEFAULT_LIMITS;
  const schema = useMemo(() => buildSchema({ ...DEFAULT_LIMITS, ...limits }), [limits]);
  const abortRef = useRef<AbortController | null>(null);
  const prefill = (location.state as { prefill?: Partial<FormValues> } | null)?.prefill;

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { resume_text: "", jd_text: "", job_title: "", company: "", role_type: undefined, seniority_level: "", difficulty: "mixed", ...prefill },
  });
  const { errors } = form.formState;
  const [resume, jd] = form.watch(["resume_text", "jd_text"]);

  const samples = useMutation({
    mutationFn: api.samples,
    onSuccess: (s) => {
      form.reset({ ...form.getValues(), resume_text: s.resume_text, jd_text: s.jd_text, job_title: s.job_title, company: s.company, role_type: s.role_type });
      toast.success("Sample resume and job description loaded");
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const create = useMutation({
    mutationFn: (body: SessionCreate) => {
      abortRef.current = new AbortController();
      return api.createSession(body, abortRef.current.signal);
    },
    onSuccess: (session) => {
      qc.setQueryData(keys.session(session.id), session);
      void qc.invalidateQueries({ queryKey: ["sessions"] });
      void qc.invalidateQueries({ queryKey: ["analytics"] });
      navigate(`/interviews/${session.id}`, { replace: true });
    },
  });

  const onSubmit = form.handleSubmit((v) => {
    create.mutate({
      resume_text: v.resume_text,
      jd_text: v.jd_text,
      job_title: v.job_title,
      company: v.company || null,
      role_type: v.role_type,
      seniority_level: (v.seniority_level || null) as SessionCreate["seniority_level"],
      difficulty: (v.difficulty || null) as SessionCreate["difficulty"],
    });
  });

  const cancel = () => {
    abortRef.current?.abort();
    create.reset();
    toast.info("Generation cancelled. If the server had already finished, the session will appear in your history.");
  };

  if (create.isPending) {
    const v = form.getValues();
    return (
      <div className="py-4 lg:py-10">
        <GenerationProgress onCancel={cancel} title={v.job_title} company={v.company || undefined} role={v.role_type} />
      </div>
    );
  }

  const createError = create.error && !(create.error instanceof DOMException) ? create.error : null;

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        eyebrow="New interview"
        title="Set up your interview."
        description="Paste your resume and the job description. We'll generate eight questions grounded in both."
        actions={
          <Button variant="outline" size="sm" onClick={() => samples.mutate()} loading={samples.isPending}>
            {!samples.isPending && <Wand2 />} Load sample data
          </Button>
        }
      />

      {createError && (
        <Alert
          tone="error"
          icon={<AlertCircle className="text-destructive" />}
          title="We couldn't create your interview"
          className="mb-6"
          action={
            <Button size="sm" variant="outline" onClick={onSubmit}>
              Try again
            </Button>
          }
        >
          {errorMessage(createError)}
          {createError instanceof ApiError && createError.code === "rate_limited" ? "" : " Nothing was saved; your inputs are still here."}
        </Alert>
      )}

      <form onSubmit={onSubmit} noValidate>
        <Step n="01" title="Your resume" hint="Include roles, projects, tools and results. Contact details are removed before AI processing.">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="resume_text">Resume (plain text) *</Label>
              <CharCount value={resume} max={limits.resume_max} />
            </div>
            <Textarea
              id="resume_text"
              className="min-h-[260px] text-[14px]"
              placeholder={"Paste your resume as plain text, e.g.\n\nSoftware Engineer, Acme (2022–present)\n- Built a FastAPI service for document processing…"}
              aria-invalid={!!errors.resume_text}
              aria-describedby="resume-error"
              {...form.register("resume_text")}
            />
            <FieldError id="resume-error" message={errors.resume_text?.message} />
          </div>
        </Step>

        <Step n="02" title="The job description" hint="The full posting works best. Responsibilities and requirements matter most.">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="jd_text">Job description *</Label>
              <CharCount value={jd} max={limits.jd_max} />
            </div>
            <Textarea
              id="jd_text"
              className="min-h-[220px] text-[14px]"
              placeholder={"Paste the full job posting, e.g.\n\nResponsibilities\n- Design reliable production APIs…\n\nRequirements\n- 3+ years with Python…"}
              aria-invalid={!!errors.jd_text}
              aria-describedby="jd-error"
              {...form.register("jd_text")}
            />
            <FieldError id="jd-error" message={errors.jd_text?.message} />
          </div>
        </Step>

        <Step n="03" title="Role details" hint="Seniority is inferred from both documents unless you choose one. Every interview has eight questions.">
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="job_title">Target job title *</Label>
              <Input id="job_title" placeholder="e.g. Backend Engineer" aria-invalid={!!errors.job_title} {...form.register("job_title")} />
              <FieldError message={errors.job_title?.message} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="company">
                Company <span className="font-normal text-muted-foreground">(optional)</span>
              </Label>
              <Input id="company" placeholder="e.g. Contoso" {...form.register("company")} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role_type">Role category *</Label>
              <Select id="role_type" aria-invalid={!!errors.role_type} defaultValue="" {...form.register("role_type")}>
                <option value="" disabled>
                  Select a category
                </option>
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
              <FieldError message={errors.role_type?.message} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="seniority_level">Seniority</Label>
              <Select id="seniority_level" {...form.register("seniority_level")}>
                <option value="">Infer from my resume and the job</option>
                {SENIORITY_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="difficulty">Difficulty</Label>
              <Select id="difficulty" className="sm:max-w-xs" {...form.register("difficulty")}>
                {DIFFICULTY_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </Step>

        <div className="space-y-5 border-t pt-8">
          <Alert tone="info" icon={<ShieldCheck />}>
            Your resume, the job description and your answers are sent to{" "}
            {config.data?.ai_is_demo ? "the offline demo engine (no external AI)" : "the configured AI provider"} to generate
            questions and feedback. Don't include information you aren't comfortable sharing.
          </Alert>
          <div className="flex flex-col-reverse items-stretch gap-3 sm:flex-row sm:items-center sm:justify-end">
            {Object.keys(errors).length > 0 && (
              <p className="flex items-center gap-1.5 text-xs text-destructive sm:mr-auto" role="alert">
                <Info className="size-3.5" aria-hidden /> Fix the highlighted fields to continue.
              </p>
            )}
            <Button type="button" variant="ghost" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button type="submit" size="lg">
              Generate my interview
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}
