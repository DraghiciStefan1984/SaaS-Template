from django.urls import path

from .views import (
    EmailVerificationResendView,
    EmailVerificationView,
    GoogleLoginStatusView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordRecoveryRequestView,
    PasswordResetView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("email/verify/", EmailVerificationView.as_view(), name="auth-email-verify"),
    path(
        "email/verification/resend/",
        EmailVerificationResendView.as_view(),
        name="auth-email-verification-resend",
    ),
    path("social/google/", GoogleLoginView.as_view(), name="auth-google-login"),
    path(
        "social/google/status/",
        GoogleLoginStatusView.as_view(),
        name="auth-google-login-status",
    ),
    path(
        "password/recover/",
        PasswordRecoveryRequestView.as_view(),
        name="auth-password-recover",
    ),
    path("password/reset/", PasswordResetView.as_view(), name="auth-password-reset"),
    path("password/change/", PasswordChangeView.as_view(), name="auth-password-change"),
]
