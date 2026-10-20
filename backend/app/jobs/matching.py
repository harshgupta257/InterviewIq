"""Deterministic match scoring.

The AI provides structured judgements (1-5 fit ratings and the skills a listing names);
this module turns them into a 0-100 alignment score with fixed weights, and computes skill
coverage itself from evidence in the resume, rather than trusting the model's list.

    score = 100 x (0.40 x skill_coverage + 0.25 x experience + 0.20 x role + 0.15 x responsibilities)

where each 1-5 rating is mapped to 0..1 as (r - 1) / 4. If the listing names no skills,
skill coverage is excluded and the remaining weights are rescaled.

The score estimates how well the resume aligns with the listing text. It is not a
probability of being hired.
"""

import re
from dataclasses import dataclass, field

from app.ai.schemas import JobMatchItem, ResumeProfile

WEIGHTS = {"skills": 0.40, "experience": 0.25, "role": 0.20, "responsibilities": 0.15}
SCORING_VERSION = "job_match_score/v1"

_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "nodejs": "node.js",
    "node": "node.js",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "gcp": "google cloud",
    "amazon web services": "aws",
    "sklearn": "scikit-learn",
    "pyspark": "spark",
}


def _norm(skill: str) -> str:
    s = re.sub(r"\s+", " ", skill.strip().lower())
    s = re.sub(r"[()]", "", s)
    return _ALIASES.get(s, s)


def _in_text(skill: str, text: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


@dataclass
class SkillCoverage:
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def ratio(self) -> float | None:
        total = len(self.matched) + len(self.missing)
        return len(self.matched) / total if total else None


def skill_coverage(required: list[str], profile: ResumeProfile, resume_text: str) -> SkillCoverage:
    """A required skill counts as matched only with evidence: listed in the extracted
    profile, or named in the resume text itself."""
    have = {_norm(s) for s in [*profile.skills, *profile.tools, *profile.certifications]}
    lowered = resume_text.lower()
    cov = SkillCoverage()
    seen: set[str] = set()
    for skill in required:
        key = _norm(skill)
        if not key or key in seen:
            continue
        seen.add(key)
        if key in have or _in_text(key, lowered) or _in_text(skill.strip().lower(), lowered):
            cov.matched.append(skill.strip())
        else:
            cov.missing.append(skill.strip())
    return cov


def _unit(rating: int) -> float:
    return (rating - 1) / 4


def compute_score(item: JobMatchItem, coverage: SkillCoverage) -> int:
    parts = {
        "experience": _unit(item.experience_fit),
        "role": _unit(item.role_alignment),
        "responsibilities": _unit(item.responsibilities_fit),
    }
    weights = dict(WEIGHTS)
    if coverage.ratio is None:
        weights.pop("skills")
    else:
        parts["skills"] = coverage.ratio
    total_w = sum(weights.values())
    score = sum(weights[k] * parts[k] for k in weights) / total_w
    return int(round(score * 100))


def score_label(score: int) -> str:
    if score >= 75:
        return "Strong match"
    if score >= 55:
        return "Good match"
    if score >= 35:
        return "Partial match"
    return "Weak match"
