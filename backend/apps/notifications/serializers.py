from rest_framework import serializers

from apps.common.serializers import validate_json_payload_size

from .models import (
    NotificationChannel,
    NotificationDeliveryLog,
    NotificationEvent,
    NotificationPreference,
)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = (
            "id",
            "organization",
            "user",
            "event",
            "channel",
            "is_enabled",
            "config",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class NotificationPreferenceUpsertSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    user_id = serializers.IntegerField(required=False, allow_null=True)
    event = serializers.ChoiceField(choices=NotificationEvent.values)
    channel = serializers.ChoiceField(choices=NotificationChannel.values)
    is_enabled = serializers.BooleanField(default=True)
    config = serializers.JSONField(required=False, validators=[validate_json_payload_size])


class NotificationDeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDeliveryLog
        fields = (
            "id",
            "organization",
            "user",
            "event",
            "channel",
            "status",
            "recipient",
            "subject",
            "payload",
            "provider",
            "provider_message_id",
            "error_message",
            "metadata",
            "sent_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
