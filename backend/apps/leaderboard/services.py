from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, F

from apps.contests.models import Contest
from apps.judging.models import Evaluation
from apps.submissions.models import Submission

POINTS_PER_SCORE = 100  # балл 8.00 даёт 800 очков
CENT = Decimal("0.01")


def fmt(value):
    return f"{value:.2f}"


def average(values):
    """Среднее по шкале с двумя знаками или None, если значений нет."""
    if not values:
        return None
    return (Decimal(sum(values)) / len(values)).quantize(CENT, rounding=ROUND_HALF_UP)


def points_for(score):
    return int((score * POINTS_PER_SCORE).to_integral_value(rounding=ROUND_HALF_UP))


def rated_submissions(**filters):
    """Принятые работы завершённых конкурсов с итоговым баллом.

    Балл работы это среднее подтверждённых итогов судей, назначенных на конкурс.
    Черновики оценок и оценки снятых судей не учитываются.
    """
    rows = (
        Evaluation.objects.filter(
            status=Evaluation.Status.FINAL,
            submission__status=Submission.Status.ACCEPTED,
            submission__contest__status=Contest.Status.FINISHED,
            judge__jury_assignments__contest=F("submission__contest"),
            **filters,
        )
        .values(
            "submission_id",
            "submission__author_id",
            "submission__author__username",
            "submission__contest_id",
        )
        .annotate(score=Avg("total"))
    )
    return [
        {
            "submission_id": r["submission_id"],
            "user_id": r["submission__author_id"],
            "username": r["submission__author__username"],
            "contest_id": r["submission__contest_id"],
            "score": r["score"].quantize(CENT, rounding=ROUND_HALF_UP),
        }
        for r in rows
    ]


def assign_places(items, key):
    """Места по убыванию. При равенстве место общее: 1, 1, 3."""
    ordered = sorted(items, key=lambda i: (-i[key], i["username"]))
    place, previous = 0, None
    for index, item in enumerate(ordered, start=1):
        if item[key] != previous:
            place, previous = index, item[key]
        item["place"] = place
    return ordered


def build_leaderboard(category=None):
    filters = {"submission__contest__category": category} if category else {}
    totals = {}
    for row in rated_submissions(**filters):
        entry = totals.setdefault(
            row["user_id"],
            {"user_id": row["user_id"], "username": row["username"], "points": 0, "contest_ids": set()},
        )
        entry["points"] += points_for(row["score"])
        entry["contest_ids"].add(row["contest_id"])
    items = [
        {
            "user_id": e["user_id"],
            "username": e["username"],
            "points": e["points"],
            "contests": len(e["contest_ids"]),
        }
        for e in totals.values()
    ]
    return assign_places(items, "points")


def contest_results(contest):
    items = [
        {
            "submission_id": r["submission_id"],
            "username": r["username"],
            "score": r["score"],
            "points": points_for(r["score"]),
        }
        for r in rated_submissions(submission__contest=contest)
    ]
    return assign_places(items, "score")