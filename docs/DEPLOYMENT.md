# Deployment

Target: **Supabase** (DB + Auth) → **Render** (FastAPI, Docker) → **Vercel** (static SPA).

## 1. Supabase

1. Create a project and note the **Project URL**, the **anon/publishable key** and the **DB password**.
2. Apply `supabase/migrations/*.sql` in filename order. Use the SQL editor, or the CLI: `supabase link --project-ref <ref>` then `supabase db push`.
3. Run `supabase/tests/rls_isolation_test.sql` on a **staging** project. It should print `RLS isolation test passed`, and everything it does is rolled back.
4. Under Authentication → URL Configuration:
   - Set the Site URL to `https://<your-app>.vercel.app`.
   - Add redirect URLs `https://<your-app>.vercel.app/reset-password` and `https://<your-app>.vercel.app/login`.
5. Under Authentication → Emails, configure SMTP for production volumes. The built-in sender is rate-limited.
6. Under Database → Connection string, copy the **Session pooler** URI (port 5432) for `DATABASE_URL`.

## 2. Render (backend)

1. Push the repo to GitHub, then in Render choose **New → Blueprint** and select the repo. `render.yaml` defines the service.
2. Fill in the prompted secrets:

| Key | Value |
|---|---|
| `FRONTEND_ORIGIN` | `https://<your-app>.vercel.app` (comma-separate extra domains) |
| `DATABASE_URL` | Supabase session-pooler URI |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_JWT_SECRET` | only for legacy HS256 projects; otherwise leave empty (JWKS is used) |
| `SUPABASE_SERVICE_ROLE_KEY` | service-role / secret key (for account deletion) |
| `GEMINI_API_KEY` or `OPENAI_API_KEY` | matching `AI_PROVIDER` |

3. The health check path is `/health`. A third-party AI outage does not fail it.
4. On boot the logs should show a JSON `startup` line. If configuration is invalid, the service exits with a list of problems instead of serving traffic.

**HTTPS.** Render terminates TLS. Uvicorn runs with `--proxy-headers`, so client IPs come from `X-Forwarded-For`.

**Logs.** Logs are structured JSON on stdout. Filter by `request_id`, which is also returned to clients in `X-Request-ID` and shown in UI error states. AI calls log `ai_call_succeeded` or `ai_attempt_failed` with duration, attempts and tokens. Per-user cost and latency rows are written to `ai_usage_events`.

**Free plan caveat.** Render's free plan sleeps when idle, so the first request after a pause is slow. Deploys restart the service. This configuration does not claim zero-downtime deploys.

## 3. Vercel (frontend)

1. Import the repo and set **Root Directory** to `frontend`. `vercel.json` sets the Vite build, SPA rewrites and security headers.
2. Set these environment variables (all public):
   - `VITE_API_BASE_URL=https://<render-service>.onrender.com`
   - `VITE_SUPABASE_URL=https://<ref>.supabase.co`
   - `VITE_SUPABASE_ANON_KEY=<anon/publishable key>`
3. Deploy, then update `FRONTEND_ORIGIN` on Render if the domain changed.

Never put the service-role key, the AI keys or `DATABASE_URL` in Vercel. Every `VITE_` variable ends up in the browser bundle.

## 4. Optional: public demo deployment

To let visitors try the product without accounts or AI cost, run a **second** Render service
with these settings:
`DEMO_MODE=true`, `AI_PROVIDER=demo`, `DATABASE_URL=sqlite+aiosqlite:////tmp/demo.db`,
`DB_AUTO_CREATE=true`, a strong `DEMO_JWT_SECRET` (48+ random characters), and
`FRONTEND_ORIGIN` set to that demo frontend.

Then point a separate Vercel project at it with no Supabase variables. Demo data is
ephemeral and resets on each deploy or restart.

## 5. GitHub Actions

- `ci.yml` runs on every push and PR. It covers backend lint, format and types, tests on SQLite and Postgres 16, migrations plus the RLS test, frontend lint, typecheck, test and build, and the Docker build. It needs no secrets.
- `deploy.yml` is optional and runs after CI succeeds on `main`. Its secrets are `RENDER_DEPLOY_HOOK_URL`, `VERCEL_TOKEN`, `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`. Missing secrets skip a step instead of failing it. If you use Render's and Vercel's native Git auto-deploys, delete this workflow so deploys don't happen twice.

## Production checklist

- [ ] Migrations applied; RLS test passed on staging
- [ ] `APP_ENV=production`, `DB_AUTO_CREATE=false`, `DEMO_MODE=false`
- [ ] `FRONTEND_ORIGIN` is the exact Vercel domain (no localhost)
- [ ] AI key set and `pytest -m live_ai` passed once with it
- [ ] Supabase Auth redirect URLs and SMTP configured
- [ ] `SUPABASE_SERVICE_ROLE_KEY` set (account deletion removes the login)
- [ ] `/health` returns `{"status":"ok","database":"ok"}`
- [ ] Sign-up → interview → evaluation → history smoke test on the deployed URL
