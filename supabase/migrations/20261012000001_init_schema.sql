-- InterviewIQ initial schema.
-- Source of truth for the production database (Supabase Postgres).
-- The backend ORM models in backend/app/models mirror these tables.

-- gen_random_uuid() is built into Postgres 13+; no extension required.

-- ---------------------------------------------------------------- helpers
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------- profiles
create table if not exists public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  display_name text check (char_length(display_name) <= 120),
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Create a profile row automatically when a user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, nullif(new.raw_user_meta_data ->> 'display_name', ''))
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------- sessions
create table if not exists public.sessions (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users (id) on delete cascade,
  job_title       varchar(200) not null,
  company         varchar(200),
  jd_text         text not null check (char_length(jd_text) <= 12000),
  resume_text     text not null check (char_length(resume_text) <= 15000),
  role_type       varchar(64) not null check (role_type in (
                    'software_engineering', 'data_engineering', 'data_science', 'data_analytics',
                    'ai_ml_engineering', 'forward_deployed_engineering', 'other')),
  seniority_level varchar(32),
  difficulty      varchar(16),
  status          varchar(20) not null default 'in_progress'
                    constraint sessions_status_check check (status in ('in_progress', 'completed', 'failed')),
  analysis_json   jsonb,
  ai_provider     varchar(32) not null,
  ai_model        varchar(64) not null,
  is_demo         boolean not null default false,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  completed_at    timestamptz
);

create index if not exists ix_sessions_user_created on public.sessions (user_id, created_at desc);
create index if not exists ix_sessions_user_id on public.sessions (user_id);

create trigger sessions_set_updated_at
  before update on public.sessions
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------- questions
create table if not exists public.questions (
  id                uuid primary key default gen_random_uuid(),
  session_id        uuid not null references public.sessions (id) on delete cascade,
  question_text     text not null,
  category          varchar(32) not null
                      constraint questions_category_check check (category in (
                        'technical', 'behavioral', 'project_deepdive', 'system_design',
                        'motivation', 'case_study')),
  difficulty        varchar(16),
  why_this_question text not null,
  source_context    jsonb not null default '[]'::jsonb,
  evaluation_focus  jsonb not null default '[]'::jsonb,
  order_index       integer not null check (order_index >= 0),
  created_at        timestamptz not null default now(),
  constraint questions_session_order_key unique (session_id, order_index),
  -- Lets answers reference (question, session) together so they can never disagree.
  constraint questions_id_session_key unique (id, session_id)
);

create index if not exists ix_questions_session_id on public.questions (session_id);

-- ---------------------------------------------------------------- answers
create table if not exists public.answers (
  id                       uuid primary key default gen_random_uuid(),
  question_id              uuid not null,
  session_id               uuid not null references public.sessions (id) on delete cascade,
  user_id                  uuid not null references auth.users (id) on delete cascade,
  answer_text              text not null check (char_length(answer_text) <= 6000),
  evaluation_status        varchar(16) not null default 'pending'
                             constraint answers_eval_status_check
                             check (evaluation_status in ('pending', 'evaluating', 'completed', 'failed')),
  evaluation_error         text,
  evaluation_attempts      integer not null default 0,
  score_clarity            integer constraint answers_score_clarity_check check (score_clarity between 1 and 5),
  score_specificity        integer constraint answers_score_specificity_check check (score_specificity between 1 and 5),
  score_result_orientation integer constraint answers_score_result_check check (score_result_orientation between 1 and 5),
  score_relevance          integer constraint answers_score_relevance_check check (score_relevance between 1 and 5),
  overall_score            numeric(4, 2) check (overall_score between 1 and 5),
  feedback_json            jsonb,
  ideal_answer             text,
  rewrite_json             jsonb,
  answered_at              timestamptz default now(),
  evaluated_at             timestamptz,
  updated_at               timestamptz not null default now(),
  -- One submitted answer per question (idempotency / no duplicate scores).
  constraint answers_question_id_key unique (question_id),
  constraint answers_question_session_fkey foreign key (question_id, session_id)
    references public.questions (id, session_id) on delete cascade,
  -- A completed evaluation must have every score.
  constraint answers_completed_has_scores check (
    evaluation_status <> 'completed' or (
      score_clarity is not null and score_specificity is not null and
      score_result_orientation is not null and score_relevance is not null and
      overall_score is not null))
);

create index if not exists ix_answers_session_id on public.answers (session_id);
create index if not exists ix_answers_user_id on public.answers (user_id);
create index if not exists ix_answers_user_answered on public.answers (user_id, answered_at);

create trigger answers_set_updated_at
  before update on public.answers
  for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------- AI usage (observability)
create table if not exists public.ai_usage_events (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references auth.users (id) on delete cascade,
  operation          varchar(32) not null,
  provider           varchar(32) not null,
  model              varchar(64) not null,
  status             varchar(16) not null,
  attempts           integer not null default 1,
  duration_ms        integer not null default 0,
  prompt_tokens      integer,
  completion_tokens  integer,
  estimated_cost_usd numeric(10, 6),
  error_type         varchar(64),
  created_at         timestamptz not null default now()
);

create index if not exists ix_ai_usage_events_user_id on public.ai_usage_events (user_id);
create index if not exists ix_ai_usage_events_created_at on public.ai_usage_events (created_at);
