from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit.services import log_audit_event
from apps.organizations.serializers import OrganizationSerializer

from .serializers import (
    AccountStatusTokenRefreshSerializer,
    DetailResponseSerializer,
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordRecoveryRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)


def _refresh_cookie_name():
    return settings.AUTH_REFRESH_COOKIE_NAME


def _refresh_cookie_kwargs():
    return {
        "path": settings.AUTH_REFRESH_COOKIE_PATH,
        "domain": settings.AUTH_REFRESH_COOKIE_DOMAIN or None,
        "secure": settings.AUTH_REFRESH_COOKIE_SECURE,
        "httponly": True,
        "samesite": settings.AUTH_REFRESH_COOKIE_SAMESITE,
    }


def _set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        _refresh_cookie_name(),
        str(refresh_token),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        **_refresh_cookie_kwargs(),
    )


def _delete_refresh_cookie(response):
    response.delete_cookie(
        _refresh_cookie_name(),
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        domain=settings.AUTH_REFRESH_COOKIE_DOMAIN or None,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
    )


def _mutable_request_data(request):
    if hasattr(request.data, "copy"):
        return request.data.copy()
    return dict(request.data)


def _blacklist_user_refresh_tokens(user):
    for outstanding_token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding_token)


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        log_audit_event(
            action="auth.register",
            organization=user.primary_organization,
            user=user,
            request=request,
            category="auth",
        )
        response = Response(
            {
                "user": UserSerializer(user).data,
                "organization": OrganizationSerializer(
                    user.primary_organization,
                    context={"request": request, "current_user": user},
                ).data,
                "tokens": {
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, refresh)
        return response


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        refresh = response.data.pop("refresh", "")
        if refresh:
            _set_refresh_cookie(response, refresh)
        user_id = (
            response.data.get("user", {}).get("id") if isinstance(response.data, dict) else None
        )
        user = get_user_model().objects.filter(id=user_id).first() if user_id else None
        log_audit_event(
            action="auth.login",
            user=user,
            request=request,
            category="auth",
        )
        return response


class RefreshView(TokenRefreshView):
    serializer_class = AccountStatusTokenRefreshSerializer
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        data = _mutable_request_data(request)
        if not data.get("refresh"):
            cookie_refresh = request.COOKIES.get(_refresh_cookie_name())
            if cookie_refresh:
                data["refresh"] = cookie_refresh
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        response_data = dict(serializer.validated_data)
        refresh = response_data.pop("refresh", "")
        response = Response(response_data, status=status.HTTP_200_OK)
        if refresh:
            _set_refresh_cookie(response, refresh)
        return response


class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        data = _mutable_request_data(request)
        if not data.get("refresh"):
            cookie_refresh = request.COOKIES.get(_refresh_cookie_name())
            if cookie_refresh:
                data["refresh"] = cookie_refresh
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_audit_event(
            action="auth.logout",
            user=request.user,
            request=request,
            category="auth",
        )
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _delete_refresh_cookie(response)
        return response


class PasswordRecoveryRequestView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordRecoveryRequestSerializer
    throttle_scope = "auth"

    @extend_schema(
        request=PasswordRecoveryRequestSerializer,
        responses={status.HTTP_202_ACCEPTED: DetailResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = get_user_model().objects.filter(email__iexact=email).first()
        log_audit_event(
            action="auth.password_recovery_requested",
            user=user,
            request=request,
            category="auth",
            metadata={"email_known": bool(user)},
        )
        return Response(
            {
                "detail": (
                    "If an account exists for this email, password recovery "
                    "instructions will be sent when email delivery is configured."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer
    throttle_scope = "auth"

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={status.HTTP_200_OK: DetailResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
            _blacklist_user_refresh_tokens(user)
        log_audit_event(
            action="auth.password_changed",
            user=request.user,
            request=request,
            category="auth",
        )
        response = Response({"detail": "Password changed."})
        _delete_refresh_cookie(response)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
