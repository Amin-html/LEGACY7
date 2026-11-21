from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.contests.models import Category, Contest


def test_slug_is_generated_from_cyrillic_title_and_is_unique(make_contest):
    first = make_contest(title="Спортивный кадр")
    second = make_contest(title="Спортивный кадр")
    assert first.slug == "спортивный-кадр"
    assert second.slug == "спортивный-кадр-2"


def test_deadline_must_be_after_start(make_contest):
    now = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        make_contest(starts_at=now, deadline=now - timedelta(days=1))


def test_is_open_depends_on_status_and_dates(make_contest):
    now = timezone.now()
    assert make_contest().is_open is True
    assert make_contest(status=Contest.Status.DRAFT).is_open is False
    past = make_contest(starts_at=now - timedelta(days=30), deadline=now - timedelta(days=1))
    assert past.is_open is False
    soon = make_contest(starts_at=now + timedelta(days=2), deadline=now + timedelta(days=9))
    assert soon.is_open is False


def test_category_slug(db):
    assert Category.objects.create(name="Видео").slug == "видео"