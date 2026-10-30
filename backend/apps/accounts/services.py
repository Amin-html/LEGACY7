from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

EMAIL_VERIFY_SALT = "legacy7.email-verify"
EMAIL_VERIFY_MAX_AGE = 60 * 60 * 24 * 3  # 3 дня


def make_email_token(user):
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=EMAIL_VERIFY_SALT)


def read_email_token(token):
    """Вернёт пользователя или None. Бросит signing.BadSignature, если токен битый/просрочен."""
    data = signing.loads(token, salt=EMAIL_VERIFY_SALT, max_age=EMAIL_VERIFY_MAX_AGE)
    return get_user_model().objects.filter(pk=data["uid"], email=data["email"]).first()


def send_verification_email(user):
    token = quote(make_email_token(user), safe=":")
    url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    send_mail(
        "Подтверди email — LEGACY 7",
        f"Привет, {user.username}!\n\nПодтверди email по ссылке:\n{url}\n\nСсылка действует 3 дня.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        "Сброс пароля — LEGACY 7",
        f"Чтобы задать новый пароль, перейди по ссылке:\n{url}\n\nСсылка действует 1 час. "
        "Если это был не ты, просто игнорируй письмо.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


def revoke_all_refresh_tokens(user):
    """Выход со всех устройств: все refresh-токены пользователя в чёрный список."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)