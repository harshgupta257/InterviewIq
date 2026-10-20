-- AI Job Finder: saved searches and their listings. Additive only.
-- Stores preferences, provider queries, a skills-only profile (no resume text or personal
-- details), listing data returned by the job-search provider, and match analysis.

create table if not exists public.job_searches (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users (id) on delete cascade,
  cache_key   varchar(64) not null,
  provider    varchar(32) not null,
  country     varchar(8),
  params      jsonb not null,
  queries     jsonb not null default '[]'::jsonb,
  profile     jsonb not null default '{}'::jsonb,
  status      varchar(16) not null default 'discovered'
                constraint job_searches_status_check check (status in ('discovered', 'matched', 'match_failed')),
  match_error text,
  total_found integer not null default 0,
  rejected    integer not null default 0,
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null
);

create index if not exists ix_job_searches_user_created on public.job_searches (user_id, created_at desc);
create index if not exists ix_job_searches_user_cache on public.job_searches (user_id, cache_key);

create table if not exists public.job_results (
  id                   uuid primary key default gen_random_uuid(),
  search_id            uuid not null references public.job_searches (id) on delete cascade,
  user_id              uuid not null references auth.users (id) on delete cascade,
  rank                 integer not null,
  provider             varchar(32) not null,
  provider_job_id      varchar(300) not null,
  title                varchar(300) not null,
  company              varchar(200),
  location             varchar(200),
  work_mode            varchar(16),
  employment_type      varchar(64),
  experience_level     varchar(16),
  salary_min           numeric(14, 2),
  salary_max           numeric(14, 2),
  salary_currency      varchar(3),
  category             varchar(120),
  description          text check (char_length(description) <= 12000),
  description_source   varchar(20) not null default 'listing_summary'
                         constraint job_results_desc_source_check
                         check (description_source in ('listing_summary', 'user_provided')),
  url                  text not null check (url like 'https://%'),
  posted_at            timestamptz,
  retrieved_at         timestamptz not null default now(),
  match                jsonb,
  interview_session_id uuid references public.sessions (id) on delete set null,
  constraint job_results_search_provider_key unique (search_id, provider_job_id)
);

create index if not exists ix_job_results_search_id on public.job_results (search_id);
create index if not exists ix_job_results_user_id on public.job_results (user_id);

-- Row Level Security: owner-only access (the backend also scopes every query by user id).
alter table public.job_searches enable row level security;
alter table public.job_results  enable row level security;
revoke all on public.job_searches, public.job_results from anon;

create policy "job_searches: owner can read"
  on public.job_searches for select to authenticated
  using (user_id = (select auth.uid()));
create policy "job_searches: owner can insert"
  on public.job_searches for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy "job_searches: owner can update"
  on public.job_searches for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy "job_searches: owner can delete"
  on public.job_searches for delete to authenticated
  using (user_id = (select auth.uid()));

create policy "job_results: owner can read"
  on public.job_results for select to authenticated
  using (user_id = (select auth.uid()));
create policy "job_results: owner can insert into own search"
  on public.job_results for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.job_searches s
      where s.id = job_results.search_id and s.user_id = (select auth.uid())));
create policy "job_results: owner can update"
  on public.job_results for update to authenticated
  using (user_id = (select auth.uid()))
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.job_searches s
      where s.id = job_results.search_id and s.user_id = (select auth.uid())));
create policy "job_results: owner can delete"
  on public.job_results for delete to authenticated
  using (user_id = (select auth.uid()));
