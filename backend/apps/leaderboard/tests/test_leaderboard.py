from decimal import Decimal

import pytest
from django.urls import reverse

from apps.contests.models import Category, Contest
from apps.judging.models import Evaluation
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
URL = "leaderboard"


def rows(api, **params):
    r = api.get(reverse(URL), params)
    assert r.status_code == 200
    return r.data["results"]


def table(result):
    return [(r["place"], r["user"]["username"], r["points"], r["contests"]) for r in result]


def test_empty_leaderboard(api):
    r = api.get(reverse(URL))
    assert r.status_code == 200
    assert r.data["count"] == 0
    assert r.data["results"] == []


def test_points_are_summed_over_finished_contests(api, make_finished, rate, make_user):
    alice, bob = make_user(username="alice"), make_user(username="bob")
    first, second = make_finished(), make_finished()
    rate(first, alice, 8, 6)   # 7.00 -> 700
    rate(second, alice, 9, 9)  # 9.00 -> 900
    rate(first, bob, 5, 5)     # 5.00 -> 500
    assert table(rows(api)) == [(1, "alice", 1600, 2), (2, "bob", 500, 1)]


def test_equal_points_share_a_place(api, make_finished, rate, make_user):
    contest = make_finished()
    for name, total in (("alice", 7), ("bob", 7), ("carol", 5)):
        rate(contest, make_user(username=name), total, total)
    assert table(rows(api)) == [(1, "alice", 700, 1), (1, "bob", 700, 1), (3, "carol", 500, 1)]


def test_score_is_rounded_half_up(api, make_finished, rate, make_user):
    rate(make_finished(), make_user(username="alice"), "7.33", "7.34")  # 7.335 -> 7.34
    assert rows(api)[0]["points"] == 734


def test_unfinished_contests_do_not_count(api, make_finished, rate, make_user):
    for status in (Contest.Status.JUDGING, Contest.Status.PUBLISHED, Contest.Status.ARCHIVED):
        rate(make_finished(status=status), make_user(), 9, 9)
    assert rows(api) == []


def test_only_accepted_works_count(api, make_finished, rate, make_user):
    rate(make_finished(), make_user(), 9, 9, status=Submission.Status.REJECTED)
    assert rows(api) == []


def test_draft_evaluations_are_ignored(api, make_finished, rate, make_user):
    contest = make_finished()
    sub = rate(contest, make_user(username="alice"), 6, 10)
    Evaluation.objects.filter(submission=sub, judge=contest.judges[1]).update(
        status=Evaluation.Status.DRAFT
    )
    assert rows(api)[0]["points"] == 600  # считается только подтверждённая оценка


def test_evaluations_of_unassigned_judges_are_ignored(api, make_finished, rate, make_user):
    contest = make_finished()
    sub = rate(contest, make_user(username="alice"), 4, 4)
    Evaluation.objects.create(
        submission=sub,
        judge=make_user(role="jury"),
        total=Decimal("10"),
        status=Evaluation.Status.FINAL,
    )
    assert rows(api)[0]["points"] == 400


def test_unrated_work_does_not_count_as_a_contest(api, make_finished, rate, make_user):
    alice = make_user(username="alice")
    rate(make_finished(), alice, 8, 8)
    rate(make_finished(), alice)  # принята, но оценок нет
    assert table(rows(api)) == [(1, "alice", 800, 1)]


def test_filter_by_category(api, make_finished, rate, make_user, category):
    design = Category.objects.create(name="Дизайн")
    rate(make_finished(category=category), make_user(username="photo"), 9, 9)
    rate(make_finished(category=design), make_user(username="artist"), 7, 7)
    assert table(rows(api, category=design.slug)) == [(1, "artist", 700, 1)]
    assert table(rows(api, category=category.slug)) == [(1, "photo", 900, 1)]
    assert len(rows(api)) == 2


def test_unknown_category_is_404(api):
    assert api.get(reverse(URL), {"category": "нет-такой"}).status_code == 404


def test_pagination(api, make_finished, rate, make_user):
    contest = make_finished()
    for _ in range(25):
        rate(contest, make_user(), 5, 5)
    page1 = api.get(reverse(URL))
    assert page1.data["count"] == 25
    assert len(page1.data["results"]) == 20
    assert len(api.get(reverse(URL), {"page": 2}).data["results"]) == 5


def test_no_emails_in_public_data(api, make_finished, rate, make_user):
    user = make_user(username="alice")
    rate(make_finished(), user, 8, 8)
    assert user.email not in str(api.get(reverse(URL)).data)


def test_finished_contest_cannot_be_archived(api, make_finished, organizer):
    contest = make_finished()
    api.force_authenticate(organizer)
    r = api.post(reverse("manage-contest-archive", args=[contest.pk]))
    assert r.status_code == 400
    contest.refresh_from_db()
    assert contest.status == Contest.Status.FINISHED