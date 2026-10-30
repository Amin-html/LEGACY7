from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .services import (
    read_email_token,
    revoke_all_refresh_tokens,
    send_password_reset_email,
    send_verification_email,
)

User = get_user_model()


class PublicAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class VerifyEmailView(PublicAuthView):
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = read_email_token(serializer.validated_data["token"])
        except signing.BadSignature:  # включает просроченный токен
            user = None
        if user is None:
            return Response({"detail": "Ссылка недействительна или устарела."}, status=400)
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        return Response({"detail": "Email подтверждён."})


class ResendVerificationView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if request.user.is_email_verified:
            return Response({"detail": "Email уже подтверждён."}, status=400)
        send_verification_email(request.user)
        return Response(status=204)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestView(PublicAuthView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True
        ).first()
        if user:
            send_password_reset_email(user)
        # Всегда 204: нельзя узнать, есть ли такой email в системе
        return Response(status=204)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)


class PasswordResetConfirmView(PublicAuthView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data["uid"])))
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is None or not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": "Ссылка недействительна или устарела."}, status=400)
        try:
            validate_password(data["new_password"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        revoke_all_refresh_tokens(user)  # старые сессии больше не живы
        return Response({"detail": "Пароль изменён."})