from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserAccountStatus
from apps.accounts.services import (
    get_password_reset_user,
    reset_user_password,
    verify_email_verification_token,
)
from apps.organizations.services import create_organization_for_owner

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "name",
            "is_email_verified",
            "account_status",
            "date_joined",
        )
        read_only_fields = ("id", "email", "is_email_verified", "account_status", "date_joined")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    organization_name = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data):
        organization_name = validated_data.pop("organization_name", "")
        user = User.objects.create_user(**validated_data)
        organization = create_organization_for_owner(
            owner=user,
            name=organization_name or f"{user.email}'s workspace",
        )
        user.primary_organization = organization
        return user


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.account_status != UserAccountStatus.ACTIVE:
            raise AuthenticationFailed("This account is not active.")

        data["user"] = UserSerializer(self.user).data
        return data


class AccountStatusTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = self.token_class(attrs["refresh"])
        except TokenError as error:
            raise InvalidToken(str(error)) from error
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(id=user_id).first()
        if user is None or user.account_status != UserAccountStatus.ACTIVE:
            raise AuthenticationFailed("This account is not active.")
        return super().validate(attrs)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        refresh = attrs.get("refresh", "")
        try:
            self.token = RefreshToken(refresh) if refresh else None
        except TokenError:
            self.token = None
        return attrs

    def save(self, **kwargs):
        if self.token:
            self.token.blacklist()


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=False, max_length=4096)

    def save(self, **kwargs):
        try:
            return verify_email_verification_token(self.validated_data["token"])
        except ValueError as exc:
            raise serializers.ValidationError({"token": str(exc)}) from exc


class GoogleCredentialSerializer(serializers.Serializer):
    credential = serializers.CharField(write_only=True, trim_whitespace=False, max_length=16384)


class GoogleLoginStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    client_id = serializers.CharField(allow_blank=True)
    nonce = serializers.CharField(allow_blank=True)


class SocialLoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = UserSerializer()


class PasswordRecoveryRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return User.objects.normalize_email(value)


class PasswordResetSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate(self, attrs):
        user = get_password_reset_user(attrs["uid"])
        if user is None or not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "This password reset link is invalid."})
        if not user.is_active or user.account_status != UserAccountStatus.ACTIVE:
            raise serializers.ValidationError({"token": "This account is not active."})
        validate_password(attrs["new_password"], user)
        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        return reset_user_password(
            user=self.validated_data["user"],
            new_password=self.validated_data["new_password"],
        )


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
