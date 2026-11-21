import pytest
from django.urls import reverse

from apps.contests.models import Contest
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
URL = "contest-results"


def test_results_have_places_ties_and_prizes(api, make_finished, rate, make_user):
    contest = make_finished(prizes=(15000, 10000))
    for name, total in (("alice", 9), ("bob", 7), ("carol", 7), ("dave", 3)):
        rate(contest, make_user(username=name), total, total)
    r = api.get(reverse(URL, args=[contest.slug]))
    assert r.status_code == 200
    assert r.data["contest"]["slug"] == contest.slug
    assert [
        (x["place"], x["username"], x["score"], x["points"], x["prize"]) for x in r.data["results"]
    ] == [
        (1, "alice", "9.00", 900, "15000.00"),
        (2, "bob", "7.00", 700, "10000.00"),
        (2, "carol", "7.00", 700, "10000.00"),
        (4, "dave", "3.00", 300, None),
    ]


def test_titles_are_hidden_unless_showcase_is_public(api, make_finished, rate, make_user):
    hidden = make_finished()
    rate(hidden, make_user(username="alice"), 8, 8)
    assert "title" not in api.get(reverse(URL, args=[hidden.slug])).data["results"][0]

    shown = make_finished(public_submissions=True)
    rate(shown, make_user(username="bob"), 8, 8)
    assert api.get(reverse(URL, args=[shown.slug])).data["results"][0]["title"] == "Работа bob"


@pytest.mark.parametrize(
    "status",
    [Contest.Status.DRAFT, Contest.Status.PUBLISHED, Contest.Status.JUDGING, Contest.Status.ARCHIVED],
)
def test_only_finished_contest_has_results(api, make_finished, status):
    contest = make_finished(status=status)
    assert api.get(reverse(URL, args=[contest.slug])).status_code == 404


def test_unrated_work_is_not_listed(api, make_finished, rate, make_user):
    contest = make_finished()
    rate(contest, make_user(username="alice"), 8, 8)
    rate(contest, make_user(username="bob"))
    assert [x["username"] for x in api.get(reverse(URL, args=[contest.slug])).data["results"]] == ["alice"]


def test_rejected_work_is_not_listed(api, make_finished, rate, make_user):
    contest = make_finished()
    rate(contest, make_user(username="alice"), 8, 8, status=Submission.Status.REJECTED)
    assert api.get(reverse(URL, args=[contest.slug])).data["results"] == []


def test_no_emails_in_results(api, make_finished, rate, make_user):
    contest = make_finished()
    user = make_user(username="alice")
    rate(contest, user, 8, 8)
    assert user.email not in str(api.get(reverse(URL, args=[contest.slug])).data)