import pytest

from evals.metrics import exact_agreement, mean_absolute_error, quadratic_weighted_kappa, within_one
from evals.run_eval import is_labelled, summarise


def test_basic_metrics() -> None:
    human, ai = [1, 2, 3, 4, 5], [1, 3, 3, 2, 5]
    assert mean_absolute_error(human, ai) == pytest.approx(0.6)
    assert exact_agreement(human, ai) == pytest.approx(0.6)
    assert within_one(human, ai) == pytest.approx(0.8)


def test_kappa_perfect_and_undefined() -> None:
    assert quadratic_weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5]) == pytest.approx(1.0)
    assert quadratic_weighted_kappa([3, 3, 3], [3, 3, 3]) is None


def test_metric_input_validation() -> None:
    with pytest.raises(ValueError):
        mean_absolute_error([1, 2], [1])
    with pytest.raises(ValueError):
        exact_agreement([0], [1])


def test_unlabelled_items_are_excluded() -> None:
    assert not is_labelled({"human_scores": {"clarity": None}})
    full = {"clarity": 3, "specificity": 4, "result_orientation": 2, "relevance": 5}
    assert is_labelled({"human_scores": full})


def test_summary_reports_large_disagreements() -> None:
    results = [
        {
            "id": "a",
            "human": {"clarity": 5, "specificity": 3, "result_orientation": 3, "relevance": 3},
            "ai": {"clarity": 2, "specificity": 3, "result_orientation": 3, "relevance": 3},
        },
        {"id": "b", "error": "AIServiceError"},
    ]
    s = summarise(results, "fake", "m")
    assert s["sample_count"] == 1 and s["failed_items"] == 1
    assert s["large_disagreements"] == [{"id": "a", "dimension": "clarity", "human": 5, "ai": 2}]


def test_shipped_dataset_has_30_unlabelled_items() -> None:
    import json
    from pathlib import Path

    lines = (
        (Path(__file__).parent.parent / "evals" / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
    )
    items = [json.loads(x) for x in lines if x.strip()]
    assert len(items) >= 30
    assert len({i["id"] for i in items}) == len(items)
