from rest_framework import serializers

from .models import JobRun


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

