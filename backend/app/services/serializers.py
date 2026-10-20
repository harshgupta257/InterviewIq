"""ORM -> API response conversion."""

from app.models import Answer, InterviewSession
from app.repositories.sessions import SessionStats
from app.schemas import (
    ROLE_LABELS,
    AnswerOut,
    DimensionScore,
    EvaluationOut,
    QuestionOut,
    RewriteOut,
    SessionDetail,
    SessionProgress,
    SessionSummary,
)
from app.services.scoring import to_percentage


def answer_out(answer: Answer) -> AnswerOut:
    evaluation = None
    fb = answer.feedback_json or {}
    if (
        answer.evaluation_status == "completed"
        and answer.overall_score is not None
        and answer.score_clarity is not None
        and answer.score_specificity is not None
        and answer.score_result_orientation is not None
        and answer.score_relevance is not None
    ):
        evaluation = EvaluationOut(
            clarity=DimensionScore(score=answer.score_clarity, reason=fb.get("clarity_reason", "")),
            specificity=DimensionScore(
                score=answer.score_specificity, reason=fb.get("specificity_reason", "")
            ),
            result_orientation=DimensionScore(
                score=answer.score_result_orientation, reason=fb.get("result_orientation_reason", "")
            ),
            relevance=DimensionScore(score=answer.score_relevance, reason=fb.get("relevance_reason", "")),
            overall_feedback=fb.get("overall_feedback", ""),
            one_thing_to_fix=fb.get("one_thing_to_fix", ""),
            average=float(answer.overall_score),
            percentage=to_percentage(answer.overall_score),
            is_demo=bool(fb.get("is_demo")),
            model=fb.get("model"),
        )
    rewrite = None
    rw = answer.rewrite_json
    if rw:
        rewrite = RewriteOut(
            improved_answer=rw.get("improved_answer", answer.ideal_answer or ""),
            improvements=rw.get("improvements", []),
            missing_information=rw.get("missing_information", []),
            suggested_follow_up=rw.get("suggested_follow_up", ""),
            generated_at=rw.get("generated_at"),
            is_demo=bool(rw.get("is_demo")),
        )
    return AnswerOut(
        id=answer.id,
        question_id=answer.question_id,
        session_id=answer.session_id,
        answer_text=answer.answer_text,
        evaluation_status=answer.evaluation_status,
        evaluation_error=answer.evaluation_error,
        evaluation=evaluation,
        rewrite=rewrite,
        answered_at=answer.answered_at,
        evaluated_at=answer.evaluated_at,
    )


def session_summary(session: InterviewSession, stats: SessionStats) -> SessionSummary:
    total = stats.total_questions
    return SessionSummary(
        id=session.id,
        job_title=session.job_title,
        company=session.company,
        role_type=session.role_type,
        role_label=ROLE_LABELS.get(session.role_type, session.role_type),
        seniority_level=session.seniority_level,
        status=session.status,
        is_demo=session.is_demo,
        created_at=session.created_at,
        completed_at=session.completed_at,
        total_questions=total,
        answered_count=stats.answered_count,
        evaluated_count=stats.evaluated_count,
        average_score=to_percentage(stats.average_overall) if stats.average_overall is not None else None,
        completion_pct=round(stats.answered_count / total * 100, 1) if total else 0.0,
    )


def session_detail(session: InterviewSession, stats: SessionStats) -> SessionDetail:
    questions = sorted(session.questions, key=lambda q: q.order_index)
    answered_ids = {a.question_id for a in session.answers}
    next_index = next((i for i, q in enumerate(questions) if q.id not in answered_ids), len(questions))
    order = {q.id: q.order_index for q in questions}
    answers = sorted(session.answers, key=lambda a: order.get(a.question_id, 0))
    summary = session_summary(session, stats)
    return SessionDetail(
        **summary.model_dump(),
        jd_text=session.jd_text,
        resume_text=session.resume_text,
        difficulty=session.difficulty,
        analysis=session.analysis_json,
        ai_provider=session.ai_provider,
        ai_model=session.ai_model,
        questions=[QuestionOut.model_validate(q) for q in questions],
        answers=[answer_out(a) for a in answers],
        progress=SessionProgress(
            total_questions=len(questions),
            answered_count=stats.answered_count,
            evaluated_count=stats.evaluated_count,
            failed_evaluations=stats.failed_count,
            current_question_index=next_index,
            is_complete=stats.total_questions > 0 and stats.evaluated_count == stats.total_questions,
        ),
    )
