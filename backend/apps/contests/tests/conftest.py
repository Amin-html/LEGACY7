from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.contests.models import Category, Contest, Prize


@pytest.fixture
def category(db):
    return Category.objects.create(name="Фотография")


@pytest.fixture
def make_contest(db, make_user, category):
    counter = {"n": 0}

    def factory(prizes=(), **kw):
        counter["n"] += 1
        now = timezone.now()
        defaults = dict(
            title=f"Конкурс {counter['n']}",
            description="Описание",
            category=category,
            organizer=make_user(role="organizer"),
            status=Contest.Status.PUBLISHED,
            starts_at=now - timedelta(days=1),
            deadline=now + timedelta(days=10),
        )
        defaults.update(kw)
        contest = Contest.objects.create(**defaults)
        for place, amount in enumerate(prizes, start=1):
            Prize.objects.create(contest=contest, place=place, amount=Decimal(amount))
        return contest

    return factory