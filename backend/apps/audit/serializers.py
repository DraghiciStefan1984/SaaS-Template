from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id",
            "organization",
            "user",
            "action",
            "category",
            "status",
            "target_entity_type",
            "target_entity_id",
            "ip_address",
            "user_agent",
            "request_id",
            "metadata",
            "created_at",
        )
        read_only_fields = fields

