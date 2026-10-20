"""Measure agreement between the AI evaluator and human-labelled scores.

Usage (from backend/):
    python -m evals.run_eval                       # uses AI_PROVIDER etc. from .env
    python -m evals.run_eval --dataset evals/dataset.jsonl --min-labelled 30

Only items with complete `human_scores` are evaluated. The script refuses to report
metrics when fewer than --min-labelled items are labelled, so unlabelled synthetic data
can never produce a misleading "agreement" number.

Results (per-item scores and a summary) are written to evals/results/<timestamp>/.
"""

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.ai.prompts import answer_evaluation
from app.ai.provider import build_provider
from app.ai.schemas import AnswerEvaluation
from app.ai.structured import run_structured
from app.core.config import get_settings
from evals.metrics import exact_agreement, mean_absolute_error, quadratic_weighted_kappa, within_one

DIMENSIONS = ("clarity", "specificity", "result_orientation", "relevance")
HERE = Path(__file__).parent


def load(path: Path) -> list[dict[str, Any]]:
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return items


def is_labelled(item: dict[str, Any]) -> bool:
    hs = item.get("human_scores") or {}
    return all(isinstance(hs.get(d), int) and 1 <= hs[d] <= 5 for d in DIMENSIONS)


async def score_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    settings = get_settings()
    provider = build_provider(settings)
    if provider.is_demo:
        print("WARNING: AI_PROVIDER=demo is a heuristic, not an AI model.", file=sys.stderr)
    results = []
    try:
        for item in items:
            payload = answer_evaluation.build_payload(
                question_text=item["question"],
                category=item.get("category", "technical"),
                evaluation_focus=item.get("evaluation_focus", []),
                job_title=item.get("job_title", "Software Engineer"),
                role_type=item.get("role_type", "software_engineering"),
                seniority=item.get("seniority"),
                resume_excerpt=item.get("candidate_context", ""),
                jd_excerpt=item.get("jd_excerpt", ""),
                answer_text=item["answer"],
            )
            try:
                out = await run_structured(
                    provider,
                    operation="answer_evaluation",
                    system_prompt=answer_evaluation.SYSTEM_PROMPT,
                    payload=payload,
                    model_cls=AnswerEvaluation,
                    max_retries=settings.ai_max_retries,
                    temperature=0.1,
                )
                ai = {d: getattr(out.value, d) for d in DIMENSIONS}
                results.append(
                    {
                        "id": item["id"],
                        "human": item["human_scores"],
                        "ai": ai,
                        "ai_reasons": {d: getattr(out.value, f"{d}_reason") for d in DIMENSIONS},
                    }
                )
            except Exception as exc:  # noqa: BLE001 - recorded, not hidden
                results.append({"id": item["id"], "error": type(exc).__name__})
    finally:
        await provider.aclose()
    return results


def summarise(results: list[dict[str, Any]], provider: str, model: str) -> dict[str, Any]:
    ok = [r for r in results if "ai" in r]
    summary: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "prompt_version": answer_evaluation.VERSION,
        "run_at": datetime.now(UTC).isoformat(),
        "sample_count": len(ok),
        "failed_items": len(results) - len(ok),
        "dimensions": {},
    }
    for d in DIMENSIONS:
        h = [r["human"][d] for r in ok]
        a = [r["ai"][d] for r in ok]
        if not h:
            continue
        kappa = quadratic_weighted_kappa(h, a)
        summary["dimensions"][d] = {
            "mae": round(mean_absolute_error(h, a), 3),
            "exact_agreement": round(exact_agreement(h, a), 3),
            "within_one": round(within_one(h, a), 3),
            "quadratic_weighted_kappa": round(kappa, 3) if kappa is not None else None,
            "mean_ai_minus_human": round(sum(x - y for x, y in zip(a, h, strict=True)) / len(h), 3),
        }
    # Largest disagreements, for error analysis.
    gaps = []
    for r in ok:
        for d in DIMENSIONS:
            diff = r["ai"][d] - r["human"][d]
            if abs(diff) >= 2:
                gaps.append({"id": r["id"], "dimension": d, "human": r["human"][d], "ai": r["ai"][d]})
    summary["large_disagreements"] = gaps
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=HERE / "dataset.jsonl")
    parser.add_argument("--min-labelled", type=int, default=30)
    args = parser.parse_args()

    items = load(args.dataset)
    labelled = [i for i in items if is_labelled(i)]
    print(f"{len(items)} items, {len(labelled)} with complete human labels.")
    if len(labelled) < args.min_labelled:
        print(
            f"Refusing to report agreement: need at least {args.min_labelled} labelled items. "
            "Fill in human_scores (see evals/README.md) and re-run.",
            file=sys.stderr,
        )
        return 2

    settings = get_settings()
    results = asyncio.run(score_items(labelled))
    summary = summarise(results, settings.ai_provider, settings.resolved_ai_model)

    out_dir = HERE / "results" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "items.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
