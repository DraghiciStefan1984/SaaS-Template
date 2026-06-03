from rest_framework import serializers

from .models import (
    DataDeletionRequest,
    DataDeletionTarget,
    DataExportRequest,
    DataExportScope,
)


class DataExportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataExportRequest
        fields = (
            "id",
            "organization",
            "requested_by",
            "scope",
            "status",
            "export_payload",
            "file_path",
            "error_message",
            "expires_at",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DataExportCreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    scope = serializers.ChoiceField(
        choices=DataExportScope.choices,
        default=DataExportScope.ORGANIZATION,
    )


class DataDeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataDeletionRequest
        fields = (
            "id",
            "organization",
            "requested_by",
            "target",
            "status",
            "reason",
            "metadata",
            "scheduled_for",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DataDeletionCreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    target = serializers.ChoiceField(
        choices=DataDeletionTarget.choices,
        default=DataDeletionTarget.ORGANIZATION,
    )
    reason = serializers.CharField(required=False, allow_blank=True)
