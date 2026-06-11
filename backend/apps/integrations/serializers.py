from rest_framework import serializers

from apps.common.serializers import validate_json_object

from .models import (
    CredentialType,
    IntegrationAccount,
    IntegrationProvider,
    IntegrationSyncLog,
    ProviderAuthType,
)
from .services import (
    connect_integration_account,
    provider_credential_fields,
    provider_health_check,
    provider_is_customer_configurable,
    reconnect_integration_account,
)


class IntegrationProviderSerializer(serializers.ModelSerializer):
    health = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    credential_fields = serializers.SerializerMethodField()
    is_customer_configurable = serializers.SerializerMethodField()

    class Meta:
        model = IntegrationProvider
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "auth_type",
            "scopes",
            "status",
            "feature_flags",
            "description",
            "credential_fields",
            "is_customer_configurable",
            "health",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_health(self, obj) -> dict:
        return provider_health_check(obj)

    def get_description(self, obj) -> str:
        description = obj.config.get("description", "")
        return description if isinstance(description, str) else ""

    def get_credential_fields(self, obj) -> list[dict]:
        return provider_credential_fields(obj)

    def get_is_customer_configurable(self, obj) -> bool:
        return provider_is_customer_configurable(obj)


class IntegrationAccountSerializer(serializers.ModelSerializer):
    provider = IntegrationProviderSerializer(read_only=True)
    has_credential = serializers.SerializerMethodField()

    class Meta:
        model = IntegrationAccount
        fields = (
            "id",
            "organization",
            "provider",
            "display_name",
            "status",
            "has_credential",
            "last_sync_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_has_credential(self, obj) -> bool:
        return hasattr(obj, "credential")


class ConnectIntegrationSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    external_account_id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    credential_type = serializers.ChoiceField(
        choices=CredentialType.choices,
        required=False,
        default=CredentialType.API_KEY,
    )
    credential_payload = serializers.JSONField(
        required=False,
        write_only=True,
        validators=[validate_json_object],
    )
    metadata = serializers.JSONField(required=False, validators=[validate_json_object])

    def validate(self, attrs):
        provider = self.context["provider"]
        if provider.auth_type == ProviderAuthType.NONE:
            attrs.pop("credential_payload", None)
        return attrs

    def create(self, validated_data):
        provider = validated_data.pop("provider", self.context["provider"])
        organization = validated_data.pop("organization")
        request = validated_data.pop("request")
        return connect_integration_account(
            organization=organization,
            provider=provider,
            connected_by=request.user,
            external_account_id=validated_data.get("external_account_id", ""),
            display_name=validated_data.get("display_name", ""),
            scopes=validated_data.get("scopes"),
            credential_type=validated_data.get("credential_type"),
            credential_payload=validated_data.get("credential_payload"),
            metadata=validated_data.get("metadata"),
        )


class IntegrationSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationSyncLog
        fields = (
            "id",
            "integration_account",
            "action",
            "status",
            "started_at",
            "completed_at",
            "error_message",
            "external_request_id",
            "rate_limit_reset_at",
            "retry_count",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class ReconnectIntegrationSerializer(serializers.Serializer):
    external_account_id = serializers.CharField(required=False, allow_blank=True, max_length=255)
    display_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    credential_type = serializers.ChoiceField(
        choices=CredentialType.choices,
        required=False,
        default=CredentialType.API_KEY,
    )
    credential_payload = serializers.JSONField(
        required=False,
        write_only=True,
        validators=[validate_json_object],
    )

    def create(self, validated_data):
        return reconnect_integration_account(
            self.context["account"],
            connected_by=self.context["request"].user,
            **validated_data,
        )


class DisconnectIntegrationResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
