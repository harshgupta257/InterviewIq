-- Row Level Security for every user-owned table.
--
-- Defence in depth: the FastAPI backend already scopes every query by the verified
-- user id. These policies additionally guarantee that a client holding only the
-- public anon key and a user's JWT can never read or modify another user's rows.
-- `(select auth.uid())` is used so Postgres evaluates it once per statement.

alter table public.profiles        enable row level security;
alter table public.sessions        enable row level security;
alter table public.questions       enable row level security;
alter table public.answers         enable row level security;
alter table public.ai_usage_events enable row level security;

-- Anonymous (not signed in) clients get nothing.
revoke all on public.profiles, public.sessions, public.questions, public.answers,
              public.ai_usage_events from anon;

-- ---------------------------------------------------------------- profiles
create policy "profiles: owner can read"
  on public.profiles for select to authenticated
  using (id = (select auth.uid()));

create policy "profiles: owner can insert"
  on public.profiles for insert to authenticated
  with check (id = (select auth.uid()));

create policy "profiles: owner can update"
  on public.profiles for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

create policy "profiles: owner can delete"
  on public.profiles for delete to authenticated
  using (id = (select auth.uid()));

-- ---------------------------------------------------------------- sessions
create policy "sessions: owner can read"
  on public.sessions for select to authenticated
  using (user_id = (select auth.uid()));

create policy "sessions: owner can insert"
  on public.sessions for insert to authenticated
  with check (user_id = (select auth.uid()));

create policy "sessions: owner can update"
  on public.sessions for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

create policy "sessions: owner can delete"
  on public.sessions for delete to authenticated
  using (user_id = (select auth.uid()));

-- ---------------------------------------------------------------- questions
-- Ownership is inherited from the parent session.
create policy "questions: session owner can read"
  on public.questions for select to authenticated
  using (exists (
    select 1 from public.sessions s
    where s.id = questions.session_id and s.user_id = (select auth.uid())));

create policy "questions: session owner can insert"
  on public.questions for insert to authenticated
  with check (exists (
    select 1 from public.sessions s
    where s.id = questions.session_id and s.user_id = (select auth.uid())));

create policy "questions: session owner can update"
  on public.questions for update to authenticated
  using (exists (
    select 1 from public.sessions s
    where s.id = questions.session_id and s.user_id = (select auth.uid())))
  with check (exists (
    select 1 from public.sessions s
    where s.id = questions.session_id and s.user_id = (select auth.uid())));

create policy "questions: session owner can delete"
  on public.questions for delete to authenticated
  using (exists (
    select 1 from public.sessions s
    where s.id = questions.session_id and s.user_id = (select auth.uid())));

-- ---------------------------------------------------------------- answers
-- Inserting requires owning the session; the composite FK already guarantees the
-- question belongs to that session.
create policy "answers: owner can read"
  on public.answers for select to authenticated
  using (user_id = (select auth.uid()));

create policy "answers: owner can insert into own session"
  on public.answers for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.sessions s
      where s.id = answers.session_id and s.user_id = (select auth.uid())));

create policy "answers: owner can update"
  on public.answers for update to authenticated
  using (user_id = (select auth.uid()))
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.sessions s
      where s.id = answers.session_id and s.user_id = (select auth.uid())));

create policy "answers: owner can delete"
  on public.answers for delete to authenticated
  using (user_id = (select auth.uid()));

-- ---------------------------------------------------------------- ai_usage_events
-- Written only by the backend; users may read their own usage.
create policy "ai_usage_events: owner can read"
  on public.ai_usage_events for select to authenticated
  using (user_id = (select auth.uid()));
