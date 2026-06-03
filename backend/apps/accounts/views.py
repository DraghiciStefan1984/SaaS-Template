from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.audit.services import log_audit_event
from apps.organizations.serializers import OrganizationSerializer

from .serializers import (
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
)


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
        return Response(
            {
                "user": UserSerializer(user).data,
                "organization": OrganizationSerializer(
                    user.primary_organization,
                    context={"request": request, "current_user": user},
                ).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer
    throttle_scope = "auth"

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
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


class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_audit_event(
            action="auth.logout",
            user=request.user,
            request=request,
            category="auth",
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
