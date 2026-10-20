import { ArrowRight, Mail } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { PublicLayout } from "@/components/layout";
import { site } from "@/lib/site";

const UPDATED = "13 October 2026";

function DocPage({ label, title, intro, children }: { label: string; title: string; intro: ReactNode; children: ReactNode }) {
  return (
    <PublicLayout>
      <article className="container grid gap-12 py-16 lg:grid-cols-12 lg:py-24">
        <header className="lg:col-span-4">
          <p className="eyebrow text-foreground">{label}</p>
          <h1 className="display mt-6 text-[3rem] sm:text-[4rem]">{title}</h1>
          <p className="mt-6 text-sm text-muted-foreground">Last updated {UPDATED}</p>
        </header>
        <div className="space-y-10 border-t border-foreground pt-8 lg:col-span-8">
          <p className="text-[18px] leading-relaxed">{intro}</p>
          {children}
        </div>
      </article>
    </PublicLayout>
  );
}

function Section({ n, title, children }: { n: string; title: string; children: ReactNode }) {
  return (
    <section className="grid gap-4 border-t pt-8 sm:grid-cols-12">
      <p className="text-sm font-semibold tabular-nums sm:col-span-2">{n}</p>
      <div className="space-y-3 sm:col-span-10">
        <h2 className="text-xl font-bold tracking-[-0.02em]">{title}</h2>
        <div className="space-y-3 text-[16px] leading-relaxed text-muted-foreground">{children}</div>
      </div>
    </section>
  );
}

export function PrivacyPage() {
  return (
    <DocPage
      label="Legal — Privacy"
      title="Privacy policy"
      intro="InterviewIQ is an interview-practice tool. This page explains what we store, why, who processes it, and how to remove it."
    >
      <Section n="01" title="What we collect">
        <p>Your email address and password are handled by our authentication provider (Supabase Auth). We store an optional display name.</p>
        <p>
          When you practise, we store the resume text, job description, generated questions, your answers, their scores and
          feedback, and any example answers you request.
        </p>
        <p>
          For reliability and cost monitoring we record technical metadata about each AI request — operation type, duration,
          token counts and errors. These records contain no resume or answer text.
        </p>
      </Section>
      <Section n="02" title="How it is processed">
        <p>
          To generate questions and feedback, your resume, the job description and your answers are sent to the language-model
          provider configured for this service (for example Google Gemini or OpenAI). Email addresses, phone numbers and links are
          removed from your resume and the job description before they are sent.
        </p>
        <p>Application logs record identifiers, sizes and timings — never your resume, answers, passwords or access tokens.</p>
      </Section>
      <Section n="03" title="Who can see it">
        <p>
          Your sessions are visible only to you. Every request is checked against your account, and the database enforces
          row-level security so one user cannot read another user's data.
        </p>
        <p>We do not sell your data or use it for advertising.</p>
      </Section>
      <Section n="04" title="Deleting your data">
        <p>
          You can delete individual sessions from History, or delete your account under Settings. Account deletion removes your
          sessions, questions, answers, feedback, profile and usage records, and then your login.
        </p>
      </Section>
      <Section n="05" title="Contact">
        <p>
          Questions about this policy? <Link to="/contact" className="font-semibold text-foreground underline underline-offset-4">Contact us</Link>.
        </p>
      </Section>
    </DocPage>
  );
}

export function TermsPage() {
  return (
    <DocPage
      label="Legal — Terms"
      title="Terms of use"
      intro="By using InterviewIQ you agree to these terms. They are written to be short and readable."
    >
      <Section n="01" title="The service">
        <p>
          InterviewIQ generates practice interview questions from the resume and job description you provide, and gives
          automated feedback on your answers. It is a practice aid, not professional career, legal or hiring advice.
        </p>
      </Section>
      <Section n="02" title="Automated feedback">
        <p>
          Questions, scores and example answers are produced automatically and may be inaccurate or incomplete. Example answers
          are illustrations for learning; only present experience in a real interview that is genuinely yours.
        </p>
      </Section>
      <Section n="03" title="Your content">
        <p>
          You keep ownership of everything you submit. You confirm you have the right to submit it, and you allow us to process it
          only to provide the service, as described in the <Link to="/privacy" className="font-semibold text-foreground underline underline-offset-4">privacy policy</Link>.
        </p>
      </Section>
      <Section n="04" title="Acceptable use">
        <p>
          Don't attempt to access other users' data, overload the service, bypass rate limits, or submit content you don't have
          the right to share.
        </p>
      </Section>
      <Section n="05" title="Availability and changes">
        <p>
          The service is provided as is, may change, and may occasionally be unavailable — for example when the language-model
          provider is busy. We may update these terms; the date above shows the latest version.
        </p>
      </Section>
    </DocPage>
  );
}

export function ContactPage() {
  const github = site.social.find((s) => s.name === "GitHub");
  return (
    <DocPage label="Company — Contact" title="Contact" intro="Questions, feedback, or interest in a self-hosted setup — we'd like to hear from you.">
      {site.contactEmail ? (
        <a
          href={`mailto:${site.contactEmail}`}
          className="group flex items-center justify-between border border-foreground p-8 transition-all duration-200 hover:bg-foreground hover:text-background"
        >
          <span className="flex items-center gap-4">
            <Mail className="size-6" strokeWidth={1.5} aria-hidden />
            <span className="text-2xl font-bold tracking-[-0.02em]">{site.contactEmail}</span>
          </span>
          <ArrowRight className="size-5 transition-transform duration-200 group-hover:translate-x-1" aria-hidden />
        </a>
      ) : (
        <p className="border-l-2 border-taupe bg-secondary p-6 text-[16px] leading-relaxed">
          A contact address hasn't been published for this deployment yet.
          {github && (
            <>
              {" "}
              You can reach the project on{" "}
              <a href={github.href} target="_blank" rel="noopener noreferrer" className="font-semibold underline underline-offset-4">
                GitHub
              </a>
              .
            </>
          )}
        </p>
      )}
      <Section n="01" title="Account and data requests">
        <p>
          You can delete sessions or your entire account yourself under Settings — no request needed. See the{" "}
          <Link to="/privacy" className="font-semibold text-foreground underline underline-offset-4">privacy policy</Link> for details.
        </p>
      </Section>
    </DocPage>
  );
}
