from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contests.models import ContestJury
from apps.contests.tests.conftest import category, make_contest  # noqa: F401
from apps.judging.tests.conftest import contest, criteria, judge, make_sub, organizer, sub  # noqa: F401
from apps.notifications.models import Notification
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
K = Notification.Kind
S = Submission.Status
MODERATE = "manage-submission-moderate"


@pytest.fixture
def org_api(api, organizer):
    api.force_authenticate(organizer)
    return api


@pytest.fixture
def closed(make_contest, organizer, judge, make_sub):
    """Опубликованный конкурс с прошедшим дедлайном: принятая работа и судья есть."""
    now = timezone.now()
    c = make_contest(
        organizer=organizer, starts_at=now - timedelta(days=10), deadline=now - timedelta(days=1)
    )
    ContestJury.objects.create(contest=c, judge=judge)
    make_sub(c)
    return c


# ---------- модерация ----------

def test_accepting_a_work_notifies_its_author(org_api, contest, make_sub):
    work = make_sub(contest, status=S.SUBMITTED)
    assert org_api.post(reverse(MODERATE, args=[work.pk]), {"action": "accept"}, format="json").status_code == 200
    n = Notification.objects.get(user=work.author)
    assert n.kind == K.SUBMISSION_ACCEPTED
    assert n.is_read is False
    assert n.data == {"contest_slug": contest.slug, "submission_id": work.id}
    assert contest.title in n.text


def test_rejecting_a_work_notifies_with_the_reason(org_api, contest, make_sub):
    work = make_sub(contest, status=S.SUBMITTED)
    body = {"action": "reject", "comment": "Не по теме"}
    assert org_api.post(reverse(MODERATE, args=[work.pk]), body, format="json").status_code == 200
    n = Notification.objects.get(user=work.author)
    assert n.kind == K.SUBMISSION_REJECTED
    assert "Не по теме" in n.text


def test_failed_moderation_sends_nothing(org_api, contest, make_sub, api, make_user):
    work = make_sub(contest, status=S.SUBMITTED)
    url = reverse(MODERATE, args=[work.pk])
    assert org_api.post(url, {"action": "reject"}, format="json").status_code == 400  # без причины
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    assert api.post(url, {"action": "accept"}, format="json").status_code == 404  # чужой конкурс
    assert Notification.objects.count() == 0


# ---------- жюри ----------

def test_assigning_a_judge_notifies_once(org_api, organizer, make_contest, make_user):
    new_contest = make_contest(organizer=organizer)
    new_judge = make_user(role="jury")
    url = reverse("manage-contest-jury", args=[new_contest.pk])
    assert org_api.post(url, {"email": new_judge.email}, format="json").status_code == 201
    assert org_api.post(url, {"email": new_judge.email}, format="json").status_code == 200
    items = Notification.objects.filter(user=new_judge)
    assert items.count() == 1
    assert items[0].kind == K.JURY_ASSIGNED
    assert items[0].data == {"contest_slug": new_contest.slug}


def test_failed_assignment_sends_nothing(org_api, organizer, make_contest, make_user):
    new_contest = make_contest(organizer=organizer)
    url = reverse("manage-contest-jury", args=[new_contest.pk])
    org_api.post(url, {"email": make_user().email}, format="json")  # не судья
    org_api.post(url, {"email": "nobody@example.com"}, format="json")
    assert Notification.objects.count() == 0


def test_starting_judging_notifies_every_judge(org_api, closed, judge, make_user):
    second = make_user(role="jury")
    ContestJury.objects.create(contest=closed, judge=second)
    r = org_api.post(reverse("manage-contest-start-judging", args=[closed.pk]))
    assert r.status_code == 200
    users = set(Notification.objects.filter(kind=K.JUDGING_STARTED).values_list("user_id", flat=True))
    assert users == {judge.id, second.id}


def test_refused_start_sends_nothing(org_api, closed, make_sub):
    make_sub(closed, status=S.SUBMITTED)  # работа ждёт модерации
    assert org_api.post(reverse("manage-contest-start-judging", args=[closed.pk])).status_code == 400
    assert Notification.objects.count() == 0


# ---------- завершение ----------

def test_finishing_notifies_only_authors_of_accepted_works(org_api, contest, make_sub, judge):
    a, b = make_sub(contest), make_sub(contest)
    rejected = make_sub(contest, status=S.REJECTED)
    r = org_api.post(reverse("manage-contest-finish", args=[contest.pk]), {"force": True}, format="json")
    assert r.status_code == 200
    items = Notification.objects.all()
    assert {n.user_id for n in items} == {a.author_id, b.author_id}
    assert all(n.kind == K.RESULTS_PUBLISHED for n in items)
    mine = Notification.objects.get(user=a.author)
    assert mine.data == {"contest_slug": contest.slug, "submission_id": a.id}
    assert not Notification.objects.filter(user=rejected.author).exists()
    assert not Notification.objects.filter(user=judge).exists()


def test_refused_finish_sends_nothing(org_api, contest, sub):
    r = org_api.post(reverse("manage-contest-finish", args=[contest.pk]))
    assert r.status_code == 400  # оценки не подтверждены
    assert Notification.objects.count() == 0