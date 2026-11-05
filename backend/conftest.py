import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

PASSWORD = "Str0ng-Pass-123"


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Лимит запросов хранится в кэше. Чистим, чтобы тесты не мешали друг другу."""
    cache.clear()


@pytest.fixture(autouse=True)
def fast_password_hasher(settings):
    """В тестах пароли хешируются быстро: прогон идёт в разы быстрее."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_user(db):
    counter = {"n": 0}

    def factory(email=None, password=PASSWORD, **extra):
        counter["n"] += 1
        email = email or f"user{counter['n']}@example.com"
        username = extra.pop("username", email.split("@")[0])
        return get_user_model().objects.create_user(
            email=email, username=username, password=password, **extra
        )

    return factory