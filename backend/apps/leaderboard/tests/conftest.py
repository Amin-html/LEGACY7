from decimal import Decimal

import pytest
from django.utils import timezone

from apps.contests.models import Contest, ContestJury
from apps.contests.tests.conftest import category, make_contest  # noqa: F401
from apps.judging.models import Evaluation
from apps.submissions.models import Submission


@pytest.fixture
def organizer(make_user):
    return make_user(role="organizer", is_email_verified=True)


@pytest.fixture
def make_finished(make_contest, make_user, organizer):
    """Завершённый конкурс с двумя назначенными судьями (contest.judges)."""

    def factory(judges=2, **kw):
        kw.setdefault("status", Contest.Status.FINISHED)
        contest = make_contest(organizer=organizer, **kw)
        contest.judges = [make_user(role="jury") for _ in range(judges)]
        for judge in contest.judges:
            ContestJury.objects.create(contest=contest, judge=judge)
        return contest

    return factory


@pytest.fixture
def rate(db):
    """Создаёт работу автора и подтверждённые оценки судей: rate(contest, author, 8, 6)."""

    def factory(
        contest,
        author,
        *totals,
        status=Submission.Status.ACCEPTED,
        eval_status=Evaluation.Status.FINAL,
    ):
        sub = Submission.objects.create(
            contest=contest,
            author=author,
            title=f"Работа {author.username}",
            description="Описание",
            status=status,
            submitted_at=timezone.now(),
        )
        for judge, total in zip(contest.judges, totals):
            Evaluation.objects.create(
                submission=sub,
                judge=judge,
                total=Decimal(str(total)),
                status=eval_status,
                finalized_at=timezone.now(),
            )
        return sub

    return factory