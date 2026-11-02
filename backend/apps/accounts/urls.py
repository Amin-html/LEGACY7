from django.urls import path

from .email_views import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ResendVerificationView,
    VerifyEmailView,
)
from .google_views import GoogleLoginView
from .views import LoginView, LogoutView, MeView, RefreshView, RegisterView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("auth/verify-email/resend/", ResendVerificationView.as_view(), name="verify-email-resend"),
    path("auth/password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
    path("users/me/", MeView.as_view(), name="me"),
]