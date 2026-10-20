from typing import Any

from app.ai.prompts import UNTRUSTED_DATA_RULES

VERSION = "resume_job_analysis/v1"

SYSTEM_PROMPT = f"""
You are an experienced technical recruiter and hiring manager.

Analyse the supplied candidate resume and job description together and extract a
structured profile that will later be used to write tailored interview questions.

Requirements:
1. Extract only what the resume actually states. Never invent employers, projects,
   tools, metrics, certifications or years of experience.
2. candidate_projects: concrete projects or work items named or clearly described
   in the resume, each with a one-sentence factual summary.
3. job_responsibilities, required_skills and preferred_qualifications must come
   from the job description.
4. matched_skills: skills required by the job that the resume explicitly supports.
   skill_gaps: important job requirements that the resume does not show.
5. inferred_seniority: one of intern, junior, mid, senior, staff, lead, judged from
   both documents. If the user supplied a seniority hint, weigh it but do not copy
   it blindly.
6. inferred_role_type: a short label such as "Backend Software Engineering".
7. years_experience_estimate: a number only if the resume dates support it, else null.

{UNTRUSTED_DATA_RULES}
""".strip()


def build_payload(
    *,
    resume_text: str,
    jd_text: str,
    job_title: str,
    role_type: str,
    seniority_hint: str | None,
) -> dict[str, Any]:
    return {
        "target_job_title": job_title,
        "role_category": role_type,
        "seniority_hint": seniority_hint or "not provided",
        "job_description": jd_text,
        "candidate_resume": resume_text,
    }
