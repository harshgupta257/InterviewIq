<a id="top"></a>

<div align="center">

<img src="docs/assets/banner.svg" alt="InterviewIQ: AI interview coach and resume-matched job finder" width="100%">

<br>

[![CI](https://github.com/harshgupta257/InterviewIq/actions/workflows/ci.yml/badge.svg)](https://github.com/harshgupta257/InterviewIq/actions/workflows/ci.yml)
![React](https://img.shields.io/badge/React_18-0d0221?style=for-the-badge&logo=react&logoColor=00f0ff)
![TypeScript](https://img.shields.io/badge/TypeScript-0d0221?style=for-the-badge&logo=typescript&logoColor=00f0ff)
![FastAPI](https://img.shields.io/badge/FastAPI-0d0221?style=for-the-badge&logo=fastapi&logoColor=39ff14)
![Python](https://img.shields.io/badge/Python_3.12-0d0221?style=for-the-badge&logo=python&logoColor=f9f002)
![Supabase](https://img.shields.io/badge/Supabase-0d0221?style=for-the-badge&logo=supabase&logoColor=39ff14)
![Gemini](https://img.shields.io/badge/Gemini-0d0221?style=for-the-badge&logo=googlegemini&logoColor=ff2a6d)
![Render](https://img.shields.io/badge/Render-0d0221?style=for-the-badge&logo=render&logoColor=f5f0ff)

**[`◆ FEATURES`](#features)** &nbsp;
**[`◆ JOB FINDER`](#job-finder)** &nbsp;
**[`◆ ARCHITECTURE`](#architecture)** &nbsp;
**[`◆ QUICK START`](#quick-start)** &nbsp;
**[`◆ DEPLOY`](#deploy)** &nbsp;
**[`◆ TESTS`](#tests)** &nbsp;
**[`◆ API`](docs/API.md)**

</div>

```console
$ interviewiq --boot
[ OK ] resume + job description ......... parsed
[ OK ] interview ......................... 8 questions generated, grounded in your experience
[ OK ] rubric ............................ clarity · specificity · result orientation · relevance
[ OK ] score ............................. computed by the backend, never by the model
[ OK ] job finder ........................ real listings, scored 0–100 against your resume
[ -- ] fabricated results ................ none. failures say so, and you can retry.
```

InterviewIQ turns a resume and a target job description into a tailored mock interview.
It writes **eight grounded questions** and scores each answer on a **transparent four-part
rubric**. Then it shows a stronger example answer and tracks your progress over time. The
**AI Job Finder** finds real listings that fit your resume and turns any of them into an
interview in one click.

<img src="docs/assets/stats.svg" alt="8 questions per session · 4 rubric dimensions · 0–100 job match · 128 backend tests · 0 fabricated scores" width="100%">

<img src="docs/assets/divider.svg" width="100%" alt="">

<a id="features"></a>

## `⟨01⟩` SYSTEM MODULES

<table>
<tr>
<td width="50%" valign="top">

### ▸ Tailored sessions
Resume + JD analysis, then **exactly 8** questions: 2 technical, 2 project deep-dive,
2 behavioral, 1 system design *or* case study, 1 motivation. Every question is schema
validated, with a bounded repair-retry loop.

</td>
<td width="50%" valign="top">

### ▸ Rubric evaluation
Four integer scores (1–5), each with a reason, plus overall feedback and *the one
thing to fix*. The percentage is `avg / 5 × 100`, **computed by the backend** and
never taken from the model.

</td>
</tr>
<tr>
<td valign="top">

### ▸ Interview workspace
One question at a time, answered in order. Drafts autosave locally. Progress is
restored from the database on refresh, and duplicate submits and multiple open tabs
are handled safely.

</td>
<td valign="top">

### ▸ Stronger answer
A STAR-shaped example (behavioral questions only), *What changed*, missing details
shown as `[placeholders]`, and a likely follow-up. It's saved and reused unless you
regenerate it.

</td>
</tr>
<tr>
<td valign="top">

### ▸ AI Job Finder
Upload a PDF/DOCX resume, set roles, location and preferences, and get **real
listings** with a 0–100 match score. Then **Prepare for interview** on any of them.

</td>
<td valign="top">

### ▸ Dashboard + history
Real aggregates, a score-trend chart (with a table view) and rubric averages. History
has search, role filter, sort, pagination, and delete with confirmation.

</td>
</tr>
</table>

<details>
<summary><b>▸ More modules: auth, failure handling, settings, demo mode</b></summary>
<br>

- **Auth:** Supabase email/password sign-up, login, logout, password reset and protected routes. The backend verifies every JWT, via JWKS signing keys or the legacy HS256 secret.
- **Failure handling:** an answer is stored *before* evaluation. A failed evaluation is marked `failed` and offers **Retry**, and scores are never fabricated.
- **Session review:** expand or collapse each question, compare your answer with the example, keep the resume hidden by default, and *Practice again*.
- **Settings:** display name, theme (light/dark/system), AI provider disclosure, sign out, and account deletion.
- **Demo mode:** passwordless, isolated demo accounts with labelled sample history, plus an offline heuristic "AI" that's always labelled as *not an AI model*.

</details>

### ▸ Screens

<table>
<tr>
<td width="50%"><img src="docs/assets/screens/landing.png" alt="Landing page"></td>
<td width="50%"><img src="docs/assets/screens/dashboard.png" alt="Dashboard with score trend"></td>
</tr>
<tr>
<td align="center"><sub><code>/</code> landing</sub></td>
<td align="center"><sub><code>/dashboard</code> progress and rubric averages</sub></td>
</tr>
<tr>
<td><img src="docs/assets/screens/workspace.png" alt="Interview workspace"></td>
<td><img src="docs/assets/screens/evaluation.png" alt="Answer evaluation"></td>
</tr>
<tr>
<td align="center"><sub><code>/interviews/:id</code> one question at a time</sub></td>
<td align="center"><sub>four-dimension evaluation</sub></td>
</tr>
<tr>
<td colspan="2"><img src="docs/assets/screens/job-finder.png" alt="AI Job Finder"></td>
</tr>
<tr>
<td colspan="2" align="center"><sub><code>/jobs</code> AI Job Finder</sub></td>
</tr>
</table>

> [!NOTE]
> These screenshots were captured in **demo mode**: the sample history is fictional and the
> scores come from the offline heuristic, which the UI labels as such.

<img src="docs/assets/divider.svg" width="100%" alt="">

<a id="job-finder"></a>

## `⟨02⟩` AI JOB FINDER

`/jobs` (sidebar: **Job finder**). Upload a resume (PDF/DOCX, or paste / reuse your latest).
Set target roles, location, level, work arrangement and employment type, and see real
listings scored against your resume. **Prepare for interview** sends a listing (plus the
full description you paste, if the listing only has a summary) into the interview engine.

```mermaid
%%{init: {'theme':'base','themeVariables':{'background':'#05010d','primaryColor':'#0d0221','primaryTextColor':'#f5f0ff','primaryBorderColor':'#00f0ff','lineColor':'#ff2a6d','secondaryColor':'#0d0221','tertiaryColor':'#0d0221','edgeLabelBackground':'#0d0221','clusterBkg':'#05010d','clusterBorder':'#7b2cbf','titleColor':'#f9f002','fontFamily':'monospace'}}}%%
flowchart LR
    R[/"Resume"/] -- "contacts redacted" --> P["01 · ANALYSE<br>skills-only profile"]
    P -- "keywords + location" --> S["02 · DISCOVER<br>Adzuna listings"]
    S --> M["03 · EVALUATE<br>score 0–100"]
    M --> I(["PREPARE<br>8-question interview"])
```

| Stage | What runs | Data sent out |
|---|---|---|
| `01` Analyse resume | Gemini extracts a skills-only profile | Resume with contact details removed |
| `02` Discover listings | Adzuna job-search API (`ADZUNA_*`) | Role keywords + location only, **never the resume** |
| `03` Evaluate matches | One batched Gemini call; score computed in code | Profile + redacted resume + listing text |

<details>
<summary><b>▸ How the 0–100 score is computed</b></summary>
<br>

```text
score = 100 × ( 0.40 · skill_coverage      ← computed from evidence in your resume
              + 0.25 · experience          ┐
              + 0.20 · role alignment      ├ AI ratings 1–5, mapped to 0–1
              + 0.15 · responsibilities )  ┘
```

- If a listing names no skills, the skills weight is dropped and the rest renormalised.
- Labels: **≥75 Strong · ≥55 Good · ≥35 Partial · else Weak**.
- It estimates resume-to-listing alignment, **not** hiring probability.
- It is labelled **provisional** unless scored against a full description you provided,
  because Adzuna returns summaries only.

</details>

<details>
<summary><b>▸ Why Adzuna instead of Gemini Google Search grounding</b></summary>
<br>

The Gemini API terms for grounding forbid analysing, caching, altering or mixing other
content into grounded results, and a job finder must do all of those. Adzuna is a licensed
job-search API with a free developer tier.

- Its terms require an "Adzuna" attribution on each listing, which every card renders.
- Organisations may use it on trial for 14 days, and commercial use "may require a
  licence agreement". Check this with Adzuna before a commercial launch.
- Default limits: 25/min, 250/day, 2,500/month.

</details>

<details>
<summary><b>▸ Honesty rules and storage</b></summary>
<br>

- Only listings returned by the provider are shown, and none are ever generated.
- Links are restricted to the provider's own HTTPS listing URLs.
- Missing fields show "Not listed", and predicted salaries are hidden.
- Listings are never claimed to be open.
- **Storage:**
  - `job_searches` holds preferences, queries and the skills-only profile.
  - `job_results` holds listing fields, match analysis and the linked interview.
  - Resume files are processed in memory and never stored, and resume text stays in the browser tab.
  - Both tables are deleted with the account.

</details>

<img src="docs/assets/divider.svg" width="100%" alt="">

<a id="architecture"></a>

## `⟨03⟩` ARCHITECTURE

```mermaid
%%{init: {'theme':'base','themeVariables':{'background':'#05010d','primaryColor':'#0d0221','primaryTextColor':'#f5f0ff','primaryBorderColor':'#ff2a6d','lineColor':'#00f0ff','secondaryColor':'#0d0221','tertiaryColor':'#0d0221','edgeLabelBackground':'#0d0221','clusterBkg':'#05010d','clusterBorder':'#7b2cbf','titleColor':'#f9f002','fontFamily':'monospace'}}}%%
flowchart LR
    subgraph Browser
        W["React + Vite SPA<br>Render static site"]
    end
    subgraph Render
        A["FastAPI<br>Docker web service"]
    end
    subgraph Supabase
        AU["Auth<br>login only"]
        DB[("Postgres<br>+ RLS")]
    end
    AI["Gemini / OpenAI<br>server-side keys"]
    JOBS["Adzuna<br>job-search API"]
    W -- "HTTPS + JWT" --> A
    W -. "sign in" .-> AU
    A -- "verify JWT (JWKS)" --> AU
    A --> DB
    A --> AI
    A --> JOBS
```

| Layer | Choice | Where |
|---|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind, shadcn-style components (Radix), TanStack Query, RHF + Zod, Recharts, Lucide | `frontend/` |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async) | `backend/app` |
| DB | Supabase Postgres + RLS (prod); SQLite (local demo + tests) | `supabase/migrations` |
| Auth | Supabase Auth; backend verifies JWT (JWKS or HS256) | `app/core/security.py` |
| AI | Provider abstraction: `gemini`, `openai`, `demo`, with model fallback | `app/ai/` |
| Jobs | Provider interface + Adzuna adapter, normalisation, deterministic scoring | `app/jobs/` |

<details>
<summary><b>▸ Backend source map</b></summary>

```text
backend/app
├── main.py                 app factory: config validation, middleware, CORS, routers
├── asgi.py                 uvicorn entry point
├── core/                   config, security (JWT), logging (JSON + request IDs), exceptions, rate limit
├── api/routes/             health, sessions, answers, analytics, account, jobs (+ demo)
├── schemas/                public API request/response models
├── models/                 SQLAlchemy ORM (mirrors the SQL migrations)
├── repositories/           all queries, every one scoped by user_id
├── services/               interview, question, evaluation, rewrite, analytics, account, demo, job finder
├── jobs/                   resume extraction, job providers, normalisation, match scoring
└── ai/
    ├── provider.py         Gemini / OpenAI over httpx; error mapping; model fallback; cost estimates
    ├── demo_provider.py    offline heuristic (explicitly selected, never a fallback)
    ├── structured.py       bounded retries + JSON repair + schema validation
    ├── schemas.py          AI output schemas (8 questions, 1–5 scores…)
    └── prompts/            version-controlled prompts
```

</details>

<details>
<summary><b>▸ Key design decisions</b></summary>
<br>

- **The backend owns all data access.**
  - The browser uses Supabase only for authentication.
  - The backend scopes **every** query by the verified user id.
  - It returns 404 rather than 403, so it never reveals whether a record exists.
  - RLS policies add defence in depth.
- **AI calls happen before writes.** Session creation runs both AI steps first, then inserts the session and its questions in one transaction, so a failure leaves no partial rows.
- **Idempotency:**
  - A `UNIQUE(question_id)` constraint allows one answer per question.
  - An identical resubmit returns the stored answer.
  - An atomic `UPDATE … WHERE status IN (…)` claim stops two tabs from evaluating, and billing, the same answer.
  - A claim stuck in `evaluating` is reclaimed after 4 minutes.
- **Prompt-injection hardening:**
  - User text travels only as JSON inside `<untrusted_data>`, with `<` and `>` escaped so it can't close the block.
  - System prompts tell the model to treat that data as data, never as instructions.
  - All model output is schema-validated.
  - The LLM has no tools, SQL or credentials.
- **Data minimisation:**
  - Email addresses, phone numbers and links are redacted before AI calls.
  - Logs contain IDs, sizes and durations, never resume text, answers or tokens.

</details>

<img src="docs/assets/divider.svg" width="100%" alt="">

<a id="quick-start"></a>

## `⟨04⟩` BOOT SEQUENCE

> [!TIP]
> **No credentials needed.** Demo mode runs on SQLite with an offline heuristic in place of the AI.
> Prerequisites: Python 3.12+ and Node 20+.

<details open>
<summary><b>▸ Windows: one command</b></summary>
<br>

```powershell
powershell -ExecutionPolicy Bypass -File .\start-dev.ps1
```

</details>

<details>
<summary><b>▸ Manual: macOS / Linux / Windows</b></summary>
<br>

```bash
# Backend (demo mode, SQLite, offline demo AI)
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                     # defaults: DEMO_MODE=true, AI_PROVIDER=demo
uvicorn app.asgi:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env.local                               # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

</details>

Open **http://localhost:5173**, choose **Log in**, then **Explore the demo**. API docs are at http://localhost:8000/docs.

> [!WARNING]
> **Seeing `{"error":{"code":"not_found",...}}`?** Port 8000 is the API, not the website.
> Open **http://localhost:5173** instead (the web app must be running).

To get real AI feedback while still using demo login, set `AI_PROVIDER=gemini` and
`GEMINI_API_KEY=…` (or `openai` / `OPENAI_API_KEY`) in `backend/.env` and restart.

<details>
<summary><b>▸ Full local setup: Supabase + real AI</b></summary>
<br>

1. **Create a Supabase project** at supabase.com.
2. **Apply migrations** once `DATABASE_URL` is set in `backend/.env` (step 5):
   - Run `cd backend && python -m scripts.apply_migrations`. It is safe to re-run.
   - Or paste `supabase/migrations/*.sql` into the SQL editor in order, or use `supabase db push`.
   - Then run `python -m scripts.check_setup` to verify the database, auth keys and AI key without printing secrets.
3. *(Recommended)* **Run the RLS isolation test** on a non-production project: `psql "$DB_URL" -f supabase/tests/rls_isolation_test.sql`. It runs inside a rolled-back transaction.
4. **Configure Auth.** Under Authentication → URL Configuration, set the Site URL to `http://localhost:5173` and add `http://localhost:5173/reset-password` as a redirect URL.
5. **`backend/.env`:**
   ```env
   DEMO_MODE=false
   DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   DB_AUTO_CREATE=false
   SUPABASE_URL=https://<ref>.supabase.co
   SUPABASE_JWT_SECRET=            # only if your project still uses legacy HS256 JWT secret
   SUPABASE_SERVICE_ROLE_KEY=...   # optional: lets account deletion remove the auth user
   AI_PROVIDER=gemini
   GEMINI_API_KEY=...
   ADZUNA_APP_ID=...               # optional: enables live job search (developer.adzuna.com)
   ADZUNA_APP_KEY=...
   ```
6. **`frontend/.env.local`:**
   ```env
   VITE_API_BASE_URL=http://localhost:8000
   VITE_SUPABASE_URL=https://<ref>.supabase.co
   VITE_SUPABASE_ANON_KEY=<public anon / publishable key>
   ```

</details>

<details>
<summary><b>▸ Environment variables</b></summary>
<br>

| Variable | Where | Required | Purpose |
|---|---|---|---|
| `APP_ENV` | backend | – | `development` / `test` / `production` (stricter startup checks) |
| `FRONTEND_ORIGIN` | backend | prod | Comma-separated CORS allowlist |
| `DATABASE_URL` | backend | prod | Postgres URL (Supabase session pooler recommended) |
| `DB_AUTO_CREATE` | backend | – | `true` only for SQLite/dev; production uses migrations |
| `SUPABASE_URL` | backend | prod | JWKS verification + admin user deletion |
| `SUPABASE_JWT_SECRET` | backend | legacy | HS256 verification for legacy projects |
| `SUPABASE_SERVICE_ROLE_KEY` | backend | optional | Deletes the auth user on account deletion |
| `DEMO_MODE`, `DEMO_JWT_SECRET`, `DEMO_SESSIONS_PER_HOUR` | backend | – | Demo accounts (SQLite only) |
| `AI_PROVIDER` | backend | ✔ | `gemini` / `openai` / `demo` |
| `GEMINI_API_KEY` / `OPENAI_API_KEY` | backend | per provider | Never exposed to the browser |
| `AI_MODEL`, `AI_FALLBACK_MODELS` | backend | – | Primary model, then comma-separated models tried in order when it is overloaded (503/429/timeout) |
| `AI_TIMEOUT_SECONDS`, `AI_MAX_RETRIES`, `AI_RETRY_BACKOFF_SECONDS` | backend | – | Bounded retry policy |
| `RATE_LIMIT_PER_MINUTE` | backend | – | Per-user AI request limit |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`, `ADZUNA_COUNTRY` | backend | for job finder | Licensed job-search provider |
| `JOB_SEARCH_*`, `JOB_SEARCHES_PER_HOUR`, `RESUME_UPLOAD_MAX_MB` | backend | – | Job finder cache, limits and upload size |
| `VITE_API_BASE_URL` | frontend | ✔ | Backend URL |
| `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` | frontend | for real auth | **Public** values only |

The backend refuses to start with an inconsistent configuration. For example, it rejects a
real provider without a key, production with SQLite or localhost CORS, and demo mode with
Postgres.

</details>

<img src="docs/assets/divider.svg" width="100%" alt="">

<a id="deploy"></a>

## `⟨05⟩` DEPLOY TO THE GRID

[`render.yaml`](render.yaml) is a Render Blueprint that creates both services:

| Service | Type | Source |
|---|---|---|
| `interviewiq-api` | Docker web service | `backend/` |
| `interviewiq-web` | Static site with SPA rewrites and security headers | `frontend/` |

1. Render dashboard → **New → Blueprint** → select this repo.
2. Fill in the values Render asks for. The API's secrets stay on the API; the website gets only public `VITE_` values.
3. Set `FRONTEND_ORIGIN` to the website URL and `VITE_API_BASE_URL` to the API URL.
4. In Supabase → Authentication → URL Configuration, set the Site URL to the website and add its `/login` and `/reset-password` as redirect URLs.

> [!IMPORTANT]
> Never put `DATABASE_URL`, the service-role key or AI keys in a `VITE_` variable: those
> are bundled into the browser. Render's free plan sleeps when idle, so the first request
> after a pause is slow. More detail is in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

<img src="docs/assets/divider.svg" width="100%" alt="">

<a id="tests"></a>

## `⟨06⟩` DIAGNOSTICS

```bash
cd backend
pytest                       # 128 tests, mocked AI, SQLite: no credentials needed
TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/iq_test pytest   # same suite on Postgres
pytest -m live_ai            # optional: real provider round-trip (needs a key in .env)
ruff check . && ruff format --check . && mypy app

cd frontend
npm run lint && npm run typecheck && npm test && npm run build
```

CI ([`ci.yml`](.github/workflows/ci.yml)) runs all of this on SQLite **and** Postgres 16.
It also applies the SQL migrations, runs the RLS isolation test, builds the frontend and
builds the Docker image.

<details>
<summary><b>▸ What the backend tests cover</b></summary>
<br>

- Request validation, question-schema and count validation, invalid categories and distribution.
- Score range and percentage maths, malformed-JSON repair, bounded retries, and transient vs permanent vs quota errors.
- IDOR and ownership checks for every endpoint, plus expired, forged and `alg=none` tokens.
- Idempotent duplicate submits, out-of-order answers, evaluation failure followed by retry, and refresh restore.
- Rewrite caching and regeneration, analytics aggregation, rate limits, and prompt-injection isolation.
- Job finder:
  - PDF/DOCX extraction and rejection, and the Adzuna adapter against a mocked API.
  - URL safety, de-duplication, scoring, caching, partial results and per-user isolation.
  - Prepare-interview.
- Log hygiene, atomic rollback on DB failure, account deletion, and the evaluator metrics.

</details>

<details>
<summary><b>▸ Demo mode</b></summary>
<br>

- `DEMO_MODE=true` adds **Explore the demo** to the login page. Each visitor gets an isolated account (random UUID, 12-hour token) seeded with three fictional sessions, badged **Demo** in the UI.
- `AI_PROVIDER=demo` replaces the AI with a deterministic keyword/statistics heuristic. A banner, a badge on every score and the `[Demo heuristic]` prefix in feedback all say it is **not an AI model**.
- Demo mode needs the SQLite database, because demo users aren't Supabase Auth users. See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for a separate public demo backend.
- With a real provider configured, the app never falls back to demo output when the provider fails. It shows an error and keeps the answer for a retry.

</details>

<details>
<summary><b>▸ Evaluator quality</b></summary>
<br>

`backend/evals/` contains 30 synthetic answers (10 questions × weak/medium/strong) and an
agreement runner. The runner reports MAE, exact agreement, within-one agreement, quadratic
weighted kappa, bias and the largest disagreements. **Human labels are intentionally empty,
and no agreement experiment has been run.** The runner refuses to report metrics until at
least 30 items are human-labelled. See [backend/evals/README.md](backend/evals/README.md).

</details>

<details>
<summary><b>▸ Known limitations</b></summary>
<br>

- **Verified against live services:**
  - Gemini (question generation, evaluation, resume profile and job matching).
  - A hosted Supabase project.
- **Live Adzuna search has not been tested yet:** the adapter is tested against a mocked API.
- **Rate limiting is per process** and kept in memory. With several instances, move it to Redis.
- **Synchronous AI calls:** generation and evaluation run inside the HTTP request, which takes 10–40 s for generation. A job queue would be the next step at scale.
- **Demo heuristic scores** measure only text statistics; they aren't meaningful feedback.
- **React Router v6:** two moderate advisories (GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg) are fixed only in v7.
  - The app doesn't use SSR.
  - Its one redirect from user input (`?next=`) goes through a strict same-site validator (`safeRedirectPath`, unit-tested).
  - Upgrading to v7 is recommended.
- **Cost estimates** in `ai_usage_events` use a static price table in `app/ai/provider.py`. They're approximate.
- **Resume upload:** old `.doc` files and scanned (image-only) PDFs aren't supported; scanned PDFs get a clear message.

</details>

<details>
<summary><b>▸ Requires credentials or manual configuration</b></summary>
<br>

- Supabase project, migrations, Auth URL configuration and email templates/SMTP (email confirmation and password reset).
- A Gemini or OpenAI API key for real question generation, evaluation and rewriting.
- Adzuna `app_id` / `app_key` for live job search.
- `SUPABASE_SERVICE_ROLE_KEY` so account deletion also removes the auth user. Without it, the app deletes all data and tells the user that an admin must remove the login.
- Render services (via the Blueprint).
- Human labels for the evaluation dataset.

</details>

<img src="docs/assets/divider.svg" width="100%" alt="">

<div align="center">

<sub>

**[`API reference`](docs/API.md)** &nbsp;·&nbsp; **[`Deployment`](docs/DEPLOYMENT.md)** &nbsp;·&nbsp; **[`Demo script`](docs/DEMO_SCRIPT.md)** &nbsp;·&nbsp; **[`Evaluator agreement`](backend/evals/README.md)**

</sub>

<br>

<code>// end of transmission</code> &nbsp; · &nbsp; built by <a href="https://github.com/harshgupta257">Harsh Gupta</a> &nbsp; · &nbsp; <a href="#top">▲ back to top</a>

</div>
