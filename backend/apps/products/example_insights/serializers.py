from rest_framework import serializers

from .models import ExampleInsightRequest
from .services import create_example_insight_request


class ExampleInsightRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExampleInsightRequest
        fields = (
            "id",
            "organization",
            "created_by",
            "report",
            "job_run",
            "title",
            "status",
            "input_payload",
            "constraints",
            "ai_execution_plan",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ExampleInsightCreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    title = serializers.CharField(max_length=240)
    input_payload = serializers.JSONField(required=False)
    constraints = serializers.JSONField(required=False)

    def create(self, validated_data):
        return create_example_insight_request(
            organization=validated_data["organization"],
            created_by=validated_data["created_by"],
            title=validated_data["title"],
            input_payload=validated_data.get("input_payload", {}),
            constraints=validated_data.get("constraints", {}),
        )

