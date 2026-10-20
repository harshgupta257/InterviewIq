import { ArrowRight, Check, FileSearch, ListChecks, PenLine, Plus } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { SwissComposition } from "@/components/brand";
import { PublicLayout } from "@/components/layout";
import { Reveal } from "@/components/Reveal";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/** Section heading on the 12-column grid: index + label on the left, title on the right. */
function SectionHead({ index, label, title, children }: { index: string; label: string; title: ReactNode; children?: ReactNode }) {
  return (
    <div className="grid gap-6 border-t border-foreground pt-6 lg:grid-cols-12 lg:gap-8">
      <p className="eyebrow text-foreground lg:col-span-3">
        <span className="tabular-nums">{index}</span> — {label}
      </p>
      <div className="lg:col-span-9">
        <h2 className="display text-[2.6rem] sm:text-[3.6rem] lg:text-[4.2rem]">{title}</h2>
        {children && <div className="mt-6 max-w-2xl text-[17px] leading-relaxed text-muted-foreground">{children}</div>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ hero */

function Hero() {
  return (
    <section id="top" className="border-b border-foreground">
      <div className="container grid gap-12 py-16 lg:grid-cols-12 lg:gap-8 lg:py-24">
        <div className="flex flex-col justify-between gap-12 lg:col-span-7">
          <div>
            <p className="eyebrow animate-fade-up text-foreground">Interview practice / Est. 2026</p>
            <h1 className="display mt-8 animate-fade-up text-[3.4rem] [animation-delay:80ms] sm:text-[5rem] lg:text-[6.4rem]">
              Walk into every interview <em>prepared.</em>
            </h1>
          </div>
          <div className="grid animate-fade-up gap-8 [animation-delay:160ms] sm:grid-cols-12">
            <p className="text-[17px] leading-relaxed text-muted-foreground sm:col-span-8">
              Paste your resume and the job you want. InterviewIQ writes eight questions grounded in your real
              experience, scores each answer on four clear criteria, and tells you the one thing to fix next.
            </p>
            <div className="flex flex-col gap-3 sm:col-span-12 sm:flex-row">
              <Button asChild size="lg">
                <Link to="/signup">
                  Start practising <ArrowRight />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <a href="#how-it-works">See how it works</a>
              </Button>
            </div>
          </div>
        </div>
        <div className="animate-fade-up [animation-delay:240ms] lg:col-span-5">
          <SwissComposition className="text-foreground" />
        </div>
      </div>

      {/* Fact strip */}
      <div className="border-t border-foreground">
        <dl className="container grid grid-cols-2 lg:grid-cols-4">
          {[
            ["08", "Questions per interview, each tied to your resume or the role"],
            ["04", "Scoring criteria: clarity, specificity, results, relevance"],
            ["1–5", "Integer scale, with a written reason for every score"],
            ["01", "Clear next step after every answer"],
          ].map(([n, l], i) => (
            <div
              key={l}
              className={cn(
                "py-8 pr-6",
                i % 2 === 1 && "border-l border-foreground pl-6",
                i >= 2 && "border-t border-foreground lg:border-t-0",
                i === 2 && "lg:border-l lg:pl-6",
              )}
            >
              <dt className="sr-only">{l}</dt>
              <dd className="display text-5xl tabular-nums">{n}</dd>
              <dd className="mt-3 max-w-[16rem] text-sm leading-snug text-muted-foreground">{l}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}

/* --------------------------------------------------------------- features */

const FEATURES = [
  {
    icon: FileSearch,
    title: "Questions from your experience",
    body: "Each question names a real project, tool or requirement — or asks honestly about a gap between your resume and the role. Nothing generic, nothing you haven't done.",
  },
  {
    icon: ListChecks,
    title: "Scoring you can read",
    body: "Clarity, specificity, result orientation and relevance, each scored 1–5 with a reason that quotes your answer. The overall percentage is simple arithmetic, never a black box.",
  },
  {
    icon: PenLine,
    title: "A stronger version of your answer",
    body: "See your answer rewritten using only facts you supplied. Where a detail is missing you get a marked placeholder, not an invented achievement.",
  },
];

function Features() {
  return (
    <section id="features" className="scroll-mt-16">
      <div className="container py-20 lg:py-28">
        <Reveal>
          <SectionHead index="01" label="Features" title={<>Three things it does. <em>Properly.</em></>} />
        </Reveal>
        <div className="mt-14 grid border-l border-t border-foreground md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, body }, i) => (
            <Reveal key={title} delay={i * 80} className="border-b border-r border-foreground">
              <div className="group flex h-full flex-col p-8 transition-all duration-200 hover:bg-foreground hover:text-background">
              <div className="flex items-start justify-between">
                <span className="display text-4xl tabular-nums">0{i + 1}</span>
                <Icon className="size-7" strokeWidth={1.5} aria-hidden />
              </div>
              <h3 className="mt-16 text-xl font-bold tracking-[-0.02em]">{title}</h3>
              <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground transition-colors duration-200 group-hover:text-background">{body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ----------------------------------------------------------- how it works */

const STEPS = [
  ["Paste", "Your resume and the job description. Contact details are stripped before processing."],
  ["Answer", "Eight questions, one at a time. Drafts save as you type; progress survives a refresh."],
  ["Improve", "Read the scores and reasons, compare with a stronger example, then practise again."],
];

function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-16 bg-beige text-ink">
      <div className="container py-20 lg:py-28">
        <Reveal>
          <div className="grid gap-6 border-t border-ink pt-6 lg:grid-cols-12 lg:gap-8">
            <p className="eyebrow text-ink lg:col-span-3">02 — How it works</p>
            <h2 className="display text-[2.6rem] sm:text-[3.6rem] lg:col-span-9 lg:text-[4.2rem]">
              From resume to rehearsal <em>in three steps.</em>
            </h2>
          </div>
        </Reveal>
        <ol className="mt-14 grid gap-px bg-ink md:grid-cols-3">
          {STEPS.map(([t, d], i) => (
            <Reveal as="li" key={t} delay={i * 80} className="bg-beige p-8 md:min-h-[15rem]">
              <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink">Step {i + 1}</p>
              <p className="display mt-6 text-[2.8rem]">{t}.</p>
              <p className="mt-4 max-w-xs text-[15px] leading-relaxed text-ink/80">{d}</p>
            </Reveal>
          ))}
        </ol>

        {/* A real product artifact instead of decoration. */}
        <Reveal id="rubric" className="mt-16 grid scroll-mt-24 border border-ink bg-paper lg:grid-cols-12">
          <div className="border-b border-ink p-8 lg:col-span-7 lg:border-b-0 lg:border-r">
            <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink">Question 3 of 8 — Project deep-dive</p>
            <p className="mt-6 text-2xl font-semibold leading-snug tracking-[-0.02em]">
              “Your resume mentions a FastAPI document-processing service. How did you handle validation, failures and
              reliability — and what would you change before production?”
            </p>
            <p className="mt-6 text-sm text-ink/75">Based on — Resume: FastAPI service · Job description: reliable production APIs</p>
          </div>
          <div className="p-8 lg:col-span-5">
            <div className="flex items-baseline justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-eyebrow text-ink">Evaluation</p>
              <p className="display text-6xl tabular-nums">
                80<span className="text-2xl font-normal">%</span>
              </p>
            </div>
            <ul className="mt-6 divide-y divide-ink/20 border-y border-ink/20">
              {(
                [
                  ["Clarity", 4],
                  ["Specificity", 3],
                  ["Result orientation", 4],
                  ["Relevance", 5],
                ] as const
              ).map(([l, n]) => (
                <li key={l} className="flex items-center justify-between py-3 text-sm">
                  <span>{l}</span>
                  <span className="flex items-center gap-3">
                    <span className="flex gap-1" aria-hidden>
                      {[1, 2, 3, 4, 5].map((k) => (
                        <span key={k} className={cn("h-2 w-4", k <= n ? "bg-ink" : "bg-beige-300")} />
                      ))}
                    </span>
                    <span className="w-8 text-right font-semibold tabular-nums">{n}/5</span>
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-6 border-l-2 border-taupe pl-4 text-sm leading-relaxed">
              <span className="font-semibold">Next step:</span> describe one concrete failure you handled and how you detected it.
            </p>
            <p className="mt-4 text-xs text-ink/70">Example output.</p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* ------------------------------------------------- testimonials (honest) */

const SAMPLES = [
  {
    category: "Behavioural",
    score: 55,
    quote: "You described the disagreement clearly, but the outcome is missing. Say what was decided and what changed as a result.",
    dimension: "Result orientation · 2/5",
  },
  {
    category: "Technical depth",
    score: 75,
    quote: "Good use of a concrete example with the window function. You didn't explain how you verified correctness — add the check you ran.",
    dimension: "Specificity · 4/5",
  },
  {
    category: "Motivation & fit",
    score: 85,
    quote: "You tied the role's focus on reliable APIs to your FastAPI work and named a gap you want to grow into. Specific and honest.",
    dimension: "Relevance · 5/5",
  },
];

function Testimonials() {
  return (
    <section id="feedback" className="scroll-mt-16">
      <div className="container py-20 lg:py-28">
        <Reveal>
          <SectionHead index="03" label="Feedback, verbatim" title={<>What the feedback <em>actually says.</em></>}>
            InterviewIQ is new, so instead of customer quotes, here is the kind of feedback it writes. Every remark points
            at something specific in the answer.
          </SectionHead>
        </Reveal>
        <div className="mt-14 grid gap-10 md:grid-cols-3 md:gap-8">
          {SAMPLES.map((s, i) => (
            <Reveal as="figure" key={s.category} delay={i * 80} className="flex flex-col border-t-2 border-foreground pt-6">
              <div className="flex items-baseline justify-between">
                <p className="eyebrow text-foreground">{s.category}</p>
                <p className="text-sm font-semibold tabular-nums">{s.score}%</p>
              </div>
              <blockquote className="mt-6 flex-1 text-xl font-medium leading-snug tracking-[-0.015em]">“{s.quote}”</blockquote>
              <figcaption className="mt-8 flex flex-wrap items-center justify-between gap-2 border-t pt-4 text-xs text-muted-foreground">
                <span>{s.dimension}</span>
                <span>Example output — not a customer review</span>
              </figcaption>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- pricing */

type Tier = {
  name: string;
  price: string;
  note: string;
  features: string[];
  cta: { label: string; to: string };
  highlight?: boolean;
  footnote?: string;
};

const TIERS: Tier[] = [
  {
    name: "Demo",
    price: "$0",
    note: "No account needed",
    features: ["Explore with sample history", "Offline heuristic scoring (not AI)", "Data is temporary"],
    cta: { label: "Try the demo", to: "/login" },
    footnote: "Available when the demo is enabled on this deployment.",
  },
  {
    name: "Practice",
    price: "$0",
    note: "Free account",
    features: ["Unlimited interviews, 8 questions each", "Four-criterion scoring with reasons", "Stronger example answers", "Full history and progress"],
    cta: { label: "Create free account", to: "/signup" },
    highlight: true,
  },
  {
    name: "Self-hosted",
    price: "$0",
    note: "Your infrastructure",
    features: ["Run it with your own model API key", "Your own Supabase database", "Full control of your data"],
    cta: { label: "Get in touch", to: "/contact" },
  },
];

function Pricing() {
  return (
    <section id="pricing" className="scroll-mt-16 border-t border-foreground">
      <div className="container py-20 lg:py-28">
        <Reveal>
          <SectionHead index="04" label="Pricing" title={<>Free while we build it. <em>No card required.</em></>} />
        </Reveal>
        <div className="mt-14 grid border-l border-t border-foreground md:grid-cols-3">
          {TIERS.map((t, i) => (
            <Reveal
              key={t.name}
              delay={i * 80}
              className={cn("flex flex-col border-b border-r border-foreground p-8", t.highlight && "bg-foreground text-background")}
            >
              <div className="flex items-baseline justify-between gap-3">
                <h3 className="text-xl font-bold tracking-[-0.02em]">{t.name}</h3>
                {t.highlight && (
                  <span className="bg-taupe px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-ink">Recommended</span>
                )}
              </div>
              <p className="display mt-8 text-7xl tabular-nums">{t.price}</p>
              <p className={cn("mt-2 text-sm", t.highlight ? "text-background" : "text-muted-foreground")}>{t.note}</p>
              <ul className={cn("mt-8 flex-1 space-y-3 border-t pt-6 text-[15px]", t.highlight ? "border-background/40" : "border-border")}>
                {t.features.map((f) => (
                  <li key={f} className="flex gap-3">
                    <Check className="mt-0.5 size-4 shrink-0" aria-hidden />
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                asChild
                className={cn("mt-10 w-full", t.highlight && "bg-background text-foreground hover:bg-background/85")}
                variant={t.highlight ? "default" : "outline"}
              >
                <Link to={t.cta.to}>
                  {t.cta.label} <ArrowRight />
                </Link>
              </Button>
              {t.footnote && <p className="mt-3 text-xs text-muted-foreground">{t.footnote}</p>}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------- FAQ */

const FAQS = [
  [
    "How are the questions personalised?",
    "Your resume and the job description are analysed together. Each question is grounded in a specific project, skill or requirement — or in a gap between the two — and shows which details inspired it.",
  ],
  [
    "How is my answer scored?",
    "Clarity, specificity, result orientation and relevance are each scored from 1 to 5 with a written reason. The overall percentage is the average of the four, calculated by InterviewIQ itself.",
  ],
  [
    "Will the example answers make things up?",
    "No. Stronger examples use only facts from your resume and your own answer. Where a detail is missing you'll see a marked placeholder and a note on what to add.",
  ],
  [
    "What happens to my resume?",
    "Your resume, the job description and your answers are sent to the configured language-model provider to generate questions and feedback. Email addresses, phone numbers and links are removed first. You can delete your account and all data at any time.",
  ],
  [
    "Does it work for non-engineering roles?",
    "Yes. Data science, analytics and other roles get a case-study question in place of system design, and every question is tailored to the role you choose.",
  ],
];

function Faq() {
  return (
    <section id="faq" className="scroll-mt-16 border-t border-foreground">
      <div className="container grid gap-12 py-20 lg:grid-cols-12 lg:py-28">
        <Reveal className="lg:col-span-4">
          <p className="eyebrow text-foreground">05 — FAQ</p>
          <h2 className="display mt-6 text-[2.6rem] sm:text-[3.4rem]">Questions, answered.</h2>
        </Reveal>
        <Reveal delay={80} className="lg:col-span-8">
          <div className="border-t border-foreground">
            {FAQS.map(([q, a]) => (
              <details key={q} className="group border-b border-foreground">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-6 text-lg font-semibold tracking-[-0.015em] transition-all duration-200 hover:pl-2 [&::-webkit-details-marker]:hidden">
                  {q}
                  <Plus className="size-5 shrink-0 transition-transform duration-200 group-open:rotate-45" aria-hidden />
                </summary>
                <p className="max-w-2xl pb-7 text-[16px] leading-relaxed text-muted-foreground">{a}</p>
              </details>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- final CTA */

function FinalCta() {
  return (
    <section className="border-t border-foreground bg-beige text-ink">
      <div className="container grid items-end gap-10 py-20 lg:grid-cols-12 lg:py-28">
        <h2 className="display text-[3rem] sm:text-[4.6rem] lg:col-span-8 lg:text-[5.6rem]">
          Rehearse it <em>before it happens.</em>
        </h2>
        <div className="space-y-6 lg:col-span-4">
          <p className="text-[17px] leading-relaxed text-ink/80">Your first tailored interview takes a couple of minutes to set up.</p>
          <div className="flex flex-col items-start gap-5">
            <Button asChild size="lg" className="bg-ink text-paper hover:bg-ink/80">
              <Link to="/signup">
                Start practising <ArrowRight />
              </Link>
            </Button>
            <Link to="/login" className="link-arrow text-ink">
              I already have an account <ArrowRight className="size-4" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Landing() {
  return (
    <PublicLayout>
      <Hero />
      <Features />
      <HowItWorks />
      <Testimonials />
      <Pricing />
      <Faq />
      <FinalCta />
    </PublicLayout>
  );
}
