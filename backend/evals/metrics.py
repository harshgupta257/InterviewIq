"""Agreement metrics between AI scores and human labels (integer 1-5 ratings)."""

from collections import Counter
from collections.abc import Sequence

CATEGORIES = (1, 2, 3, 4, 5)


def mean_absolute_error(human: Sequence[int], ai: Sequence[int]) -> float:
    _check(human, ai)
    return sum(abs(h - a) for h, a in zip(human, ai, strict=True)) / len(human)


def exact_agreement(human: Sequence[int], ai: Sequence[int]) -> float:
    _check(human, ai)
    return sum(h == a for h, a in zip(human, ai, strict=True)) / len(human)


def within_one(human: Sequence[int], ai: Sequence[int]) -> float:
    _check(human, ai)
    return sum(abs(h - a) <= 1 for h, a in zip(human, ai, strict=True)) / len(human)


def quadratic_weighted_kappa(human: Sequence[int], ai: Sequence[int]) -> float | None:
    """Cohen's kappa with quadratic weights. Returns None when undefined (no variance)."""
    _check(human, ai)
    n = len(human)
    k = len(CATEGORIES)
    idx = {c: i for i, c in enumerate(CATEGORIES)}
    observed = [[0.0] * k for _ in range(k)]
    for h, a in zip(human, ai, strict=True):
        observed[idx[h]][idx[a]] += 1
    hist_h, hist_a = Counter(human), Counter(ai)
    num = den = 0.0
    for i, ci in enumerate(CATEGORIES):
        for j, cj in enumerate(CATEGORIES):
            w = ((i - j) ** 2) / ((k - 1) ** 2)
            expected = hist_h[ci] * hist_a[cj] / n
            num += w * observed[i][j]
            den += w * expected
    if den == 0:
        return None
    return 1 - num / den


def _check(human: Sequence[int], ai: Sequence[int]) -> None:
    if len(human) != len(ai) or not human:
        raise ValueError("Score lists must be non-empty and the same length.")
    for v in (*human, *ai):
        if v not in CATEGORIES:
            raise ValueError(f"Scores must be integers 1-5, got {v!r}.")
