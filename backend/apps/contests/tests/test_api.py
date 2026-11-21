from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.contests.models import Contest, JudgingCriterion

pytestmark = pytest.mark.django_db
LIST = "contest-list"


def titles(response):
    return [c["title"] for c in response.data["results"]]


def test_categories_are_public(api, category):
    r = api.get(reverse("category-list"))
    assert r.status_code == 200
    assert r.data[0]["slug"] == "фотография"


def test_list_is_public_and_hides_draft_and_archived(api, make_contest):
    make_contest(title="Виден", status=Contest.Status.PUBLISHED)
    make_contest(title="Идёт оценка", status=Contest.Status.JUDGING)
    make_contest(title="Черновик", status=Contest.Status.DRAFT)
    make_contest(title="Архив", status=Contest.Status.ARCHIVED)
    r = api.get(reverse(LIST))
    assert r.status_code == 200
    assert set(titles(r)) == {"Виден", "Идёт оценка"}


def test_list_exposes_no_organizer_email(api, make_contest):
    make_contest()
    item = api.get(reverse(LIST)).data["results"][0]
    assert "email" not in str(item)
    assert item["organizer"]


def test_detail_by_cyrillic_slug_has_prizes_and_criteria(api, make_contest):
    contest = make_contest(title="Спортивный кадр", prizes=(15000, 10000))
    JudgingCriterion.objects.create(contest=contest, title="Идея", max_score=10)
    r = api.get(reverse("contest-detail", args=[contest.slug]))
    assert r.status_code == 200
    assert [p["place"] for p in r.data["prizes"]] == [1, 2]
    assert r.data["criteria"][0]["title"] == "Идея"
    assert r.data["prize_pool"] == "25000.00"
    assert r.data["is_open"] is True


def test_draft_detail_is_404(api, make_contest):
    contest = make_contest(status=Contest.Status.DRAFT)
    assert api.get(reverse("contest-detail", args=[contest.slug])).status_code == 404


def test_search_by_title(api, make_contest):
    make_contest(title="Футбольный челлендж")
    make_contest(title="Логотип будущего")
    r = api.get(reverse(LIST), {"search": "челлендж"})
    assert titles(r) == ["Футбольный челлендж"]


def test_filter_by_category(api, make_contest, category):
    from apps.contests.models import Category

    design = Category.objects.create(name="Дизайн")
    make_contest(title="Фото", category=category)
    make_contest(title="Лого", category=design)
    r = api.get(reverse(LIST), {"category": design.slug})
    assert titles(r) == ["Лого"]


def test_filter_by_status(api, make_contest):
    make_contest(title="Идёт", status=Contest.Status.PUBLISHED)
    make_contest(title="Оценка", status=Contest.Status.JUDGING)
    r = api.get(reverse(LIST), {"status": "judging"})
    assert titles(r) == ["Оценка"]


def test_filter_open(api, make_contest):
    now = timezone.now()
    make_contest(title="Открыт")
    make_contest(title="Закрыт", starts_at=now - timedelta(days=30), deadline=now - timedelta(days=1))
    assert titles(api.get(reverse(LIST), {"open": "true"})) == ["Открыт"]
    assert titles(api.get(reverse(LIST), {"open": "false"})) == ["Закрыт"]


def test_filter_by_deadline_range(api, make_contest):
    now = timezone.now()
    make_contest(title="Скоро", deadline=now + timedelta(days=3))
    make_contest(title="Нескоро", deadline=now + timedelta(days=30))
    cutoff = (now + timedelta(days=10)).isoformat()
    assert titles(api.get(reverse(LIST), {"deadline_before": cutoff})) == ["Скоро"]
    assert titles(api.get(reverse(LIST), {"deadline_after": cutoff})) == ["Нескоро"]


def test_ordering_by_prize_pool(api, make_contest):
    make_contest(title="Малый", prizes=(100,))
    make_contest(title="Большой", prizes=(500, 200))
    r = api.get(reverse(LIST), {"ordering": "-prize_pool"})
    assert titles(r) == ["Большой", "Малый"]


def test_contest_without_prizes_has_zero_pool(api, make_contest):
    make_contest()
    assert api.get(reverse(LIST)).data["results"][0]["prize_pool"] == "0.00"


def test_pagination(api, make_contest):
    for _ in range(13):
        make_contest()
    page1 = api.get(reverse(LIST))
    assert page1.data["count"] == 13
    assert len(page1.data["results"]) == 12
    assert page1.data["next"] is not None
    page2 = api.get(reverse(LIST), {"page": 2})
    assert len(page2.data["results"]) == 1