from rest_framework import serializers

from .models import UsageRecord


class UsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageRecord
        fields = (
            "id",
            "organization",
            "subscription",
            "period_start",
            "period_end",
            "metric_name",
            "quantity",
            "source",
            "product_scope",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class UsageMetricSummarySerializer(serializers.Serializer):
    metric_name = serializers.CharField()
    used = serializers.CharField()
    limit = serializers.JSONField()


class UsagePlanSummarySerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    status = serializers.CharField()


class UsagePeriodSummarySerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()


class UsageSummarySerializer(serializers.Serializer):
    plan = UsagePlanSummarySerializer(allow_null=True)
    period = UsagePeriodSummarySerializer(allow_null=True)
    metrics = UsageMetricSummarySerializer(many=True)
