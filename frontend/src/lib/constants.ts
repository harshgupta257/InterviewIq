import type { RoleType } from "./types";

export const ROLE_OPTIONS: { value: RoleType; label: string }[] = [
  { value: "software_engineering", label: "Software Engineering" },
  { value: "data_engineering", label: "Data Engineering" },
  { value: "data_science", label: "Data Science" },
  { value: "data_analytics", label: "Data Analytics" },
  { value: "ai_ml_engineering", label: "AI/ML Engineering" },
  { value: "forward_deployed_engineering", label: "Forward Deployed Engineering" },
  { value: "other", label: "Other" },
];

export const SENIORITY_OPTIONS = [
  { value: "intern", label: "Intern" },
  { value: "junior", label: "Junior" },
  { value: "mid", label: "Mid-level" },
  { value: "senior", label: "Senior" },
  { value: "staff", label: "Staff / Principal" },
  { value: "lead", label: "Lead / Manager" },
] as const;

export const DIFFICULTY_OPTIONS = [
  { value: "mixed", label: "Balanced mix" },
  { value: "easy", label: "Easier" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Challenging" },
] as const;

export const CATEGORY_LABELS: Record<string, string> = {
  technical: "Technical depth",
  behavioral: "Behavioral",
  project_deepdive: "Project deep-dive",
  system_design: "System design",
  motivation: "Motivation & fit",
  case_study: "Case study",
};

export const DIMENSIONS = [
  {
    key: "clarity",
    label: "Clarity",
    description: "Is the answer logically structured, understandable, and concise?",
  },
  {
    key: "specificity",
    label: "Specificity",
    description: "Concrete examples, technical details, evidence or relevant numbers, without invented facts.",
  },
  {
    key: "result_orientation",
    label: "Result orientation",
    description: "Outcomes, impact, lessons, or — for hypothetical questions — sound reasoning and trade-offs.",
  },
  {
    key: "relevance",
    label: "Relevance",
    description: "Does the answer address the actual question and the role's requirements?",
  },
] as const;

export type DimensionKey = (typeof DIMENSIONS)[number]["key"];
