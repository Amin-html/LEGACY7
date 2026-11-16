from decimal import Decimal

import pytest
from django.urls import reverse

from apps.contests.models import Contest, ContestJury, JudgingCriterion
from apps.judging.models import Evaluation
from apps.submissions.models import Submission

pytestmark = pytest.mark.django_db
S = Submission.Status
CONTESTS = "jury-contest-list"
LIST = "jury-submission-list"
DETAIL = "jury-submission-detail"
EVAL = "jury-evaluation"
FINALIZE = "jury-evaluation-finalize"


def payload(criteria, a, b, **extra):
    data = {
        "scores": [
            {"criterion": criteria[0].id, "score": a},
            {"criterion": criteria[1].id, "score": b},
        ]
    }
    data.update(extra)
    return data


def save(api, sub, data):
    return api.put(reverse(EVAL, args=[sub.pk]), data, format="json")


def finalize(api, sub):
    return api.post(reverse(FINALIZE, args=[sub.pk]))


def score_map(response):
    return {s["criterion"]: s["score"] for s in response.data["scores"]}


# ---------- доступ ----------

def test_anonymous_gets_401(api):
    assert api.get(reverse(CONTESTS)).status_code == 401
    assert api.get(reverse(LIST)).status_code == 401


@pytest.mark.parametrize("role", ["participant", "organizer"])
def test_other_roles_get_403(api, make_user, role):
    api.force_authenticate(make_user(role=role))
    assert api.get(reverse(CONTESTS)).status_code == 403
    assert api.get(reverse(LIST)).status_code == 403


@pytest.mark.parametrize("name", [DETAIL, EVAL, FINALIZE])
def test_unassigned_judge_gets_404(api, make_user, sub, name):
    api.force_authenticate(make_user(role="jury"))
    url = reverse(name, args=[sub.pk])
    response = api.post(url) if name == FINALIZE else api.get(url)
    assert response.status_code == 404


def test_unassigned_judge_cannot_save(api, make_user, sub, criteria):
    api.force_authenticate(make_user(role="jury"))
    assert save(api, sub, payload(criteria, 5, 5)).status_code == 404
    assert Evaluation.objects.count() == 0


@pytest.mark.parametrize("name", [DETAIL, EVAL])
def test_not_accepted_work_is_hidden(jury_api, contest, make_sub, name):
    for status in (S.SUBMITTED, S.DRAFT, S.REJECTED):
        hidden = make_sub(contest, status=status)
        assert jury_api.get(reverse(name, args=[hidden.pk])).status_code == 404


def test_work_is_closed_when_contest_is_not_in_judging(jury_api, contest, sub, criteria):
    contest.status = Contest.Status.FINISHED
    contest.save()
    assert jury_api.get(reverse(DETAIL, args=[sub.pk])).status_code == 404
    assert save(jury_api, sub, payload(criteria, 5, 5)).status_code == 404
    assert Evaluation.objects.count() == 0


# ---------- списки ----------

def test_contest_list_shows_only_my_judging_contests_with_progress(
    jury_api, judge, contest, sub, make_sub, make_contest
):
    make_contest(status=Contest.Status.JUDGING)  # судья не назначен
    finished = make_contest(status=Contest.Status.FINISHED)
    ContestJury.objects.create(contest=finished, judge=judge)
    second = make_sub(contest)
    Evaluation.objects.create(submission=second, judge=judge, status=Evaluation.Status.FINAL)

    r = jury_api.get(reverse(CONTESTS))
    assert [c["id"] for c in r.data] == [contest.id]
    assert (r.data[0]["total"], r.data[0]["evaluated"], r.data[0]["drafts"]) == (2, 1, 0)


def test_list_has_only_accepted_works_of_my_contests_and_hides_authors(
    jury_api, contest, sub, make_sub, make_contest
):
    make_sub(contest, status=S.SUBMITTED)
    make_sub(contest, status=S.DRAFT)
    make_sub(contest, status=S.REJECTED)
    make_sub(make_contest(status=Contest.Status.JUDGING))  # чужой конкурс
    r = jury_api.get(reverse(LIST))
    assert [s["id"] for s in r.data["results"]] == [sub.id]
    assert sub.author.username not in str(r.data)
    assert sub.author.email not in str(r.data)


def test_list_filters_by_my_status_and_contest(jury_api, judge, contest, sub, make_sub):
    done = make_sub(contest)
    Evaluation.objects.create(submission=done, judge=judge, status=Evaluation.Status.DRAFT)

    def ids(**params):
        return [s["id"] for s in jury_api.get(reverse(LIST), params).data["results"]]

    assert ids(my_status="draft") == [done.id]
    assert ids(my_status="none") == [sub.id]
    assert sorted(ids(contest=contest.id)) == sorted([sub.id, done.id])


def test_detail_shows_criteria_and_no_author(jury_api, sub):
    r = jury_api.get(reverse(DETAIL, args=[sub.pk]))
    assert r.status_code == 200
    assert [c["title"] for c in r.data["criteria"]] == ["Идея", "Исполнение"]
    assert r.data["my_evaluation"] is None
    assert r.data["my_status"] == "none"
    assert sub.author.email not in str(r.data)
    assert sub.author.username not in str(r.data)


def test_detail_shows_my_evaluation(jury_api, sub, criteria):
    save(jury_api, sub, payload(criteria, 5, 5))
    r = jury_api.get(reverse(DETAIL, args=[sub.pk]))
    assert r.data["my_status"] == "draft"
    assert r.data["my_evaluation"]["status"] == "draft"


# ---------- черновик оценки ----------

def test_save_draft_stores_scores_and_comment(jury_api, judge, sub, criteria):
    r = save(jury_api, sub, payload(criteria, 8, 4, comment="Хорошо"))
    assert r.status_code == 200, r.data
    assert r.data["status"] == "draft"
    assert r.data["comment"] == "Хорошо"
    assert r.data["total"] is None
    assert score_map(r) == {criteria[0].id: 8, criteria[1].id: 4}
    assert Evaluation.objects.get(submission=sub, judge=judge).scores.count() == 2


def test_resaving_replaces_scores_and_keeps_missing_fields(jury_api, sub, criteria):
    save(jury_api, sub, payload(criteria, 8, 4, comment="Хорошо"))
    r = save(jury_api, sub, {"scores": [{"criterion": criteria[0].id, "score": 3}]})
    assert r.status_code == 200
    assert score_map(r) == {criteria[0].id: 3}
    assert r.data["comment"] == "Хорошо"


def test_get_evaluation_before_and_after_saving(jury_api, sub, criteria):
    assert jury_api.get(reverse(EVAL, args=[sub.pk])).data["status"] == "none"
    save(jury_api, sub, payload(criteria, 5, 5))
    assert jury_api.get(reverse(EVAL, args=[sub.pk])).data["status"] == "draft"


@pytest.mark.parametrize("a,b", [(11, 4), (8, 6), (-1, 4), ("abc", 4)])
def test_invalid_scores_are_rejected(jury_api, sub, criteria, a, b):
    assert save(jury_api, sub, payload(criteria, a, b)).status_code == 400
    assert Evaluation.objects.count() == 0


def test_duplicate_and_foreign_criteria_are_rejected(jury_api, sub, criteria, make_contest):
    duplicate = {
        "scores": [
            {"criterion": criteria[0].id, "score": 5},
            {"criterion": criteria[0].id, "score": 6},
        ]
    }
    assert save(jury_api, sub, duplicate).status_code == 400
    foreign = JudgingCriterion.objects.create(contest=make_contest(), title="Чужой")
    assert save(jury_api, sub, {"scores": [{"criterion": foreign.id, "score": 1}]}).status_code == 400
    assert Evaluation.objects.count() == 0


# ---------- подтверждение ----------

def test_finalize_requires_every_criterion(jury_api, sub, criteria):
    assert finalize(jury_api, sub).status_code == 400  # оценки ещё не сохранены
    save(jury_api, sub, {"scores": [{"criterion": criteria[0].id, "score": 5}]})
    r = finalize(jury_api, sub)
    assert r.status_code == 400
    assert "Исполнение" in str(r.data)
    assert Evaluation.objects.get(submission=sub).status == Evaluation.Status.DRAFT


def test_finalize_computes_weighted_total_and_locks(jury_api, sub, criteria):
    save(jury_api, sub, payload(criteria, 5, 5, comment="Ок"))
    r = finalize(jury_api, sub)
    assert r.status_code == 200, r.data
    assert r.data["status"] == "final"
    assert r.data["total"] == "6.67"  # (0.5*2 + 1.0*1) / 3 * 10
    assert r.data["finalized_at"] is not None

    assert save(jury_api, sub, payload(criteria, 10, 5)).status_code == 400
    assert finalize(jury_api, sub).status_code == 400
    assert jury_api.get(reverse(EVAL, args=[sub.pk])).data["total"] == "6.67"


def test_best_and_worst_totals(jury_api, contest, make_sub, criteria):
    best, worst = make_sub(contest), make_sub(contest)
    save(jury_api, best, payload(criteria, 10, 5))
    save(jury_api, worst, payload(criteria, 0, 0))
    assert finalize(jury_api, best).data["total"] == "10.00"
    assert finalize(jury_api, worst).data["total"] == "0.00"


def test_each_judge_has_own_evaluation(api, judge, contest, sub, criteria, make_user):
    second = make_user(role="jury")
    ContestJury.objects.create(contest=contest, judge=second)

    api.force_authenticate(judge)
    save(api, sub, payload(criteria, 10, 5))
    finalize(api, sub)

    api.force_authenticate(second)
    assert api.get(reverse(EVAL, args=[sub.pk])).data["status"] == "none"
    save(api, sub, payload(criteria, 0, 0))
    finalize(api, sub)

    totals = Evaluation.objects.filter(submission=sub).values_list("total", flat=True)
    assert sorted(totals) == [Decimal("0.00"), Decimal("10.00")]