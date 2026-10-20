// Mirrors backend/app/schemas. Keep in sync with the OpenAPI docs at /docs.

export type RoleType =
  | "software_engineering"
  | "data_engineering"
  | "data_science"
  | "data_analytics"
  | "ai_ml_engineering"
  | "forward_deployed_engineering"
  | "other";

export type Seniority = "intern" | "junior" | "mid" | "senior" | "staff" | "lead";
export type DifficultyPref = "easy" | "medium" | "hard" | "mixed";
export type EvaluationStatus = "pending" | "evaluating" | "completed" | "failed";
export type SessionSort = "date_desc" | "date_asc" | "score_desc" | "score_asc";

export interface Question {
  id: string;
  order_index: number;
  question_text: string;
  category: string;
  difficulty: string | null;
  why_this_question: string;
  source_context: string[];
  evaluation_focus: string[];
}

export interface DimensionScore {
  score: number;
  reason: string;
}

export interface Evaluation {
  clarity: DimensionScore;
  specificity: DimensionScore;
  result_orientation: DimensionScore;
  relevance: DimensionScore;
  overall_feedback: string;
  one_thing_to_fix: string;
  average: number;
  percentage: number;
  is_demo: boolean;
  model: string | null;
}

export interface Rewrite {
  improved_answer: string;
  improvements: string[];
  missing_information: string[];
  suggested_follow_up: string;
  generated_at: string | null;
  is_demo: boolean;
}

export interface Answer {
  id: string;
  question_id: string;
  session_id: string;
  answer_text: string;
  evaluation_status: EvaluationStatus;
  evaluation_error: string | null;
  evaluation: Evaluation | null;
  rewrite: Rewrite | null;
  answered_at: string | null;
  evaluated_at: string | null;
}

export interface SessionProgress {
  total_questions: number;
  answered_count: number;
  evaluated_count: number;
  failed_evaluations: number;
  current_question_index: number;
  is_complete: boolean;
}

export interface SessionSummary {
  id: string;
  job_title: string;
  company: string | null;
  role_type: RoleType;
  role_label: string;
  seniority_level: string | null;
  status: "in_progress" | "completed" | "failed";
  is_demo: boolean;
  created_at: string;
  completed_at: string | null;
  total_questions: number;
  answered_count: number;
  evaluated_count: number;
  average_score: number | null;
  completion_pct: number;
}

export interface SessionDetail extends SessionSummary {
  jd_text: string;
  resume_text: string;
  difficulty: string | null;
  analysis: Record<string, unknown> | null;
  ai_provider: string;
  ai_model: string;
  questions: Question[];
  answers: Answer[];
  progress: SessionProgress;
}

export interface SessionList {
  items: SessionSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface SessionCreate {
  resume_text: string;
  jd_text: string;
  job_title: string;
  company?: string | null;
  role_type: RoleType;
  seniority_level?: Seniority | null;
  difficulty?: DifficultyPref | null;
}

export interface AnalyticsOverview {
  total_sessions: number;
  completed_interviews: number;
  total_questions_answered: number;
  evaluated_answers: number;
  average_score: number | null;
  most_recent_session_score: number | null;
  most_recent_session_id: string | null;
  dimension_averages: Record<"clarity" | "specificity" | "result_orientation" | "relevance", number | null>;
  includes_demo_data: boolean;
}

export interface ProgressPoint {
  session_id: string;
  job_title: string;
  company: string | null;
  date: string;
  average_score: number;
  evaluated_count: number;
  is_demo: boolean;
}

export interface Profile {
  id: string;
  email: string | null;
  display_name: string | null;
  is_demo: boolean;
}

export interface PublicConfig {
  app_env: string;
  demo_mode: boolean;
  ai_provider: string;
  ai_model: string;
  ai_is_demo: boolean;
  supabase_auth: boolean;
  limits: Record<"resume_min" | "resume_max" | "jd_min" | "jd_max" | "answer_min" | "answer_max", number>;
  job_search: { enabled: boolean; provider: string; country: string | null; upload_max_mb: number };
}

export interface Samples {
  resume_text: string;
  jd_text: string;
  job_title: string;
  company: string;
  role_type: RoleType;
}

// ---- Job finder

export type WorkMode = "remote" | "hybrid" | "onsite";
export type EmploymentFilter = "full_time" | "part_time" | "contract" | "permanent";
export type ProfileLevel = Seniority | "unknown";

export interface ResumeExtract {
  text: string;
  file_type: "pdf" | "docx";
  pages: number | null;
  char_count: number;
  truncated: boolean;
  warnings: string[];
}

export interface JobProfile {
  summary: string;
  skills: string[];
  tools: string[];
  job_titles: string[];
  education: string[];
  certifications: string[];
  projects: string[];
  experience_level: ProfileLevel;
  years_experience: number | null;
  suggested_roles: string[];
  is_demo?: boolean;
}

export interface JobSearchCreate {
  profile: JobProfile;
  target_roles: string[];
  location: string | null;
  experience_level: ProfileLevel | null;
  work_modes: WorkMode[];
  employment_types: EmploymentFilter[];
  refresh?: boolean;
}

export interface JobMatch {
  score: number;
  label: string;
  confidence: "provisional" | "full";
  required_skills: string[];
  matched_skills: string[];
  missing_skills: string[];
  relevant_experience: string[];
  reasons: string[];
  improvements: string[];
  gaps: string[];
  description_sufficient: boolean;
  components: { skills: number | null; experience: number; role: number; responsibilities: number };
  scoring_version: string;
  model: string | null;
  is_demo: boolean;
  matched_at: string | null;
}

export interface JobResult {
  id: string;
  rank: number;
  title: string;
  company: string | null;
  location: string | null;
  work_mode: WorkMode | null;
  employment_type: string | null;
  experience_level: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  category: string | null;
  description: string | null;
  description_source: "listing_summary" | "user_provided";
  url: string;
  source: string;
  posted_at: string | null;
  retrieved_at: string;
  match: JobMatch | null;
  interview_session_id: string | null;
}

export interface JobSearchParams {
  target_roles: string[];
  location: string | null;
  experience_level: string | null;
  work_modes: string[];
  employment_types: string[];
}

export interface JobSearch {
  id: string;
  created_at: string;
  expires_at: string;
  provider: string;
  attribution: { label: string; url: string } | null;
  params: JobSearchParams;
  queries: string[];
  profile: JobProfile;
  status: "discovered" | "matched" | "match_failed";
  match_error: string | null;
  total_found: number;
  rejected: number;
  cached: boolean;
  warnings: string[];
  results: JobResult[];
}

export interface JobSearchSummary {
  id: string;
  created_at: string;
  queries: string[];
  params: JobSearchParams;
  status: string;
  result_count: number;
}

export interface PrepareInterviewResult {
  job_id: string;
  created: boolean;
  session: SessionDetail;
}
