import pytest
from django.urls import reverse

from apps.contests.models import Contest
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
S = Submission.Status
MODERATE = "manage-submission-moderate"
LISTING = "manage-contest-submissions"
PUBLIC = "contest-submissions"


@pytest.fixture
def organizer(make_user):
    return make_user(role="organizer", is_email_verified=True)


@pytest.fixture
def org_api(api, organizer):
    api.force_authenticate(organizer)
    return api


@pytest.fixture
def contest(make_contest, organizer):
    return make_contest(organizer=organizer)


# ---------- модерация ----------

def test_organizer_accepts(org_api, contest, make_user, make_submission):
    sub = make_submission(make_user(), contest=contest)
    r = org_api.post(reverse(MODERATE, args=[sub.pk]), {"action": "accept"}, format="json")
    assert r.status_code == 200
    assert r.data["status"] == "accepted"
    sub.refresh_from_db()
    assert sub.status == S.ACCEPTED


def test_reject_requires_a_reason(org_api, contest, make_user, make_submission):
    sub = make_submission(make_user(), contest=contest)
    url = reverse(MODERATE, args=[sub.pk])
    assert org_api.post(url, {"action": "reject"}, format="json").status_code == 400
    assert org_api.post(url, {"action": "reject", "comment": "  "}, format="json").status_code == 400
    sub.refresh_from_db()
    assert sub.status == S.SUBMITTED

    r = org_api.post(url, {"action": "reject", "comment": "Не по теме"}, format="json")
    assert r.status_code == 200
    assert r.data["status"] == "rejected"
    assert r.data["moderation_comment"] == "Не по теме"


def test_unknown_action_is_rejected(org_api, contest, make_user, make_submission):
    sub = make_submission(make_user(), contest=contest)
    r = org_api.post(reverse(MODERATE, args=[sub.pk]), {"action": "delete"}, format="json")
    assert r.status_code == 400


def test_other_organizers_submission_is_404(api, make_user, make_submission):
    sub = make_submission(make_user())
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    r = api.post(reverse(MODERATE, args=[sub.pk]), {"action": "accept"}, format="json")
    assert r.status_code == 404
    sub.refresh_from_db()
    assert sub.status == S.SUBMITTED


def test_participant_cannot_moderate(api, make_user, contest, make_submission):
    author = make_user(role="participant")
    sub = make_submission(author, contest=contest)
    api.force_authenticate(author)  # даже автор не может принять свою работу
    r = api.post(reverse(MODERATE, args=[sub.pk]), {"action": "accept"}, format="json")
    assert r.status_code == 403


@pytest.mark.parametrize("current", [S.DRAFT, S.ACCEPTED, S.REJECTED])
def test_only_submitted_work_can_be_moderated(org_api, contest, make_user, make_submission, current):
    sub = make_submission(make_user(), contest=contest, status=current)
    r = org_api.post(reverse(MODERATE, args=[sub.pk]), {"action": "accept"}, format="json")
    assert r.status_code == 400
    sub.refresh_from_db()
    assert sub.status == current


def test_cannot_moderate_in_finished_contest(org_api, organizer, make_contest, make_user, make_submission):
    done = make_contest(organizer=organizer, status=Contest.Status.FINISHED)
    sub = make_submission(make_user(), contest=done)
    r = org_api.post(reverse(MODERATE, args=[sub.pk]), {"action": "accept"}, format="json")
    assert r.status_code == 400


# ---------- список для организатора ----------

def test_organizer_list_hides_drafts_and_filters_by_status(org_api, contest, make_user, make_submission):
    make_submission(make_user(), contest=contest, title="Подана")
    make_submission(make_user(), contest=contest, title="Принята", status=S.ACCEPTED)
    make_submission(make_user(), contest=contest, title="Черновик", status=S.DRAFT, submitted_at=None)
    url = reverse(LISTING, args=[contest.pk])

    titles = {s["title"] for s in org_api.get(url).data["results"]}
    assert titles == {"Подана", "Принята"}

    accepted = org_api.get(url, {"status": "accepted"}).data["results"]
    assert [s["title"] for s in accepted] == ["Принята"]


def test_organizer_list_has_username_but_no_email(org_api, contest, make_user, make_submission):
    author = make_user()
    make_submission(author, contest=contest)
    item = org_api.get(reverse(LISTING, args=[contest.pk])).data["results"][0]
    assert item["author"] == {"id": author.pk, "username": author.username}
    assert author.email not in str(item)


def test_other_organizer_cannot_list_foreign_contest(api, make_user, contest):
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    assert api.get(reverse(LISTING, args=[contest.pk])).status_code == 404


def test_participant_cannot_use_organizer_list(api, make_user, contest):
    api.force_authenticate(make_user(role="participant"))
    assert api.get(reverse(LISTING, args=[contest.pk])).status_code == 403


# ---------- публичная витрина ----------

def test_public_list_is_hidden_by_default(api, contest):
    assert api.get(reverse(PUBLIC, args=[contest.slug])).status_code == 404


def test_public_list_shows_only_accepted_without_email(api, make_contest, make_user, make_submission):
    contest = make_contest(public_submissions=True)
    author = make_user()
    make_submission(author, contest=contest, title="Принята", status=S.ACCEPTED)
    make_submission(make_user(), contest=contest, title="Подана")
    make_submission(make_user(), contest=contest, title="Отклонена", status=S.REJECTED)
    r = api.get(reverse(PUBLIC, args=[contest.slug]))
    assert r.status_code == 200
    assert [s["title"] for s in r.data["results"]] == ["Принята"]
    assert r.data["results"][0]["author"] == author.username
    assert author.email not in str(r.data)


def test_public_list_of_draft_contest_is_404(api, make_contest):
    hidden = make_contest(public_submissions=True, status=Contest.Status.DRAFT)
    assert api.get(reverse(PUBLIC, args=[hidden.slug])).status_code == 404