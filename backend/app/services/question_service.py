"""Resume/JD analysis and tailored question generation."""

import uuid
from dataclasses import dataclass

from app.ai.prompts import question_generation, resume_job_analysis
from app.ai.schemas import QuestionSet, ResumeJobAnalysis
from app.schemas import ROLE_LABELS, SessionCreate
from app.services.ai_gateway import AIGateway, redact_contact_details


@dataclass
class GeneratedInterview:
    analysis: ResumeJobAnalysis
    questions: QuestionSet
    seniority: str
    model: str


class QuestionService:
    def __init__(self, gateway: AIGateway) -> None:
        self.gateway = gateway

    async def generate(self, user_id: uuid.UUID, data: SessionCreate) -> GeneratedInterview:
        resume = redact_contact_details(data.resume_text)
        jd = redact_contact_details(data.jd_text)
        role_label = ROLE_LABELS[data.role_type]

        analysis = (
            await self.gateway.run(
                user_id=user_id,
                operation="resume_job_analysis",
                system_prompt=resume_job_analysis.SYSTEM_PROMPT,
                payload=resume_job_analysis.build_payload(
                    resume_text=resume,
                    jd_text=jd,
                    job_title=data.job_title,
                    role_type=role_label,
                    seniority_hint=data.seniority_level,
                ),
                model_cls=ResumeJobAnalysis,
                temperature=0.1,
            )
        ).value

        # An explicit user choice wins over the inferred seniority.
        seniority = data.seniority_level or analysis.inferred_seniority

        generation = await self.gateway.run(
            user_id=user_id,
            operation="question_generation",
            system_prompt=question_generation.SYSTEM_PROMPT,
            payload=question_generation.build_payload(
                resume_text=resume,
                jd_text=jd,
                job_title=data.job_title,
                company=data.company,
                role_type=role_label,
                seniority=seniority,
                difficulty=data.difficulty,
                analysis=analysis.model_dump(),
            ),
            model_cls=QuestionSet,
            temperature=0.6,
        )

        return GeneratedInterview(
            analysis=analysis, questions=generation.value, seniority=seniority, model=generation.model
        )
