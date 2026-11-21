from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contests.models import Contest
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
LIST = "my-submission-list"
DETAIL = "my-submission-detail"
SUBMIT = "my-submission-submit"
S = Submission.Status


def body(contest, **over):
    data = {
        "contest": contest.slug,
        "title": "Моя работа",
        "description": "Описание",
        "link": "https://example.com/work",
    }
    data.update(over)
    return data


def close(contest):
    """Делает конкурс закрытым: дедлайн уже прошёл."""
    now = timezone.now()
    contest.starts_at = now - timedelta(days=30)
    contest.deadline = now - timedelta(days=1)
    contest.save()


def call(api, method, url, data=None):
    if method == "get":
        return api.get(url)
    return getattr(api, method)(url, data, format="json")


# ---------- доступ ----------

def test_anonymous_gets_401(api):
    assert api.get(reverse(LIST)).status_code == 401


@pytest.mark.parametrize("role", ["organizer", "jury"])
def test_other_roles_get_403(api, make_user, role):
    api.force_authenticate(make_user(role=role))
    assert api.get(reverse(LIST)).status_code == 403


# ---------- создание ----------

def test_create_draft(me, participant, make_contest):
    contest = make_contest(title="Спортивный кадр")
    r = me.post(reverse(LIST), body(contest), format="json")
    assert r.status_code == 201, r.data
    assert r.data["status"] == "draft"
    assert r.data["contest"] == contest.slug
    assert r.data["contest_title"] == "Спортивный кадр"
    assert r.data["can_edit"] is True
    assert Submission.objects.get(pk=r.data["id"]).author == participant


def test_server_fields_in_body_are_ignored(me, participant, make_user, make_contest):
    other = make_user()
    r = me.post(
        reverse(LIST),
        body(
            make_contest(),
            status="accepted",
            author=other.pk,
            moderation_comment="взлом",
            submitted_at="2020-01-01T00:00:00Z",
        ),
        format="json",
    )
    assert r.status_code == 201
    obj = Submission.objects.get(pk=r.data["id"])
    assert obj.status == S.DRAFT
    assert obj.author == participant
    assert obj.moderation_comment == ""
    assert obj.submitted_at is None


def test_one_submission_per_contest(me, make_contest):
    contest = make_contest()
    assert me.post(reverse(LIST), body(contest), format="json").status_code == 201
    r = me.post(reverse(LIST), body(contest), format="json")
    assert r.status_code == 400
    assert "contest" in r.data
    assert Submission.objects.count() == 1


@pytest.mark.parametrize("kind", ["draft", "judging", "closed", "not_started"])
def test_cannot_submit_to_unavailable_contest(me, make_contest, kind):
    now = timezone.now()
    kwargs = {
        "draft": {"status": Contest.Status.DRAFT},
        "judging": {"status": Contest.Status.JUDGING},
        "closed": {"starts_at": now - timedelta(days=30), "deadline": now - timedelta(days=1)},
        "not_started": {"starts_at": now + timedelta(days=2), "deadline": now + timedelta(days=9)},
    }[kind]
    r = me.post(reverse(LIST), body(make_contest(**kwargs)), format="json")
    assert r.status_code == 400
    assert Submission.objects.count() == 0


def test_unknown_contest_is_rejected(me):
    r = me.post(reverse(LIST), {"contest": "нет-такого", "title": "x"}, format="json")
    assert r.status_code == 400


@pytest.mark.parametrize("link", ["javascript:alert(1)", "ftp://example.com/f", "not a url"])
def test_dangerous_or_invalid_links_are_rejected(me, make_contest, link):
    r = me.post(reverse(LIST), body(make_contest(), link=link), format="json")
    assert r.status_code == 400
    assert "link" in r.data


def test_title_is_required(me, make_contest):
    data = body(make_contest())
    del data["title"]
    r = me.post(reverse(LIST), data, format="json")
    assert r.status_code == 400
    assert "title" in r.data


# ---------- чтение и чужие работы ----------

def test_list_contains_only_own_submissions(me, participant, make_user, make_submission):
    mine = make_submission(participant)
    make_submission(make_user())
    r = me.get(reverse(LIST))
    assert [s["id"] for s in r.data["results"]] == [mine.pk]


@pytest.mark.parametrize(
    "method,name,data",
    [
        ("get", DETAIL, None),
        ("patch", DETAIL, {"title": "Взлом"}),
        ("delete", DETAIL, None),
        ("post", SUBMIT, None),
    ],
)
def test_foreign_submission_is_404(me, make_user, make_submission, method, name, data):
    foreign = make_submission(make_user(), status=S.DRAFT, submitted_at=None, title="Чужая")
    assert call(me, method, reverse(name, args=[foreign.pk]), data).status_code == 404
    foreign.refresh_from_db()
    assert foreign.title == "Чужая"
    assert foreign.status == S.DRAFT


def test_author_sees_moderation_comment(me, participant, make_submission):
    sub = make_submission(participant, status=S.REJECTED, moderation_comment="Не по теме")
    r = me.get(reverse(DETAIL, args=[sub.pk]))
    assert r.data["moderation_comment"] == "Не по теме"
    assert r.data["can_edit"] is False


# ---------- редактирование ----------

def test_patch_draft(me, participant, make_submission):
    sub = make_submission(participant, status=S.DRAFT, submitted_at=None)
    r = me.patch(reverse(DETAIL, args=[sub.pk]), {"title": "Новое", "status": "accepted"}, format="json")
    assert r.status_code == 200
    assert r.data["title"] == "Новое"
    assert r.data["status"] == "draft"


def test_contest_cannot_be_changed_after_creation(me, participant, make_contest, make_submission):
    sub = make_submission(participant, status=S.DRAFT, submitted_at=None)
    other = make_contest()
    r = me.patch(reverse(DETAIL, args=[sub.pk]), {"contest": other.slug}, format="json")
    assert r.status_code == 200
    sub.refresh_from_db()
    assert sub.contest_id != other.pk


def test_submitted_work_can_be_edited_while_contest_is_open(me, participant, make_submission):
    sub = make_submission(participant)
    r = me.patch(reverse(DETAIL, args=[sub.pk]), {"description": "Дополнил"}, format="json")
    assert r.status_code == 200
    assert r.data["status"] == "submitted"


def test_closed_contest_blocks_edit_and_withdraw(me, participant, make_submission):
    sub = make_submission(participant)
    close(sub.contest)
    assert me.get(reverse(DETAIL, args=[sub.pk])).data["can_edit"] is False
    assert me.patch(reverse(DETAIL, args=[sub.pk]), {"title": "Поздно"}, format="json").status_code == 400
    assert me.delete(reverse(DETAIL, args=[sub.pk])).status_code == 400
    assert Submission.objects.filter(pk=sub.pk).exists()


@pytest.mark.parametrize("final", [S.ACCEPTED, S.REJECTED])
def test_moderated_work_is_locked(me, participant, make_submission, final):
    sub = make_submission(participant, status=final)
    assert me.patch(reverse(DETAIL, args=[sub.pk]), {"title": "Правка"}, format="json").status_code == 400
    assert me.delete(reverse(DETAIL, args=[sub.pk])).status_code == 400


# ---------- подача ----------

def test_submit_draft(me, participant, make_submission):
    sub = make_submission(participant, status=S.DRAFT, submitted_at=None)
    r = me.post(reverse(SUBMIT, args=[sub.pk]))
    assert r.status_code == 200
    assert r.data["status"] == "submitted"
    sub.refresh_from_db()
    assert sub.submitted_at is not None


def test_submit_needs_description(me, participant, make_submission):
    sub = make_submission(participant, status=S.DRAFT, submitted_at=None, description="  ")
    assert me.post(reverse(SUBMIT, args=[sub.pk])).status_code == 400


def test_submit_needs_verified_email(api, make_user, make_submission):
    user = make_user(role="participant")  # email не подтверждён
    sub = make_submission(user, status=S.DRAFT, submitted_at=None)
    api.force_authenticate(user)
    assert api.post(reverse(SUBMIT, args=[sub.pk])).status_code == 403
    sub.refresh_from_db()
    assert sub.status == S.DRAFT


def test_cannot_submit_twice(me, participant, make_submission):
    sub = make_submission(participant)
    assert me.post(reverse(SUBMIT, args=[sub.pk])).status_code == 400


def test_cannot_submit_after_deadline(me, participant, make_submission):
    sub = make_submission(participant, status=S.DRAFT, submitted_at=None)
    close(sub.contest)
    assert me.post(reverse(SUBMIT, args=[sub.pk])).status_code == 400
    sub.refresh_from_db()
    assert sub.status == S.DRAFT


# ---------- отзыв ----------

def test_draft_and_submitted_can_be_withdrawn(me, participant, make_submission):
    draft = make_submission(participant, status=S.DRAFT, submitted_at=None)
    submitted = make_submission(participant)
    assert me.delete(reverse(DETAIL, args=[draft.pk])).status_code == 204
    assert me.delete(reverse(DETAIL, args=[submitted.pk])).status_code == 204
    assert Submission.objects.count() == 0