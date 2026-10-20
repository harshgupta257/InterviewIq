"""Offline demo provider (AI_PROVIDER=demo).

Produces deterministic, rule-based output so the full product can be explored without
any API key. It is NOT an AI model and it is never used as a fallback when a real
provider fails. Sessions created with it are flagged `is_demo=True` and every piece of
its output is labelled as demo content in the UI.
"""

import json
import re
from typing import Any

from app.ai.provider import AIProvider, AIRequest, AIResult, AIUsage

KNOWN_SKILLS = [
    "Python",
    "Java",
    "TypeScript",
    "JavaScript",
    "Go",
    "Rust",
    "C++",
    "C#",
    "SQL",
    "Scala",
    "React",
    "Node.js",
    "FastAPI",
    "Django",
    "Flask",
    "Spring",
    "GraphQL",
    "REST",
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Kafka",
    "Spark",
    "PySpark",
    "Airflow",
    "dbt",
    "Databricks",
    "Snowflake",
    "BigQuery",
    "AWS",
    "GCP",
    "Azure",
    "Docker",
    "Kubernetes",
    "Terraform",
    "CI/CD",
    "Git",
    "Linux",
    "Pandas",
    "NumPy",
    "scikit-learn",
    "PyTorch",
    "TensorFlow",
    "LLM",
    "RAG",
    "NLP",
    "Machine Learning",
    "Tableau",
    "Power BI",
    "Excel",
    "A/B testing",
    "Statistics",
    "ETL",
    "Microservices",
    "System Design",
]
DEMO_PREFIX = "[Demo heuristic] "


def _find_skills(text: str) -> list[str]:
    found = []
    for skill in KNOWN_SKILLS:
        pattern = r"(?<![A-Za-z])" + re.escape(skill) + r"(?![A-Za-z])"
        if re.search(pattern, text, re.IGNORECASE):
            found.append(skill)
    return found


def _find_projects(resume: str) -> list[dict[str, Any]]:
    projects = []
    for line in resume.splitlines():
        stripped = line.strip(" -*•\t")
        if re.match(
            r"^(built|developed|designed|implemented|created|led|migrated|automated)\b",
            stripped,
            re.IGNORECASE,
        ):
            projects.append(
                {"name": stripped[:80], "summary": stripped[:300], "technologies": _find_skills(stripped)[:5]}
            )
    return projects[:6]


def _seniority(resume: str, hint: str | None) -> str:
    if hint and hint in {"intern", "junior", "mid", "senior", "staff", "lead"}:
        return hint
    years = [int(y) for y in re.findall(r"(\d{1,2})\+?\s+years", resume, re.IGNORECASE)]
    top = max(years, default=0)
    if top >= 8:
        return "senior"
    if top >= 3:
        return "mid"
    return "junior"


def _analysis(p: dict[str, Any]) -> dict[str, Any]:
    resume, jd = p.get("candidate_resume", ""), p.get("job_description", "")
    resume_skills, jd_skills = _find_skills(resume), _find_skills(jd)
    matched = [s for s in jd_skills if s in resume_skills]
    gaps = [s for s in jd_skills if s not in resume_skills]
    hint = p.get("seniority_hint")
    return {
        "candidate_summary": DEMO_PREFIX
        + "Keyword-based summary. Detected skills: "
        + (", ".join(resume_skills[:8]) or "none recognised")
        + ".",
        "candidate_skills": resume_skills,
        "candidate_tools": resume_skills,
        "candidate_projects": _find_projects(resume),
        "years_experience_estimate": None,
        "job_responsibilities": [
            line.strip(" -*•\t")[:200] for line in jd.splitlines() if line.strip().startswith(("-", "*", "•"))
        ][:8],
        "required_skills": jd_skills,
        "preferred_qualifications": [],
        "matched_skills": matched,
        "skill_gaps": gaps,
        "inferred_seniority": _seniority(resume, hint if hint != "not provided" else None),
        "inferred_role_type": p.get("role_category") or "Software Engineering",
    }


def _questions(p: dict[str, Any]) -> dict[str, Any]:
    a = p.get("structured_analysis") or {}
    title = p.get("target_job_title", "this role")
    company = p.get("company")
    company_txt = company if company and company != "not provided" else "this team"
    matched = a.get("matched_skills") or a.get("candidate_skills") or ["your main language"]
    gaps = a.get("skill_gaps") or []
    projects = a.get("candidate_projects") or []
    s1 = matched[0]
    s2 = matched[1] if len(matched) > 1 else (gaps[0] if gaps else "testing")
    p1 = projects[0]["name"] if projects else "the most significant project on your resume"
    p2 = projects[1]["name"] if len(projects) > 1 else "a project where you owned a key decision"
    role = (p.get("role_category") or "").lower()
    engineering = any(k in role for k in ("software", "engineering", "ai/ml", "deployed"))
    design_or_case = (
        {
            "question_text": f"Design a production service for the core workflow described in the {title} "
            f"job description. Walk through the API, data model, failure handling and how you "
            f"would scale it.",
            "category": "system_design",
            "source_context": ["JD: role responsibilities", f"Resume: {s1}"],
            "evaluation_focus": ["Architecture trade-offs", "Reliability", "Scalability reasoning"],
        }
        if engineering
        else {
            "question_text": f"A key metric for {company_txt} dropped 15% week over week. How would you "
            f"investigate the cause and decide what to report to stakeholders?",
            "category": "case_study",
            "source_context": ["JD: analytical responsibilities"],
            "evaluation_focus": ["Structured problem solving", "Hypothesis testing", "Communication"],
        }
    )
    qs = [
        {
            "question_text": f"Your resume mentions {s1}. Explain a non-trivial problem you solved with "
            f"{s1}, the alternatives you considered, and how you verified the solution was correct.",
            "category": "technical",
            "source_context": [f"Resume: {s1}", f"JD: {s1}"],
            "evaluation_focus": ["Technical depth", "Trade-off reasoning", "Validation"],
        },
        {
            "question_text": f"The role calls for {s2}. Describe how you would apply it in this position, "
            f"including common pitfalls and how you would avoid them.",
            "category": "technical",
            "source_context": [f"JD: {s2}"],
            "evaluation_focus": ["Practical knowledge", "Awareness of pitfalls"],
        },
        {
            "question_text": f"Walk me through '{p1}'. What was your specific ownership, what was the "
            f"hardest technical decision, and what would you change today?",
            "category": "project_deepdive",
            "source_context": [f"Resume: {p1}"],
            "evaluation_focus": ["Ownership", "Decision making", "Reflection"],
        },
        {
            "question_text": f"Regarding '{p2}': how did you measure whether it succeeded, and what did "
            f"the results tell you?",
            "category": "project_deepdive",
            "source_context": [f"Resume: {p2}"],
            "evaluation_focus": ["Outcome measurement", "Impact", "Honesty about limitations"],
        },
        {
            "question_text": "Tell me about a time you disagreed with a teammate or stakeholder about a "
            "technical approach. How did you resolve it and what was the outcome?",
            "category": "behavioral",
            "source_context": ["JD: collaboration with cross-functional teams"],
            "evaluation_focus": ["Collaboration", "Influence", "Outcome"],
        },
        {
            "question_text": "Describe a situation where a deadline was at risk because of something you "
            "underestimated. What did you do, and what did you learn?",
            "category": "behavioral",
            "source_context": ["JD: delivery in a fast-paced environment"],
            "evaluation_focus": ["Ownership", "Communication under pressure", "Learning"],
        },
        design_or_case,
        {
            "question_text": f"Why are you interested in the {title} role at {company_txt}, and how does "
            f"it fit the direction you want your career to take?",
            "category": "motivation",
            "source_context": [f"JD: {title}"],
            "evaluation_focus": ["Role fit", "Specific motivation", "Self-awareness"],
        },
    ]
    for q in qs:
        q["why_this_question"] = (
            DEMO_PREFIX
            + "Template question filled with keywords detected in your resume and the job description."
        )
        q["difficulty"] = "medium"
    return {"questions": qs}


def _clamp(v: float) -> int:
    return max(1, min(5, round(v)))


def _evaluation(p: dict[str, Any]) -> dict[str, Any]:
    answer = p.get("candidate_answer", "")
    question = p.get("interview_question", "")
    words = re.findall(r"\w+", answer)
    n = len(words)
    sentences = max(1, len(re.findall(r"[.!?](\s|$)", answer)))
    numbers = len(re.findall(r"\d", answer))
    q_terms = {w.lower() for w in re.findall(r"[A-Za-z]{5,}", question)}
    overlap = len(q_terms & {w.lower() for w in words}) / max(1, len(q_terms))
    outcome_words = len(
        re.findall(
            r"\b(result|impact|improv|reduc|increas|learn|lesson|outcome|so that|dropp|faster|saved|met|achiev|avoid|trade-off|validat|verif|measur)\w*",
            answer,
            re.IGNORECASE,
        )
    )
    tech_terms = len(_find_skills(answer))

    clarity = _clamp(1.5 + min(n, 200) / 60 + (1 if 8 <= n / sentences <= 28 else 0))
    specificity = _clamp(1 + min(numbers, 4) * 0.5 + min(tech_terms, 4) * 0.5 + (1 if n > 120 else 0))
    result = _clamp(1.5 + min(outcome_words, 5) * 0.8)
    relevance = _clamp(2 + overlap * 6 + (1 if n > 60 else 0))
    return {
        "clarity": clarity,
        "clarity_reason": f"{DEMO_PREFIX}Based on length ({n} words) and average sentence length.",
        "specificity": specificity,
        "specificity_reason": f"{DEMO_PREFIX}Counted {numbers} digits and {tech_terms} recognised technical terms.",
        "result_orientation": result,
        "result_orientation_reason": f"{DEMO_PREFIX}Found {outcome_words} outcome-related phrases (e.g. 'result', 'improved').",
        "relevance": relevance,
        "relevance_reason": f"{DEMO_PREFIX}About {round(overlap * 100)}% of the question's key terms appear in your answer.",
        "overall_feedback": f"{DEMO_PREFIX}This score comes from simple text statistics, not an AI review. "
        "Configure a real AI provider to receive genuine, answer-specific feedback.",
        "one_thing_to_fix": "Add one concrete example with a measurable or observable outcome."
        if result < 4
        else "Tighten the structure so the key point comes first.",
    }


def _rewrite(p: dict[str, Any]) -> dict[str, Any]:
    original = (p.get("original_answer") or "").strip()
    category = p.get("question_category")
    if category == "behavioral":
        body = (
            "Situation: [Briefly describe the context and why it mattered.]\n\n"
            "Task: [State what you were specifically responsible for.]\n\n"
            f"Action: {original[:600]}\n\n"
            "Result: [Describe the outcome you observed, with a measurement if you have one, "
            "and what you learned.]"
        )
    else:
        body = (
            "Approach: [State your overall approach in one sentence.]\n\n"
            f"Detail: {original[:700]}\n\n"
            "Trade-offs and validation: [Name the main alternative you considered, why you "
            "rejected it, and how you would verify the solution works.]"
        )
    return {
        "improved_answer": DEMO_PREFIX + "Structural template built around your own words.\n\n" + body,
        "improvements": [
            "Organised the answer into a clear structure.",
            "Added explicit slots for outcome and validation.",
        ],
        "missing_information": ["The concrete outcome or measurement", "The alternatives you considered"],
        "suggested_follow_up": "What would you do differently if you faced this again?",
    }


def _profile(p: dict[str, Any]) -> dict[str, Any]:
    resume = p.get("candidate_resume", "")
    skills = _find_skills(resume)
    titles = [
        line.split(",")[0].strip()[:80]
        for line in resume.splitlines()
        if re.search(r"\b(engineer|developer|analyst|scientist|intern|manager)\b", line, re.IGNORECASE)
        and len(line) < 120
    ][:4]
    level = _seniority(resume, None)
    base = titles[0] if titles else "Software Engineer"
    return {
        "summary": DEMO_PREFIX
        + "Keyword-based profile. Detected skills: "
        + (", ".join(skills[:8]) or "none recognised")
        + ".",
        "skills": skills,
        "tools": skills,
        "job_titles": titles,
        "education": [],
        "certifications": [],
        "projects": [x["name"] for x in _find_projects(resume)],
        "experience_level": level,
        "years_experience": None,
        "suggested_roles": [base],
    }


def _job_match(p: dict[str, Any]) -> dict[str, Any]:
    profile = p.get("candidate_profile") or {}
    have = {s.lower() for s in profile.get("skills", [])}
    matches = []
    for job in p.get("jobs", []):
        text = f"{job.get('title', '')} {job.get('listing_text', '')}"
        required = _find_skills(text)
        overlap = sum(1 for s in required if s.lower() in have)
        fit = max(1, min(5, 1 + overlap))
        short = len(job.get("listing_text", "")) < 400
        matches.append(
            {
                "job_ref": job["job_ref"],
                "required_skills": required,
                "experience_fit": 3,
                "role_alignment": fit,
                "responsibilities_fit": max(1, fit - 1),
                "relevant_experience": [],
                "reasons": [
                    DEMO_PREFIX
                    + f"{overlap} of {len(required)} recognised listing keywords appear in the profile."
                ],
                "improvements": ["Configure a real AI provider for a genuine assessment."],
                "gaps": ["Demo heuristic: only keyword overlap was checked."]
                + (["The listing text is short."] if short else []),
                "description_sufficient": not short,
            }
        )
    return {"matches": matches}


class DemoProvider(AIProvider):
    name = "demo"
    model = "demo-heuristic-v1"
    is_demo = True

    async def complete(self, request: AIRequest) -> AIResult:
        handlers = {
            "resume_job_analysis": _analysis,
            "question_generation": _questions,
            "answer_evaluation": _evaluation,
            "answer_rewriting": _rewrite,
            "resume_profile": _profile,
            "job_matching": _job_match,
        }
        output = handlers[request.operation](request.payload)
        return AIResult(text=json.dumps(output), usage=AIUsage(0, 0))
