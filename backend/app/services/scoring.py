"""Deterministic score calculation. The AI never supplies the overall score.

average    = (clarity + specificity + result_orientation + relevance) / 4
percentage = average / 5 * 100
"""

from decimal import ROUND_HALF_UP, Decimal

DIMENSIONS = ("clarity", "specificity", "result_orientation", "relevance")


def compute_average(clarity: int, specificity: int, result_orientation: int, relevance: int) -> Decimal:
    scores = (clarity, specificity, result_orientation, relevance)
    for s in scores:
        if not isinstance(s, int) or isinstance(s, bool) or not 1 <= s <= 5:
            raise ValueError(f"Scores must be integers between 1 and 5, got {s!r}.")
    return (Decimal(sum(scores)) / Decimal(4)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def to_percentage(average: Decimal | float) -> float:
    return float(
        (Decimal(str(average)) / Decimal(5) * Decimal(100)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    )
