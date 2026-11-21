from decimal import ROUND_HALF_UP, Decimal


def compute_total(criteria, scores):
    """Итог по шкале 0-10 с учётом весов.

    criteria: список JudgingCriterion, scores: {id критерия: балл}.
    """
    total_weight = sum((c.weight for c in criteria), Decimal(0))
    weighted = sum(
        (Decimal(scores[c.id]) / c.max_score * c.weight for c in criteria), Decimal(0)
    )
    return (weighted / total_weight * 10).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)