import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.services import make_email_token

User = get_user_model()
PASSWORD = "Str0ng-Pass-123"
pytestmark = pytest.mark.django_db


def do_login(api, email, password=PASSWORD):
    return api.post(reverse("login"), {"email": email, "password": password}, format="json")


class TestRegistration:
    def test_creates_user_profile_and_sends_verification_email(self, api):
        r = api.post(
            reverse("register"),
            {"email": "New@Example.com", "username": "newbie", "password": PASSWORD},
            format="json",
        )
        assert r.status_code == 201
        assert "password" not in r.data
        user = User.objects.get(email="new@example.com")
        assert user.role == User.Role.PARTICIPANT
        assert user.is_email_verified is False
        assert user.profile is not None
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["new@example.com"]

    def test_organizer_role_is_allowed(self, api):
        r = api.post(
            reverse("register"),
            {"email": "org@example.com", "username": "org", "password": PASSWORD, "role": "organizer"},
            format="json",
        )
        assert r.status_code == 201
        assert User.objects.get(email="org@example.com").role == User.Role.ORGANIZER

    @pytest.mark.parametrize("role", ["admin", "jury"])
    def test_cannot_self_assign_privileged_role(self, api, role):
        r = api.post(
            reverse("register"),
            {"email": "x@example.com", "username": "x", "password": PASSWORD, "role": role},
            format="json",
        )
        assert r.status_code == 400
        assert not User.objects.filter(email="x@example.com").exists()

    def test_duplicate_email_is_rejected_case_insensitively(self, api, make_user):
        make_user(email="dup@example.com")
        r = api.post(
            reverse("register"),
            {"email": "DUP@example.com", "username": "other", "password": PASSWORD},
            format="json",
        )
        assert r.status_code == 400
        assert "email" in r.data

    def test_weak_password_is_rejected(self, api):
        r = api.post(
            reverse("register"),
            {"email": "weak@example.com", "username": "weak", "password": "12345678"},
            format="json",
        )
        assert r.status_code == 400
        assert not User.objects.filter(email="weak@example.com").exists()


class TestTokens:
    def test_login_hides_refresh_in_body_and_sets_httponly_cookie(self, api, make_user):
        make_user(email="a@example.com")
        r = do_login(api, "a@example.com")
        assert r.status_code == 200
        assert "access" in r.data
        assert "refresh" not in r.data
        assert r.cookies["refresh_token"]["httponly"]

    def test_wrong_password_gives_401(self, api, make_user):
        make_user(email="a@example.com")
        assert do_login(api, "a@example.com", "wrong-pass-999").status_code == 401

    def test_refresh_rotates_token_and_old_one_is_dead(self, api, make_user):
        make_user(email="a@example.com")
        do_login(api, "a@example.com")
        old = api.cookies["refresh_token"].value

        r = api.post(reverse("refresh"))
        assert r.status_code == 200
        assert "access" in r.data
        assert r.cookies["refresh_token"].value != old

        api.cookies["refresh_token"] = old  # повторное использование старого токена
        assert api.post(reverse("refresh")).status_code == 401

    def test_refresh_without_cookie_gives_401(self, api):
        assert api.post(reverse("refresh")).status_code == 401

    def test_logout_blacklists_refresh_token(self, api, make_user):
        make_user(email="a@example.com")
        do_login(api, "a@example.com")
        old = api.cookies["refresh_token"].value

        assert api.post(reverse("logout")).status_code == 204
        api.cookies["refresh_token"] = old
        assert api.post(reverse("refresh")).status_code == 401

    def test_logout_all_kills_every_session(self, api, make_user):
        make_user(email="a@example.com")
        r = do_login(api, "a@example.com")
        old = api.cookies["refresh_token"].value

        api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        assert api.post(reverse("logout-all")).status_code == 204
        api.credentials()

        api.cookies["refresh_token"] = old
        assert api.post(reverse("refresh")).status_code == 401


class TestMe:
    def test_requires_authentication(self, api):
        assert api.get(reverse("me")).status_code == 401

    def test_user_cannot_change_own_role(self, api, make_user):
        user = make_user()
        api.force_authenticate(user)
        r = api.patch(reverse("me"), {"role": "admin", "bio": "hello"}, format="json")
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.role == User.Role.PARTICIPANT
        assert user.profile.bio == "hello"


class TestEmailVerification:
    def test_valid_token_verifies_email(self, api, make_user):
        user = make_user()
        r = api.post(reverse("verify-email"), {"token": make_email_token(user)}, format="json")
        assert r.status_code == 200
        user.refresh_from_db()
        assert user.is_email_verified is True

    def test_garbage_token_is_rejected(self, api, make_user):
        make_user()
        r = api.post(reverse("verify-email"), {"token": "garbage"}, format="json")
        assert r.status_code == 400


class TestPasswordReset:
    def test_unknown_email_gets_204_and_no_mail(self, api):
        r = api.post(reverse("password-reset"), {"email": "nobody@example.com"}, format="json")
        assert r.status_code == 204
        assert len(mail.outbox) == 0

    def test_known_email_gets_mail(self, api, make_user):
        make_user(email="a@example.com")
        r = api.post(reverse("password-reset"), {"email": "a@example.com"}, format="json")
        assert r.status_code == 204
        assert len(mail.outbox) == 1

    def test_full_flow_changes_password_revokes_sessions_and_token_is_single_use(
        self, api, make_user
    ):
        user = make_user(email="a@example.com")
        do_login(api, "a@example.com")
        old_refresh = api.cookies["refresh_token"].value

        user.refresh_from_db()  # логин обновил last_login, а токен сброса от него зависит
        payload = {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
            "new_password": "Brand-New-Pass-456",
        }
        assert api.post(reverse("password-reset-confirm"), payload, format="json").status_code == 200

        assert do_login(api, "a@example.com", PASSWORD).status_code == 401
        assert do_login(api, "a@example.com", "Brand-New-Pass-456").status_code == 200

        api.cookies["refresh_token"] = old_refresh
        assert api.post(reverse("refresh")).status_code == 401

        again = api.post(reverse("password-reset-confirm"), payload, format="json")
        assert again.status_code == 400


class TestOnboarding:
    def test_cannot_choose_privileged_role(self, api, make_user):
        user = make_user(onboarding_completed=False)
        api.force_authenticate(user)
        r = api.post(reverse("onboarding"), {"username": "newname", "role": "admin"}, format="json")
        assert r.status_code == 400
        user.refresh_from_db()
        assert user.onboarding_completed is False

    def test_works_once(self, api, make_user):
        user = make_user(onboarding_completed=False)
        api.force_authenticate(user)
        body = {"username": "newname", "role": "organizer"}

        assert api.post(reverse("onboarding"), body, format="json").status_code == 200
        user.refresh_from_db()
        assert user.role == User.Role.ORGANIZER
        assert user.onboarding_completed is True

        assert api.post(reverse("onboarding"), body, format="json").status_code == 400