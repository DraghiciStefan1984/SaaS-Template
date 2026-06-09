import logging
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.audit.services import log_audit_event
from apps.organizations.serializers import OrganizationSerializer

from .serializers import (
    AccountStatusTokenRefreshSerializer,
    DetailResponseSerializer,
    EmailTokenObtainPairSerializer,
    EmailVerificationSerializer,
    GoogleCredentialSerializer,
    GoogleLoginStatusSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordRecoveryRequestSerializer,
    PasswordResetSerializer,
    RegisterSerializer,
    SocialLoginResponseSerializer,
    UserSerializer,
)
from .services import (
    blacklist_user_refresh_tokens,
    get_or_create_google_user,
    google_login_configuration,
    send_email_verification_email,
    send_password_reset_email,
    verify_google_identity_token,
)

logger = logging.getLogger(__name__)


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


def _set_google_nonce_cookie(response, nonce):
    response.set_cookie(
        settings.GOOGLE_OAUTH_NONCE_COOKIE_NAME,
        nonce,
        max_age=settings.GOOGLE_OAUTH_NONCE_MAX_AGE,
        path="/api/v1/auth/social/google/",
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
    )


def _delete_google_nonce_cookie(response):
    response.delete_cookie(
        settings.GOOGLE_OAUTH_NONCE_COOKIE_NAME,
        path="/api/v1/auth/social/google/",
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
    )


def _mutable_request_data(request):
    if hasattr(request.data, "copy"):
        return request.data.copy()
    return dict(request.data)


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
        try:
            send_email_verification_email(user)
            log_audit_event(
                action="auth.email_verification_sent",
                organization=user.primary_organization,
                user=user,
                request=request,
                category="auth",
            )
        except Exception:
            logger.exception("Registration succeeded but verification email could not be sent.")
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


class EmailVerificationView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationSerializer
    throttle_scope = "auth"

    @extend_schema(
        request=EmailVerificationSerializer,
        responses={status.HTTP_200_OK: DetailResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_audit_event(
            action="auth.email_verified",
            user=user,
            request=request,
            category="auth",
        )
        return Response({"detail": "Email address verified."})


class EmailVerificationResendView(APIView):
    throttle_scope = "auth"

    @extend_schema(request=None, responses={status.HTTP_202_ACCEPTED: DetailResponseSerializer})
    def post(self, request):
        if not request.user.is_email_verified:
            send_email_verification_email(request.user)
            log_audit_event(
                action="auth.email_verification_sent",
                user=request.user,
                request=request,
                category="auth",
            )
        return Response(
            {"detail": "If verification is still required, a new email has been sent."},
            status=status.HTTP_202_ACCEPTED,
        )


class GoogleLoginStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=GoogleLoginStatusSerializer)
    def get(self, request):
        nonce = secrets.token_urlsafe(32)
        configuration = google_login_configuration(nonce)
        response = Response(configuration)
        if configuration["enabled"]:
            _set_google_nonce_cookie(response, nonce)
        return response


class GoogleLoginView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleCredentialSerializer
    throttle_scope = "auth"

    @extend_schema(
        request=GoogleCredentialSerializer,
        responses={status.HTTP_200_OK: SocialLoginResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claims = verify_google_identity_token(
            serializer.validated_data["credential"],
            request.COOKIES.get(settings.GOOGLE_OAUTH_NONCE_COOKIE_NAME, ""),
        )
        user = get_or_create_google_user(claims)
        refresh = RefreshToken.for_user(user)
        log_audit_event(
            action="auth.google_login",
            user=user,
            request=request,
            category="auth",
        )
        response = Response(
            {"access": str(refresh.access_token), "user": UserSerializer(user).data}
        )
        _set_refresh_cookie(response, refresh)
        _delete_google_nonce_cookie(response)
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
        user = get_user_model().objects.filter(
            email__iexact=email,
            is_active=True,
            account_status="active",
        ).first()
        if user is not None:
            send_password_reset_email(user)
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
                    "instructions have been sent."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


class PasswordResetView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetSerializer
    throttle_scope = "auth"

    @extend_schema(
        request=PasswordResetSerializer,
        responses={status.HTTP_200_OK: DetailResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_audit_event(
            action="auth.password_reset_completed",
            user=user,
            request=request,
            category="auth",
        )
        response = Response({"detail": "Password reset completed."})
        _delete_refresh_cookie(response)
        return response


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
            blacklist_user_refresh_tokens(user)
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
