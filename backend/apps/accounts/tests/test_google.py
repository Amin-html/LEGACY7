from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.models import SocialAccount

User = get_user_model()
PASSWORD = "Str0ng-Pass-123"
VERIFY = "apps.accounts.google_views.google_id_token.verify_oauth2_token"
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def google_configured(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id"


def claims(**over):
    base = {"sub": "g-1", "email": "gu@gmail.com", "email_verified": True}
    base.update(over)
    return base


def call(api, payload):
    with patch(VERIFY, return_value=payload) as mocked:
        r = api.post(reverse("google-login"), {"id_token": "fake"}, format="json")
    return r, mocked


def test_not_configured_returns_503(api, settings):
    settings.GOOGLE_CLIENT_ID = ""
    r = api.post(reverse("google-login"), {"id_token": "x"}, format="json")
    assert r.status_code == 503


def test_invalid_token_returns_400(api):
    with patch(VERIFY, side_effect=ValueError("bad token")):
        r = api.post(reverse("google-login"), {"id_token": "x"}, format="json")
    assert r.status_code == 400


def test_token_is_verified_against_our_client_id(api):
    _, mocked = call(api, claims())
    assert mocked.call_args.args[2] == "test-client-id"


def test_unverified_google_email_is_rejected(api):
    r, _ = call(api, claims(email_verified=False))
    assert r.status_code == 400
    assert not User.objects.filter(email="gu@gmail.com").exists()


def test_new_user_is_created_and_needs_onboarding(api):
    r, _ = call(api, claims())
    assert r.status_code == 201
    assert r.data["needs_onboarding"] is True
    assert "access" in r.data
    assert r.cookies["refresh_token"]["httponly"]
    user = User.objects.get(email="gu@gmail.com")
    assert user.role == User.Role.PARTICIPANT
    assert user.is_email_verified is True
    assert SocialAccount.objects.filter(user=user, provider="google", uid="g-1").exists()


def test_repeat_login_reuses_same_account(api):
    call(api, claims())
    r, _ = call(api, claims())
    assert r.status_code == 200
    assert User.objects.filter(email="gu@gmail.com").count() == 1
    assert SocialAccount.objects.count() == 1


def test_links_to_existing_verified_account(api, make_user):
    existing = make_user(email="gu@gmail.com", is_email_verified=True)
    r, _ = call(api, claims())
    assert r.status_code == 200
    assert r.data["user"]["id"] == existing.id
    assert existing.social_accounts.count() == 1
    existing.refresh_from_db()
    assert existing.has_usable_password()  # пароль у проверенного аккаунта остаётся


def test_unverified_account_cannot_be_hijacked_with_preset_password(api, make_user):
    # Злоумышленник заранее зарегистрировал чужой email и поставил свой пароль
    victim = make_user(email="gu@gmail.com", is_email_verified=False)
    call(api, claims())
    victim.refresh_from_db()
    assert victim.is_email_verified is True
    assert not victim.has_usable_password()
    r = api.post(
        reverse("login"), {"email": "gu@gmail.com", "password": PASSWORD}, format="json"
    )
    assert r.status_code == 401


def test_cannot_disconnect_the_only_login_method(api):
    call(api, claims())
    user = User.objects.get(email="gu@gmail.com")
    api.force_authenticate(user)
    r = api.delete(reverse("provider-detail", args=["google"]))
    assert r.status_code == 400
    assert user.social_accounts.count() == 1


def test_can_disconnect_when_password_exists(api, make_user):
    user = make_user(email="gu@gmail.com", is_email_verified=True)
    call(api, claims())
    api.force_authenticate(user)
    assert api.delete(reverse("provider-detail", args=["google"])).status_code == 204
    assert user.social_accounts.count() == 0