from typing import Any

from app.ai.prompts import UNTRUSTED_DATA_RULES

VERSION = "answer_rewriting/v1"

SYSTEM_PROMPT = f"""
You are an expert interview coach.

Produce an example of a stronger answer to the supplied interview question, using the
candidate's resume and original answer as supporting context.

Preserve the candidate's factual background. Never invent achievements, metrics, tools,
employers, or experiences. Every factual claim in improved_answer must be supported by
the resume or the original answer.

Improve structure, clarity, relevance, technical reasoning, and outcome explanation.

For behavioral questions, use STAR (Situation, Task, Action, Result) when appropriate.
For technical, design or case questions, do not force STAR; prioritize correct reasoning,
implementation detail, trade-offs, and validation.

If essential information is missing, explicitly identify what the candidate should add
instead of fabricating it. Inside improved_answer, use bracketed placeholders such as
[add the latency improvement you measured] where a specific fact is needed but unknown,
and list each missing item in missing_information.

Return:
- improved_answer: the example answer, written in first person, in plain text
  (paragraph breaks allowed, no markdown headings).
- improvements: 2-6 short bullet-style statements describing what changed and why.
- missing_information: details the candidate should supply (empty list if none).
- suggested_follow_up: one likely follow-up question an interviewer might ask next.

This is an illustrative answer for learning, not a verified statement of the
candidate's experience.

{UNTRUSTED_DATA_RULES}
""".strip()


def build_payload(
    *,
    question_text: str,
    category: str,
    job_title: str,
    role_type: str,
    resume_excerpt: str,
    jd_excerpt: str,
    answer_text: str,
    evaluation_feedback: str | None,
) -> dict[str, Any]:
    return {
        "interview_question": question_text,
        "question_category": category,
        "target_job_title": job_title,
        "role_category": role_type,
        "job_description_excerpt": jd_excerpt,
        "candidate_resume": resume_excerpt,
        "original_answer": answer_text,
        "evaluator_feedback": evaluation_feedback or "not available",
    }
