import type { RoleType } from "./types";

/** Resume text for the current tab only. Kept in memory, never written to browser storage. */
let currentResume = "";
export const resumeMemory = {
  get: () => currentResume,
  set: (text: string) => {
    currentResume = text;
  },
};

export const WORK_MODE_LABELS: Record<string, string> = { remote: "Remote", hybrid: "Hybrid", onsite: "On-site" };
export const EMPLOYMENT_LABELS: Record<string, string> = {
  full_time: "Full-time",
  part_time: "Part-time",
  contract: "Contract",
  permanent: "Permanent",
};
export const LEVEL_LABELS: Record<string, string> = {
  intern: "Intern",
  junior: "Junior / entry",
  mid: "Mid-level",
  senior: "Senior",
  staff: "Staff",
  lead: "Lead",
  unknown: "Not sure",
};

/** Best-guess interview role category from a job title; the user can change it. */
export function guessRoleType(title: string): RoleType {
  const t = title.toLowerCase();
  if (/forward[- ]deployed/.test(t)) return "forward_deployed_engineering";
  if (/data engineer|etl|analytics engineer/.test(t)) return "data_engineering";
  if (/data scien/.test(t)) return "data_science";
  if (/analyst|business intelligence|\bbi\b/.test(t)) return "data_analytics";
  if (/machine learning|\bml\b|\bai\b|deep learning|llm|nlp/.test(t)) return "ai_ml_engineering";
  if (/engineer|developer|programmer|software|sde|devops|backend|frontend|full[- ]?stack/.test(t)) return "software_engineering";
  return "other";
}

export function formatSalary(min: number | null, max: number | null, currency: string | null): string | null {
  if (min === null && max === null) return null;
  const fmt = (v: number) =>
    new Intl.NumberFormat(undefined, {
      style: currency ? "currency" : "decimal",
      currency: currency ?? undefined,
      maximumFractionDigits: 0,
      notation: v >= 100000 ? "compact" : "standard",
    }).format(v);
  if (min !== null && max !== null && min !== max) return `${fmt(min)} – ${fmt(max)}`;
  return fmt((min ?? max) as number);
}
