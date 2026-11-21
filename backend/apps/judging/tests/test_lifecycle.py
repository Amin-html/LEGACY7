from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contests.models import Contest, ContestJury
from apps.judging.models import Evaluation
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
S = Submission.Status
START = "manage-contest-start-judging"
FINISH = "manage-contest-finish"


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


def start(api, contest):
    return api.post(reverse(START, args=[contest.pk]))


def finish(api, contest, **body):
    return api.post(reverse(FINISH, args=[contest.pk]), body, format="json")


def assert_start_refused(api, contest):
    r = start(api, contest)
    assert r.status_code == 400
    contest.refresh_from_db()
    assert contest.status == Contest.Status.PUBLISHED


# ---------- старт оценивания ----------

def test_start_judging_opens_work_for_judges(org_api, closed, judge):
    r = start(org_api, closed)
    assert r.status_code == 200, r.data
    assert r.data["status"] == "judging"
    org_api.force_authenticate(judge)
    listing = org_api.get(reverse("jury-contest-list"))
    assert [c["id"] for c in listing.data] == [closed.id]


def test_cannot_start_before_deadline(org_api, closed):
    closed.deadline = timezone.now() + timedelta(days=3)
    closed.save()
    assert_start_refused(org_api, closed)


def test_cannot_start_with_works_waiting_for_moderation(org_api, closed, make_sub):
    make_sub(closed, status=S.SUBMITTED)
    assert_start_refused(org_api, closed)


def test_cannot_start_without_accepted_works(org_api, closed):
    closed.submissions.all().delete()
    assert_start_refused(org_api, closed)


def test_cannot_start_without_jury(org_api, closed):
    closed.jury_assignments.all().delete()
    assert_start_refused(org_api, closed)


def test_only_published_contest_can_start(org_api, closed):
    closed.status = Contest.Status.DRAFT
    closed.save()
    assert start(org_api, closed).status_code == 400


def test_start_is_blocked_for_foreign_organizer_and_participants(api, make_user, closed):
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    assert start(api, closed).status_code == 404
    api.force_authenticate(make_user(role="participant"))
    assert start(api, closed).status_code == 403
    closed.refresh_from_db()
    assert closed.status == Contest.Status.PUBLISHED


# ---------- завершение ----------

def test_finish_needs_all_evaluations(org_api, contest, sub):
    r = finish(org_api, contest)
    assert r.status_code == 400
    assert r.data["missing"] == 1
    contest.refresh_from_db()
    assert contest.status == Contest.Status.JUDGING


def test_finish_when_everything_is_confirmed(org_api, contest, sub, judge):
    Evaluation.objects.create(submission=sub, judge=judge, status=Evaluation.Status.FINAL)
    r = finish(org_api, contest)
    assert r.status_code == 200, r.data
    assert r.data["status"] == "finished"


def test_force_finish(org_api, contest, sub):
    r = finish(org_api, contest, force=True)
    assert r.status_code == 200
    assert r.data["status"] == "finished"


def test_only_judging_contest_can_be_finished(org_api, closed):
    assert finish(org_api, closed).status_code == 400


def test_finish_is_blocked_for_foreign_organizer_and_participants(api, make_user, contest, sub):
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    assert finish(api, contest, force=True).status_code == 404
    api.force_authenticate(make_user(role="participant"))
    assert finish(api, contest, force=True).status_code == 403
    contest.refresh_from_db()
    assert contest.status == Contest.Status.JUDGING


def test_judges_lose_access_after_finish(org_api, contest, sub, judge):
    assert finish(org_api, contest, force=True).status_code == 200
    org_api.force_authenticate(judge)
    assert org_api.get(reverse("jury-submission-detail", args=[sub.pk])).status_code == 404