from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer
from .services import revoke_all_refresh_tokens
from .views import clear_refresh_cookie

User = get_user_model()


class OnboardingSerializer(serializers.ModelSerializer):
    # Выбирать можно только безопасные роли: jury и admin выдаёт админ
    role = serializers.ChoiceField(
        choices=[(r.value, r.label) for r in User.SELF_ASSIGNABLE_ROLES]
    )

    class Meta:
        model = User
        fields = ("username", "role")


class OnboardingView(APIView):
    """Первый вход через соцсеть: выбрать ник и роль. Работает один раз."""

    def post(self, request):
        user = request.user
        if user.onboarding_completed:
            return Response({"detail": "Онбординг уже пройден."}, status=400)
        serializer = OnboardingSerializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(onboarding_completed=True)
        return Response(UserSerializer(user).data)


class LogoutAllView(APIView):
    def post(self, request):
        revoke_all_refresh_tokens(request.user)
        response = Response(status=204)
        clear_refresh_cookie(response)
        return response


class ProvidersView(APIView):
    """Страница «Способы входа»: что подключено и есть ли пароль."""

    def get(self, request):
        user = request.user
        linked = [
            {"provider": s.provider, "connected_at": s.created_at}
            for s in user.social_accounts.all()
        ]
        return Response({"has_password": user.has_usable_password(), "linked": linked})


class ProviderDetailView(APIView):
    def delete(self, request, provider):
        user = request.user
        link = user.social_accounts.filter(provider=provider).first()
        if link is None:
            return Response({"detail": "Такой способ входа не подключён."}, status=404)
        if not user.has_usable_password() and user.social_accounts.count() <= 1:
            return Response(
                {"detail": "Это единственный способ входа. Сначала задай пароль через сброс пароля."},
                status=400,
            )
        link.delete()
        return Response(status=204)