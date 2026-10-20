"""Demo accounts: isolated per visitor, seeded with clearly-labelled sample history.

Seed sessions are produced by the offline DemoProvider (not an AI model) and are
flagged is_demo=True so the UI labels them as sample data.
"""

import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.demo_provider import DemoProvider
from app.ai.prompts import answer_evaluation, question_generation, resume_job_analysis
from app.ai.schemas import AnswerEvaluation, QuestionSet, ResumeJobAnalysis
from app.ai.structured import run_structured
from app.models import Answer, InterviewSession, Profile, Question, utcnow
from app.services.demo_data import SAMPLE_JD, SAMPLE_RESUME, STRONG_ANSWERS, WEAK_ANSWERS
from app.services.interview_service import CATEGORY_ORDER
from app.services.scoring import compute_average

SEED_PLAN = [
    # (days ago, job title, company, answers, number answered)
    (21, "Backend Engineer", "Contoso Freight", WEAK_ANSWERS, 8),
    (9, "Platform Engineer", "Contoso Freight", STRONG_ANSWERS, 8),
    (2, "Software Engineer, APIs", "Fabrikam Cloud", STRONG_ANSWERS, 3),
]


async def seed_demo_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    provider = DemoProvider()
    db.add(Profile(id=user_id, display_name="Demo user"))

    analysis = (
        await run_structured(
            provider,
            operation="resume_job_analysis",
            system_prompt=resume_job_analysis.SYSTEM_PROMPT,
            payload=resume_job_analysis.build_payload(
                resume_text=SAMPLE_RESUME,
                jd_text=SAMPLE_JD,
                job_title="Backend Engineer",
                role_type="Software Engineering",
                seniority_hint="mid",
            ),
            model_cls=ResumeJobAnalysis,
            max_retries=0,
        )
    ).value

    for days_ago, title, company, answers, answered in SEED_PLAN:
        created = utcnow() - timedelta(days=days_ago)
        qset = (
            await run_structured(
                provider,
                operation="question_generation",
                system_prompt=question_generation.SYSTEM_PROMPT,
                payload=question_generation.build_payload(
                    resume_text=SAMPLE_RESUME,
                    jd_text=SAMPLE_JD,
                    job_title=title,
                    company=company,
                    role_type="Software Engineering",
                    seniority="mid",
                    difficulty=None,
                    analysis=analysis.model_dump(),
                ),
                model_cls=QuestionSet,
                max_retries=0,
            )
        ).value
        session = InterviewSession(
            user_id=user_id,
            job_title=title,
            company=company,
            jd_text=SAMPLE_JD,
            resume_text=SAMPLE_RESUME,
            role_type="software_engineering",
            seniority_level="mid",
            status="completed" if answered == 8 else "in_progress",
            analysis_json=analysis.model_dump(),
            ai_provider=provider.name,
            ai_model=provider.model,
            is_demo=True,
            created_at=created,
            updated_at=created,
            completed_at=created + timedelta(minutes=40) if answered == 8 else None,
        )
        db.add(session)
        await db.flush()
        ordered = sorted(qset.questions, key=lambda q: CATEGORY_ORDER.get(q.category, 9))
        for i, gq in enumerate(ordered):
            question = Question(
                session_id=session.id,
                question_text=gq.question_text,
                category=gq.category,
                difficulty=gq.difficulty,
                why_this_question=gq.why_this_question,
                source_context=list(gq.source_context),
                evaluation_focus=list(gq.evaluation_focus),
                order_index=i,
                created_at=created,
            )
            db.add(question)
            await db.flush()
            if i >= answered:
                continue
            text = answers[i % len(answers)]
            ev = (
                await run_structured(
                    provider,
                    operation="answer_evaluation",
                    system_prompt=answer_evaluation.SYSTEM_PROMPT,
                    payload=answer_evaluation.build_payload(
                        question_text=gq.question_text,
                        category=gq.category,
                        evaluation_focus=list(gq.evaluation_focus),
                        job_title=title,
                        role_type="software_engineering",
                        seniority="mid",
                        resume_excerpt="",
                        jd_excerpt="",
                        answer_text=text,
                    ),
                    model_cls=AnswerEvaluation,
                    max_retries=0,
                )
            ).value
            at = created + timedelta(minutes=4 * (i + 1))
            db.add(
                Answer(
                    question_id=question.id,
                    session_id=session.id,
                    user_id=user_id,
                    answer_text=text,
                    evaluation_status="completed",
                    evaluation_attempts=1,
                    score_clarity=ev.clarity,
                    score_specificity=ev.specificity,
                    score_result_orientation=ev.result_orientation,
                    score_relevance=ev.relevance,
                    overall_score=compute_average(
                        ev.clarity, ev.specificity, ev.result_orientation, ev.relevance
                    ),
                    feedback_json={
                        **{k: v for k, v in ev.model_dump().items() if k.endswith("_reason")},
                        "overall_feedback": ev.overall_feedback,
                        "one_thing_to_fix": ev.one_thing_to_fix,
                        "provider": provider.name,
                        "model": provider.model,
                        "prompt_version": answer_evaluation.VERSION,
                        "is_demo": True,
                    },
                    answered_at=at,
                    evaluated_at=at,
                    updated_at=at,
                )
            )
    await db.commit()
