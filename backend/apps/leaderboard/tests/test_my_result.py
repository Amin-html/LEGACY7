import pytest
from django.urls import reverse

from apps.contests.models import Contest, JudgingCriterion
from apps.judging.models import Evaluation, EvaluationScore
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
URL = "my-submission-result"


@pytest.fixture
def author(make_user):
    return make_user(role="participant")


def get(api, user, sub):
    api.force_authenticate(user)
    return api.get(reverse(URL, args=[sub.pk]))


def test_author_sees_full_result(api, make_finished, rate, make_user, author):
    contest = make_finished(prizes=(15000,))
    criterion = JudgingCriterion.objects.create(contest=contest, title="Идея", max_score=10)
    sub = rate(contest, author, 8, 6)
    rate(contest, make_user(role="participant"), 5, 5)

    first, second = (Evaluation.objects.get(submission=sub, judge=j) for j in contest.judges)
    Evaluation.objects.filter(pk=first.pk).update(comment="Сильная идея")
    EvaluationScore.objects.create(evaluation=first, criterion=criterion, score=9)
    EvaluationScore.objects.create(evaluation=second, criterion=criterion, score=7)

    r = get(api, author, sub)
    assert r.status_code == 200
    assert r.data["rated"] is True
    assert (r.data["score"], r.data["points"], r.data["place"], r.data["participants"]) == (
        "7.00", 700, 1, 2,
    )
    assert r.data["prize"] == "15000.00"
    assert r.data["criteria"] == [{"title": "Идея", "max_score": 10, "average": "8.00"}]
    assert r.data["comments"] == ["Сильная идея"]  # пустые комментарии не показываем
    assert contest.judges[0].username not in str(r.data)  # комментарии анонимны
    assert contest.judges[0].email not in str(r.data)


def test_accepted_work_without_evaluations_is_not_rated(api, make_finished, rate, author):
    sub = rate(make_finished(), author)
    r = get(api, author, sub)
    assert r.status_code == 200
    assert r.data == {"rated": False}


def test_rejected_work_has_no_result(api, make_finished, rate, author):
    sub = rate(make_finished(), author, 9, 9, status=Submission.Status.REJECTED)
    assert get(api, author, sub).status_code == 404


def test_result_is_hidden_until_contest_is_finished(api, make_finished, rate, author):
    sub = rate(make_finished(status=Contest.Status.JUDGING), author, 9, 9)
    assert get(api, author, sub).status_code == 404


def test_someone_elses_result_is_404(api, make_finished, rate, make_user, author):
    sub = rate(make_finished(), author, 9, 9)
    assert get(api, make_user(role="participant"), sub).status_code == 404


@pytest.mark.parametrize("role", ["organizer", "jury"])
def test_other_roles_get_403(api, make_finished, rate, make_user, author, role):
    sub = rate(make_finished(), author, 9, 9)
    assert get(api, make_user(role=role), sub).status_code == 403


def test_anonymous_gets_401(api, make_finished, rate, author):
    sub = rate(make_finished(), author, 9, 9)
    assert api.get(reverse(URL, args=[sub.pk])).status_code == 401