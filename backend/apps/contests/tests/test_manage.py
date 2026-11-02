from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contests.models import Contest, ContestJury, JudgingCriterion, Prize

pytestmark = pytest.mark.django_db
LIST = "manage-contest-list"
DETAIL = "manage-contest-detail"
DRAFT = Contest.Status.DRAFT


@pytest.fixture
def organizer(make_user):
    return make_user(role="organizer", is_email_verified=True)


@pytest.fixture
def me(api, organizer):
    """API-клиент, вошедший как организатор."""
    api.force_authenticate(organizer)
    return api


@pytest.fixture
def judge(make_user):
    return make_user(role="jury", is_email_verified=True)


def payload(category, **over):
    now = timezone.now()
    data = {
        "title": "Новый конкурс",
        "description": "Описание",
        "rules": "Правила",
        "category": category.id,
        "starts_at": (now + timedelta(days=1)).isoformat(),
        "deadline": (now + timedelta(days=10)).isoformat(),
        "prizes": [{"place": 1, "amount": "15000.00"}, {"place": 2, "amount": "10000.00"}],
        "criteria": [{"title": "Идея", "max_score": 10, "weight": "1.00"}],
    }
    data.update(over)
    return data


def call(api, method, url, body=None):
    if method == "get":
        return api.get(url)
    return getattr(api, method)(url, body, format="json")


# ---------- доступ ----------

def test_anonymous_gets_401(api):
    assert api.get(reverse(LIST)).status_code == 401


@pytest.mark.parametrize("role", ["participant", "jury"])
def test_other_roles_get_403(api, make_user, role):
    api.force_authenticate(make_user(role=role))
    assert api.get(reverse(LIST)).status_code == 403


# ---------- создание ----------

def test_organizer_creates_draft_with_prizes_and_criteria(me, organizer, category):
    r = me.post(reverse(LIST), payload(category), format="json")
    assert r.status_code == 201, r.data
    assert r.data["status"] == "draft"
    assert r.data["slug"]
    assert [p["place"] for p in r.data["prizes"]] == [1, 2]
    assert r.data["criteria"][0]["title"] == "Идея"
    assert Contest.objects.get(pk=r.data["id"]).organizer == organizer


def test_status_slug_and_organizer_in_body_are_ignored(me, organizer, category):
    r = me.post(
        reverse(LIST),
        payload(category, status="published", slug="hack", organizer=999),
        format="json",
    )
    assert r.status_code == 201
    assert r.data["status"] == "draft"
    assert r.data["slug"] != "hack"
    assert Contest.objects.get(pk=r.data["id"]).organizer == organizer


def test_deadline_must_be_after_start(me, category):
    bad = (timezone.now() - timedelta(days=1)).isoformat()
    r = me.post(reverse(LIST), payload(category, deadline=bad), format="json")
    assert r.status_code == 400
    assert "deadline" in r.data


@pytest.mark.parametrize(
    "field,value",
    [
        ("prizes", [{"place": 1, "amount": "100"}, {"place": 1, "amount": "50"}]),
        ("prizes", [{"place": 1, "amount": "0"}]),
        ("criteria", [{"title": "Идея"}, {"title": "идея"}]),
        ("criteria", [{"title": "Идея", "max_score": 0}]),
        ("criteria", [{"title": "Идея", "weight": "0"}]),
    ],
)
def test_invalid_prizes_and_criteria_are_rejected(me, category, field, value):
    r = me.post(reverse(LIST), payload(category, **{field: value}), format="json")
    assert r.status_code == 400
    assert field in r.data


# ---------- список и чужие объекты ----------

def test_list_shows_only_own_contests_including_drafts(me, organizer, make_contest):
    make_contest(title="Мой черновик", organizer=organizer, status=DRAFT)
    make_contest(title="Мой архив", organizer=organizer, status=Contest.Status.ARCHIVED)
    make_contest(title="Чужой")
    r = me.get(reverse(LIST))
    assert r.status_code == 200
    assert {c["title"] for c in r.data["results"]} == {"Мой черновик", "Мой архив"}


def test_admin_sees_all_contests(api, make_user, make_contest):
    make_contest(title="A", status=DRAFT)
    make_contest(title="B")
    api.force_authenticate(make_user(role="admin"))
    assert api.get(reverse(LIST)).data["count"] == 2


@pytest.mark.parametrize(
    "method,name,body",
    [
        ("get", DETAIL, None),
        ("patch", DETAIL, {"title": "Взлом"}),
        ("delete", DETAIL, None),
        ("post", "manage-contest-publish", None),
        ("post", "manage-contest-archive", None),
    ],
)
def test_other_organizers_contest_is_404(api, make_user, make_contest, method, name, body):
    contest = make_contest(title="Чужой", status=DRAFT)
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    r = call(api, method, reverse(name, args=[contest.pk]), body)
    assert r.status_code == 404
    contest.refresh_from_db()
    assert contest.title == "Чужой"
    assert contest.status == DRAFT


# ---------- публикация ----------

def test_publish_makes_contest_public(me, organizer, make_contest):
    contest = make_contest(organizer=organizer, status=DRAFT)
    JudgingCriterion.objects.create(contest=contest, title="Идея")
    r = me.post(reverse("manage-contest-publish", args=[contest.pk]))
    assert r.status_code == 200
    assert r.data["status"] == "published"
    public = me.get(reverse("contest-list"))
    assert contest.title in [c["title"] for c in public.data["results"]]


def test_publish_needs_a_criterion(me, organizer, make_contest):
    contest = make_contest(organizer=organizer, status=DRAFT)
    r = me.post(reverse("manage-contest-publish", args=[contest.pk]))
    assert r.status_code == 400
    contest.refresh_from_db()
    assert contest.status == DRAFT


def test_publish_needs_verified_email(api, make_user, make_contest):
    organizer = make_user(role="organizer")  # email не подтверждён
    contest = make_contest(organizer=organizer, status=DRAFT)
    JudgingCriterion.objects.create(contest=contest, title="Идея")
    api.force_authenticate(organizer)
    assert api.post(reverse("manage-contest-publish", args=[contest.pk])).status_code == 403


def test_publish_rejects_past_deadline(me, organizer, make_contest):
    now = timezone.now()
    contest = make_contest(
        organizer=organizer,
        status=DRAFT,
        starts_at=now - timedelta(days=10),
        deadline=now - timedelta(days=1),
    )
    JudgingCriterion.objects.create(contest=contest, title="Идея")
    assert me.post(reverse("manage-contest-publish", args=[contest.pk])).status_code == 400


def test_only_draft_can_be_published(me, organizer, make_contest):
    contest = make_contest(organizer=organizer)  # уже опубликован
    assert me.post(reverse("manage-contest-publish", args=[contest.pk])).status_code == 400


# ---------- редактирование ----------

def test_patch_keeps_slug_and_untouched_prizes(me, organizer, make_contest):
    contest = make_contest(organizer=organizer, status=DRAFT, prizes=(100,))
    r = me.patch(reverse(DETAIL, args=[contest.pk]), {"title": "Новое название"}, format="json")
    assert r.status_code == 200
    assert r.data["title"] == "Новое название"
    assert r.data["slug"] == contest.slug
    assert len(r.data["prizes"]) == 1


def test_patch_replaces_prizes_in_draft(me, organizer, make_contest):
    contest = make_contest(organizer=organizer, status=DRAFT, prizes=(100, 50, 20))
    body = {"prizes": [{"place": 1, "amount": "500.00"}, {"place": 2, "amount": "250.00"}]}
    r = me.patch(reverse(DETAIL, args=[contest.pk]), body, format="json")
    assert r.status_code == 200
    assert [p["amount"] for p in r.data["prizes"]] == ["500.00", "250.00"]
    assert Prize.objects.filter(contest=contest).count() == 2


def test_patch_cannot_change_status(me, organizer, make_contest):
    contest = make_contest(organizer=organizer, status=DRAFT)
    r = me.patch(reverse(DETAIL, args=[contest.pk]), {"status": "finished"}, format="json")
    assert r.status_code == 200
    contest.refresh_from_db()
    assert contest.status == DRAFT


@pytest.mark.parametrize(
    "body",
    [
        {"prizes": [{"place": 1, "amount": "1.00"}]},
        {"criteria": [{"title": "Новый"}]},
    ],
)
def test_prizes_and_criteria_are_frozen_after_publish(me, organizer, make_contest, body):
    contest = make_contest(organizer=organizer)  # опубликован
    r = me.patch(reverse(DETAIL, args=[contest.pk]), body, format="json")
    assert r.status_code == 400


def test_published_contest_can_still_change_text(me, organizer, make_contest):
    contest = make_contest(organizer=organizer)
    r = me.patch(reverse(DETAIL, args=[contest.pk]), {"description": "Уточнение"}, format="json")
    assert r.status_code == 200
    assert r.data["description"] == "Уточнение"


def test_archived_contest_is_read_only(me, organizer, make_contest):
    contest = make_contest(organizer=organizer, status=Contest.Status.ARCHIVED)
    r = me.patch(reverse(DETAIL, args=[contest.pk]), {"title": "Правка"}, format="json")
    assert r.status_code == 400


def test_patch_cannot_put_deadline_before_start(me, organizer, make_contest):
    contest = make_contest(organizer=organizer)
    bad = (timezone.now() - timedelta(days=5)).isoformat()
    r = me.patch(reverse(DETAIL, args=[contest.pk]), {"deadline": bad}, format="json")
    assert r.status_code == 400


# ---------- архив и удаление ----------

def test_archive_hides_contest_from_public_list(me, organizer, make_contest):
    contest = make_contest(organizer=organizer)
    r = me.post(reverse("manage-contest-archive", args=[contest.pk]))
    assert r.status_code == 200
    assert r.data["status"] == "archived"
    public = me.get(reverse("contest-list"))
    assert contest.title not in [c["title"] for c in public.data["results"]]
    assert me.post(reverse("manage-contest-archive", args=[contest.pk])).status_code == 400


def test_draft_can_be_deleted(me, organizer, make_contest):
    contest = make_contest(organizer=organizer, status=DRAFT)
    assert me.delete(reverse(DETAIL, args=[contest.pk])).status_code == 204
    assert not Contest.objects.filter(pk=contest.pk).exists()


def test_published_contest_cannot_be_deleted(me, organizer, make_contest):
    contest = make_contest(organizer=organizer)
    assert me.delete(reverse(DETAIL, args=[contest.pk])).status_code == 400
    assert Contest.objects.filter(pk=contest.pk).exists()


# ---------- жюри ----------

def test_assign_judge_by_email(me, organizer, make_contest, judge):
    contest = make_contest(organizer=organizer)
    url = reverse("manage-contest-jury", args=[contest.pk])
    first = me.post(url, {"email": judge.email.upper()}, format="json")
    assert first.status_code == 201
    assert first.data == {"judge_id": judge.id, "username": judge.username}
    assert me.post(url, {"email": judge.email}, format="json").status_code == 200
    assert ContestJury.objects.filter(contest=contest).count() == 1


def test_only_real_judges_can_be_assigned_and_error_does_not_leak(
    me, organizer, make_contest, make_user
):
    contest = make_contest(organizer=organizer)
    url = reverse("manage-contest-jury", args=[contest.pk])
    participant = make_user()
    a = me.post(url, {"email": participant.email}, format="json")
    b = me.post(url, {"email": "nobody@example.com"}, format="json")
    assert a.status_code == b.status_code == 400
    assert a.data == b.data
    assert ContestJury.objects.count() == 0


def test_list_and_remove_judge(me, organizer, make_contest, judge):
    contest = make_contest(organizer=organizer)
    ContestJury.objects.create(contest=contest, judge=judge)
    listing = me.get(reverse("manage-contest-jury", args=[contest.pk]))
    assert listing.data == [{"judge_id": judge.id, "username": judge.username}]
    assert "email" not in str(listing.data)
    detail = reverse("manage-contest-jury-detail", kwargs={"pk": contest.pk, "judge_id": judge.pk})
    assert me.delete(detail).status_code == 204
    assert me.delete(detail).status_code == 404


def test_other_organizer_cannot_manage_jury(api, make_user, make_contest, judge):
    contest = make_contest()
    api.force_authenticate(make_user(role="organizer", is_email_verified=True))
    url = reverse("manage-contest-jury", args=[contest.pk])
    assert api.get(url).status_code == 404
    assert api.post(url, {"email": judge.email}, format="json").status_code == 404


def test_jury_is_locked_when_contest_is_over(me, organizer, make_contest, judge):
    contest = make_contest(organizer=organizer, status=Contest.Status.FINISHED)
    url = reverse("manage-contest-jury", args=[contest.pk])
    assert me.post(url, {"email": judge.email}, format="json").status_code == 400