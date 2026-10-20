import { env } from "./env";
import type {
  AnalyticsOverview,
  Answer,
  Profile,
  ProgressPoint,
  PublicConfig,
  Samples,
  SessionCreate,
  SessionDetail,
  SessionList,
  SessionSort,
  JobProfile,
  JobResult,
  JobSearch,
  JobSearchCreate,
  JobSearchSummary,
  PrepareInterviewResult,
  ResumeExtract,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
    public requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isNetwork() {
    return this.status === 0;
  }
  get isAuth() {
    return this.status === 401;
  }
}

type TokenGetter = () => Promise<string | null>;
let getToken: TokenGetter = async () => null;
let onUnauthorized: () => void = () => undefined;

/** Wired up by AuthProvider so every request carries the current access token. */
export function configureApiAuth(getter: TokenGetter, unauthorized: () => void) {
  getToken = getter;
  onUnauthorized = unauthorized;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: FormData;
  auth?: boolean;
  signal?: AbortSignal;
}

async function request<T>(path: string, { method = "GET", body, form, auth = true, signal }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = await getToken();
    if (!token) {
      onUnauthorized();
      throw new ApiError(401, "unauthorized", "Please sign in to continue.");
    }
    headers.Authorization = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      headers,
      body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again.");
  }

  if (res.status === 204) return undefined as T;

  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    // Non-JSON response (e.g. proxy error page)
  }

  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string; details?: unknown; request_id?: string } })?.error;
    const apiError = new ApiError(
      res.status,
      err?.code ?? "http_error",
      err?.message ?? `Request failed (${res.status}).`,
      err?.details,
      err?.request_id,
    );
    if (res.status === 401 && auth) onUnauthorized();
    throw apiError;
  }
  return data as T;
}

export interface ListParams {
  q?: string;
  role_type?: string;
  status?: string;
  sort?: SessionSort;
  page?: number;
  page_size?: number;
}

function qs(params: object) {
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") search.set(k, String(v));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export const api = {
  config: () => request<PublicConfig>("/api/v1/config", { auth: false }),
  samples: () => request<Samples>("/api/v1/samples", { auth: false }),
  startDemo: () =>
    request<{ access_token: string; expires_at: string; user_id: string }>("/api/v1/demo/session", {
      method: "POST",
      auth: false,
    }),

  me: () => request<Profile>("/api/v1/me"),
  updateMe: (display_name: string | null) => request<Profile>("/api/v1/me", { method: "PATCH", body: { display_name } }),
  deleteMe: () => request<void>("/api/v1/me", { method: "DELETE" }),

  createSession: (body: SessionCreate, signal?: AbortSignal) =>
    request<SessionDetail>("/api/v1/sessions", { method: "POST", body, signal }),
  listSessions: (params: ListParams) => request<SessionList>(`/api/v1/sessions${qs(params)}`),
  getSession: (id: string) => request<SessionDetail>(`/api/v1/sessions/${encodeURIComponent(id)}`),
  deleteSession: (id: string) => request<void>(`/api/v1/sessions/${encodeURIComponent(id)}`, { method: "DELETE" }),

  submitAnswer: (sessionId: string, question_id: string, answer_text: string) =>
    request<Answer>(`/api/v1/sessions/${encodeURIComponent(sessionId)}/answers`, {
      method: "POST",
      body: { question_id, answer_text },
    }),
  retryEvaluation: (answerId: string) =>
    request<Answer>(`/api/v1/answers/${encodeURIComponent(answerId)}/retry-evaluation`, { method: "POST" }),
  rewrite: (answerId: string, regenerate = false) =>
    request<Answer>(`/api/v1/answers/${encodeURIComponent(answerId)}/rewrite${regenerate ? "?regenerate=true" : ""}`, {
      method: "POST",
    }),

  overview: () => request<AnalyticsOverview>("/api/v1/analytics/overview"),

  // ---- Job finder
  extractResume: (file: File, signal?: AbortSignal) => {
    const form = new FormData();
    form.append("file", file);
    return request<ResumeExtract>("/api/v1/resumes/extract", { method: "POST", form, signal });
  },
  jobProfile: (resume_text: string, signal?: AbortSignal) =>
    request<JobProfile>("/api/v1/jobs/profile", { method: "POST", body: { resume_text }, signal }),
  searchJobs: (body: JobSearchCreate, signal?: AbortSignal) =>
    request<JobSearch>("/api/v1/jobs/searches", { method: "POST", body, signal }),
  listJobSearches: () => request<JobSearchSummary[]>("/api/v1/jobs/searches"),
  getJobSearch: (id: string) => request<JobSearch>(`/api/v1/jobs/searches/${encodeURIComponent(id)}`),
  deleteJobSearch: (id: string) => request<void>(`/api/v1/jobs/searches/${encodeURIComponent(id)}`, { method: "DELETE" }),
  matchJobs: (id: string, resume_text: string, signal?: AbortSignal) =>
    request<JobSearch>(`/api/v1/jobs/searches/${encodeURIComponent(id)}/match`, { method: "POST", body: { resume_text }, signal }),
  rematchJob: (jobId: string, resume_text: string, description?: string) =>
    request<JobResult>(`/api/v1/jobs/${encodeURIComponent(jobId)}/match`, {
      method: "POST",
      body: { resume_text, ...(description ? { description } : {}) },
    }),
  prepareInterview: (jobId: string, body: { resume_text: string; role_type: string; description?: string; new_session?: boolean }) =>
    request<PrepareInterviewResult>(`/api/v1/jobs/${encodeURIComponent(jobId)}/prepare-interview`, { method: "POST", body }),
  progress: () => request<{ points: ProgressPoint[] }>("/api/v1/analytics/progress"),
};

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}
