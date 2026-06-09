from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from apps.common.serializers import validate_json_object
from apps.reports.models import ReportFormat, ReportTemplate

from .models import (
    JobRun,
    ScheduledRun,
    ScheduledWorkflow,
    ScheduleFrequency,
)


class JobRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobRun
        fields = (
            "id",
            "organization",
            "created_by",
            "name",
            "task_name",
            "status",
            "related_entity_type",
            "related_entity_id",
            "attempts",
            "max_attempts",
            "queued_at",
            "started_at",
            "finished_at",
            "last_error",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ScheduledWorkflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledWorkflow
        fields = (
            "id",
            "organization",
            "created_by",
            "name",
            "workflow_type",
            "status",
            "frequency",
            "timezone",
            "config",
            "next_run_at",
            "last_run_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ScheduledRunSerializer(serializers.ModelSerializer):
    job_run = JobRunSerializer(read_only=True)

    class Meta:
        model = ScheduledRun
        fields = (
            "id",
            "workflow",
            "job_run",
            "trigger",
            "scheduled_for",
            "created_at",
        )
        read_only_fields = fields


class ScheduledWorkflowCreateSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    name = serializers.CharField(max_length=160)
    frequency = serializers.ChoiceField(choices=ScheduleFrequency.values)
    timezone = serializers.CharField(max_length=64, default="UTC")
    next_run_at = serializers.DateTimeField(required=False)
    title = serializers.CharField(max_length=240)
    template_key = serializers.SlugField()
    requested_format = serializers.ChoiceField(
        choices=ReportFormat.choices,
        default=ReportFormat.JSON,
    )
    input_payload = serializers.JSONField(required=False, validators=[validate_json_object])

    def validate_template_key(self, value):
        if not ReportTemplate.objects.filter(key=value, is_active=True).exists():
            raise serializers.ValidationError("Unknown or inactive report template.")
        return value

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError("Unknown timezone.") from exc
        return value
