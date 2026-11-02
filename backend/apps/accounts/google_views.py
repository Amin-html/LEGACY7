import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from google.auth.exceptions import TransportError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import SocialAccount
from .serializers import UserSerializer
from .services import revoke_all_refresh_tokens
from .views import set_refresh_cookie

User = get_user_model()


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


def unique_username(email):
    base = re.sub(r"[^\w.@+-]", "", email.split("@")[0])[:30] or "user"
    candidate, i = base, 0
    while User.objects.filter(username__iexact=candidate).exists():
        i += 1
        candidate = f"{base}{i}"
    return candidate


@transaction.atomic
def get_or_create_google_user(payload):
    """Возвращает (user, created). Три случая: уже привязан / есть такой email / новый."""
    uid = payload["sub"]
    email = payload["email"].lower()

    link = SocialAccount.objects.select_related("user").filter(
        provider=SocialAccount.Provider.GOOGLE, uid=uid
    ).first()
    if link:
        return link.user, False

    user = User.objects.filter(email__iexact=email).first()
    if user:
        if not user.is_email_verified:
            # Защита от захвата аккаунта: пароль, который кто-то поставил на чужой
            # неподтверждённый email, сбрасываем. Владельцем считаем того, кто
            # доказал email через Google.
            user.set_unusable_password()
            user.is_email_verified = True
            user.save(update_fields=["password", "is_email_verified"])
            revoke_all_refresh_tokens(user)
        SocialAccount.objects.create(
            user=user, provider=SocialAccount.Provider.GOOGLE, uid=uid
        )
        return user, False

    user = User.objects.create_user(
        email=email,
        username=unique_username(email),
        password=None,
        is_email_verified=True,
        onboarding_completed=False,
    )
    SocialAccount.objects.create(user=user, provider=SocialAccount.Provider.GOOGLE, uid=uid)
    return user, True


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.GOOGLE_CLIENT_ID:
            return Response({"detail": "Вход через Google не настроен."}, status=503)

        try:
            payload = google_id_token.verify_oauth2_token(
                serializer.validated_data["id_token"],
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except TransportError:
            return Response({"detail": "Не удалось связаться с Google."}, status=502)
        except ValueError:
            return Response({"detail": "Недействительный токен Google."}, status=400)

        if not payload.get("email_verified") or not payload.get("email"):
            return Response({"detail": "Email в Google не подтверждён."}, status=400)

        user, created = get_or_create_google_user(payload)
        if not user.is_active:
            return Response({"detail": "Аккаунт отключён."}, status=403)

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "access": str(refresh.access_token),
                "needs_onboarding": not user.onboarding_completed,
                "user": UserSerializer(user).data,
            },
            status=201 if created else 200,
        )
        set_refresh_cookie(response, str(refresh))
        return response