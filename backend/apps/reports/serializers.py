from rest_framework import serializers

from apps.common.serializers import validate_json_object

from .models import Report, ReportArtifact, ReportFormat, ReportTemplate


class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = (
            "id",
            "key",
            "name",
            "description",
            "default_format",
            "ai_task_profile",
            "config",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReportArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportArtifact
        fields = (
            "id",
            "report",
            "format",
            "storage_backend",
            "file_path",
            "external_url",
            "content",
            "checksum",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class ReportSerializer(serializers.ModelSerializer):
    template = ReportTemplateSerializer(read_only=True)

    class Meta:
        model = Report
        fields = (
            "id",
            "organization",
            "created_by",
            "template",
            "title",
            "status",
            "requested_format",
            "input_payload",
            "result_summary",
            "error_message",
            "related_entity_type",
            "related_entity_id",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReportSummarySerializer(serializers.ModelSerializer):
    template = ReportTemplateSerializer(read_only=True)

    class Meta:
        model = Report
        fields = (
            "id",
            "organization",
            "created_by",
            "template",
            "title",
            "status",
            "requested_format",
            "related_entity_type",
            "related_entity_id",
            "completed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ReportCreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    title = serializers.CharField(max_length=240)
    template_key = serializers.SlugField(required=False, allow_blank=True)
    requested_format = serializers.ChoiceField(
        choices=ReportFormat.choices,
        required=False,
        default=ReportFormat.JSON,
    )
    input_payload = serializers.JSONField(required=False, validators=[validate_json_object])
    related_entity_type = serializers.CharField(max_length=120, required=False, allow_blank=True)
    related_entity_id = serializers.CharField(max_length=120, required=False, allow_blank=True)

    def validate_template_key(self, value):
        if value and not ReportTemplate.objects.filter(key=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive report template.")
        return value
