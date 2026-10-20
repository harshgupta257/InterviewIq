# API reference

Interactive OpenAPI docs: `GET /docs` (Swagger) and `GET /openapi.json`.

Authenticated endpoints need `Authorization: Bearer <access token>` (Supabase or demo).
User identity always comes from the verified token, never from the body or query.

Errors share one envelope:

```json
{ "error": { "code": "validation_error", "message": "…", "request_id": "…", "details": [] } }
```

Every response carries `X-Request-ID`. You can send your own (8–64 alphanumeric/hyphen characters) to correlate logs.

| Method & path | Auth | Description | Notable responses |
|---|---|---|---|
| `GET /health` | – | Liveness + DB readiness. An AI outage does not mark it unhealthy. | 200 `{status, database, ai_provider}` |
| `GET /api/v1/config` | – | Public flags: demo mode, provider/model, input limits | 200 |
| `GET /api/v1/samples` | – | Fictional sample resume + JD | 200 |
| `POST /api/v1/demo/session` | – | Create an isolated demo account (DEMO_MODE only) | 201 token · 403 `demo_disabled` · 429 |
| `GET /api/v1/me` | ✔ | Profile | 200 |
| `PATCH /api/v1/me` | ✔ | Update `display_name` | 200 |
| `DELETE /api/v1/me` | ✔ | Delete all data, then the auth user | 204 · 400 `auth_deletion_unavailable` / `auth_deletion_failed` (data already deleted) |
| `POST /api/v1/sessions` | ✔ AI | Analyse resume + JD, generate and persist 8 questions | 201 `SessionDetail` · 422 · 429 · 502 `ai_unavailable` / `ai_invalid_output` · 503 `ai_quota_exceeded` |
| `GET /api/v1/sessions` | ✔ | `q`, `role_type`, `status`, `sort` (`date_desc`, `date_asc`, `score_desc`, `score_asc`), `page`, `page_size` (≤50) | 200 `SessionList` |
| `GET /api/v1/sessions/{id}` | ✔ | Session, questions, answers, progress | 200 · 404 |
| `DELETE /api/v1/sessions/{id}` | ✔ | Delete (cascades) | 204 · 404 |
| `POST /api/v1/sessions/{id}/answers` | ✔ AI | `{question_id, answer_text}`. Saves the answer first, then evaluates it | 201 new · 200 identical resubmit · 409 `answer_exists` / `out_of_order` / `evaluation_in_progress` · 429 |
| `GET /api/v1/sessions/{id}/answers` | ✔ | Answers with evaluations | 200 |
| `POST /api/v1/answers/{id}/retry-evaluation` | ✔ AI | Re-run a failed or stale evaluation (no duplicate rows) | 200 · 409 `already_evaluated` |
| `POST /api/v1/answers/{id}/rewrite?regenerate=false` | ✔ AI | Stronger example; cached unless `regenerate=true` | 200 · 502 |
| `GET /api/v1/analytics/overview` | ✔ | Totals, averages, most recent session score, dimension means | 200 |
| `GET /api/v1/analytics/progress` | ✔ | One point per session with evaluated answers (last 50) | 200 |

**Answer evaluation result.** If evaluation fails after an answer is submitted, the endpoint
still returns 201 with `evaluation_status: "failed"` and an `evaluation_error`. The answer is
kept, and `evaluation` is `null`, because scores are never invented.

**Score fields.** Each dimension carries a `score` (1–5) and a `reason`. `average` is the mean
of the four scores, and `percentage` is `average / 5 × 100`. The backend computes both.

## Job finder

| Method & path | Auth | Description | Notable responses |
|---|---|---|---|
| `POST /api/v1/resumes/extract` | ✔ | Multipart `file` (PDF/DOCX ≤ `RESUME_UPLOAD_MAX_MB`). Text extracted in memory, nothing stored | 200 · 422 `resume_unsupported_type` / `resume_corrupt` / `resume_no_text` (scanned) / `resume_encrypted` / `resume_too_large` |
| `POST /api/v1/jobs/profile` | ✔ AI | `{resume_text}` → skills-only profile + suggested roles | 200 · 502/503 AI errors · 429 |
| `POST /api/v1/jobs/searches` | ✔ | `{profile, target_roles[], location, experience_level, work_modes[], employment_types[], refresh}`. Cached per user | 201 (`cached: true` when reused) · 503 `job_search_not_configured` · 429 `job_search_quota_exceeded` / `rate_limited` · 502 `job_search_unavailable` |
| `GET /api/v1/jobs/searches` | ✔ | Recent searches | 200 |
| `GET /api/v1/jobs/searches/{id}` | ✔ | Search with listings and analysis | 200 · 404 |
| `DELETE /api/v1/jobs/searches/{id}` | ✔ | Delete a search and its listings | 204 · 404 |
| `POST /api/v1/jobs/searches/{id}/match` | ✔ AI | `{resume_text}` → one batched evaluation | 200 (`status: matched` or `match_failed`, listings kept) |
| `POST /api/v1/jobs/{job_id}/match` | ✔ AI | `{resume_text, description?}` re-score one listing, optionally with the full description | 200 · 404 |
| `POST /api/v1/jobs/{job_id}/prepare-interview` | ✔ AI | `{resume_text, role_type, description?, new_session?}` → creates (or reuses) an interview session | 200 `{created, session}` · 400 `job_description_insufficient` |
