-- RLS isolation test. Run against a NON-PRODUCTION Supabase project after applying the
-- migrations (SQL editor, or: psql "$DATABASE_URL" -f supabase/tests/rls_isolation_test.sql).
-- Everything happens inside a transaction that is rolled back, so no data persists.
-- Any failed assertion raises an exception and aborts the script.

begin;

-- Two throwaway users.
insert into auth.users (id, email, aud, role)
values
  ('00000000-0000-4000-a000-00000000000a', 'rls-a@example.test', 'authenticated', 'authenticated'),
  ('00000000-0000-4000-a000-00000000000b', 'rls-b@example.test', 'authenticated', 'authenticated');

-- Seed one session + question for user A (as the table owner, bypassing RLS).
insert into public.sessions (id, user_id, job_title, jd_text, resume_text, role_type, ai_provider, ai_model)
values ('00000000-0000-4000-b000-00000000000a', '00000000-0000-4000-a000-00000000000a',
        'RLS test', 'jd', 'resume', 'other', 'test', 'test');
insert into public.questions (id, session_id, question_text, category, why_this_question, order_index)
values ('00000000-0000-4000-c000-00000000000a', '00000000-0000-4000-b000-00000000000a',
        'Question text for the RLS test?', 'technical', 'why', 0);

-- Job finder data for user A.
insert into public.job_searches (id, user_id, cache_key, provider, params, expires_at)
values ('00000000-0000-4000-d000-00000000000a', '00000000-0000-4000-a000-00000000000a',
        'k', 'adzuna', '{}'::jsonb, now() + interval '1 hour');
insert into public.job_results (search_id, user_id, rank, provider, provider_job_id, title, url)
values ('00000000-0000-4000-d000-00000000000a', '00000000-0000-4000-a000-00000000000a',
        0, 'adzuna', '1', 'Engineer', 'https://www.adzuna.in/land/ad/1');

-- ---- Act as user B -------------------------------------------------------------
set local role authenticated;
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-a000-00000000000b","role":"authenticated"}', true);

do $$
begin
  if (select count(*) from public.sessions) <> 0 then
    raise exception 'RLS FAIL: user B can read user A sessions';
  end if;
  if (select count(*) from public.questions) <> 0 then
    raise exception 'RLS FAIL: user B can read user A questions';
  end if;
  if (select count(*) from public.job_searches) <> 0 or (select count(*) from public.job_results) <> 0 then
    raise exception 'RLS FAIL: user B can read user A job finder data';
  end if;
  begin
    insert into public.job_results (search_id, user_id, rank, provider, provider_job_id, title, url)
    values ('00000000-0000-4000-d000-00000000000a', '00000000-0000-4000-a000-00000000000b',
            1, 'adzuna', '2', 'Injected', 'https://www.adzuna.in/land/ad/2');
    raise exception 'RLS FAIL: user B inserted a job result into user A search';
  exception when insufficient_privilege then
    null;
  end;

  update public.sessions set job_title = 'hijacked'
  where id = '00000000-0000-4000-b000-00000000000a';
  delete from public.sessions where id = '00000000-0000-4000-b000-00000000000a';

  begin
    insert into public.answers (question_id, session_id, user_id, answer_text)
    values ('00000000-0000-4000-c000-00000000000a', '00000000-0000-4000-b000-00000000000a',
            '00000000-0000-4000-a000-00000000000b', 'B answering A''s question');
    raise exception 'RLS FAIL: user B inserted an answer into user A session';
  exception when insufficient_privilege then
    null; -- expected: new row violates row-level security policy
  end;

  begin
    insert into public.sessions (user_id, job_title, jd_text, resume_text, role_type, ai_provider, ai_model)
    values ('00000000-0000-4000-a000-00000000000a', 'spoof', 'jd', 'cv', 'other', 't', 't');
    raise exception 'RLS FAIL: user B created a session owned by user A';
  exception when insufficient_privilege then
    null;
  end;
end $$;

-- ---- Act as user A -------------------------------------------------------------
select set_config('request.jwt.claims',
  '{"sub":"00000000-0000-4000-a000-00000000000a","role":"authenticated"}', true);

do $$
begin
  if (select job_title from public.sessions where id = '00000000-0000-4000-b000-00000000000a') <> 'RLS test' then
    raise exception 'RLS FAIL: user B modified or deleted user A session';
  end if;
  if (select count(*) from public.questions) <> 1 then
    raise exception 'RLS FAIL: user A cannot read own questions';
  end if;
  insert into public.answers (question_id, session_id, user_id, answer_text)
  values ('00000000-0000-4000-c000-00000000000a', '00000000-0000-4000-b000-00000000000a',
          '00000000-0000-4000-a000-00000000000a', 'Owner answer');
  if (select count(*) from public.job_results) <> 1 then
    raise exception 'RLS FAIL: user A cannot read own job results';
  end if;
  raise notice 'RLS isolation test passed';
end $$;

-- ---- Anonymous role sees nothing ---------------------------------------------------
reset role;
set local role anon;
do $$
begin
  perform 1 from public.sessions;
  raise exception 'RLS FAIL: anon can query sessions';
exception when insufficient_privilege then
  null;
end $$;

rollback;
