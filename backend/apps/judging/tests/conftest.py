import pytest
from django.utils import timezone

from apps.contests.models import Contest, ContestJury, JudgingCriterion
from apps.contests.tests.conftest import category, make_contest  # noqa: F401
from apps.submissions.models import Submission


@pytest.fixture
def organizer(make_user):
    return make_user(role="organizer", is_email_verified=True)


@pytest.fixture
def judge(make_user):
    return make_user(role="jury", is_email_verified=True)


@pytest.fixture
def contest(make_contest, organizer, judge):
    """Конкурс в стадии оценивания: два критерия, один назначенный судья."""
    c = make_contest(organizer=organizer, status=Contest.Status.JUDGING)
    JudgingCriterion.objects.create(contest=c, title="Идея", max_score=10, weight=2)
    JudgingCriterion.objects.create(contest=c, title="Исполнение", max_score=5, weight=1)
    ContestJury.objects.create(contest=c, judge=judge)
    return c


@pytest.fixture
def criteria(contest):
    return list(contest.criteria.order_by("id"))


@pytest.fixture
def make_sub(db, make_user):
    def factory(contest, status=Submission.Status.ACCEPTED, **kw):
        return Submission.objects.create(
            contest=contest,
            author=make_user(role="participant"),
            title="Работа",
            description="Описание",
            status=status,
            submitted_at=timezone.now(),
            **kw,
        )

    return factory


@pytest.fixture
def sub(contest, make_sub):
    return make_sub(contest)


@pytest.fixture
def jury_api(api, judge):
    api.force_authenticate(judge)
    return api