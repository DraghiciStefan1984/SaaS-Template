from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordRecoveryRequestView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path(
        "password/recover/",
        PasswordRecoveryRequestView.as_view(),
        name="auth-password-recover",
    ),
    path("password/change/", PasswordChangeView.as_view(), name="auth-password-change"),
]
