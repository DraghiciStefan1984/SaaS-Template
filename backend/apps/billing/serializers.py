from urllib.parse import urlparse

from django.conf import settings
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Plan, Subscription


def validate_billing_redirect_url(value):
    parsed_url = urlparse(value)
    frontend_host = urlparse(settings.FRONTEND_BASE_URL).netloc
    allowed_hosts = {frontend_host, *settings.BILLING_ALLOWED_REDIRECT_HOSTS}
    if parsed_url.scheme not in {"http", "https"} or parsed_url.netloc not in allowed_hosts:
        raise serializers.ValidationError("Redirect URL host is not allowed.")
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if (
        parsed_url.scheme == "http"
        and not settings.DEBUG
        and parsed_url.hostname not in local_hosts
    ):
        raise serializers.ValidationError("Redirect URL must use HTTPS outside local development.")
    return value


class PlanSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DictField(child=serializers.BooleanField()))
    def get_features(self, plan):
        if not isinstance(plan.features, dict):
            return {}
        return {
            name: enabled
            for name, enabled in plan.features.items()
            if isinstance(name, str) and isinstance(enabled, bool)
        }

    class Meta:
        model = Plan
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "features",
            "limits",
            "is_public",
            "display_order",
        )
        read_only_fields = fields


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "organization",
            "plan",
            "status",
            "stripe_customer_id",
            "stripe_subscription_id",
            "current_period_start",
            "current_period_end",
            "trial_end",
            "cancel_at_period_end",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SubscriptionSummarySerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "organization",
            "plan",
            "status",
            "current_period_start",
            "current_period_end",
            "trial_end",
            "cancel_at_period_end",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EntitlementPlanSerializer(serializers.Serializer):
    slug = serializers.SlugField()
    name = serializers.CharField()
    status = serializers.CharField()


class OrganizationEntitlementsSerializer(serializers.Serializer):
    organization = serializers.IntegerField()
    plan = EntitlementPlanSerializer(allow_null=True)
    features = serializers.DictField(child=serializers.BooleanField())


class CheckoutSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    plan_slug = serializers.SlugField()
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)

    def validate_success_url(self, value):
        return validate_billing_redirect_url(value)

    def validate_cancel_url(self, value):
        return validate_billing_redirect_url(value)


class CustomerPortalSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    return_url = serializers.URLField(required=False)

    def validate_return_url(self, value):
        return validate_billing_redirect_url(value)


class CheckoutSessionSerializer(serializers.Serializer):
    checkout_url = serializers.URLField()
    checkout_session_id = serializers.CharField()


class CustomerPortalSessionSerializer(serializers.Serializer):
    portal_url = serializers.URLField()


class StripeWebhookResponseSerializer(serializers.Serializer):
    received = serializers.BooleanField()
    event_type = serializers.CharField(allow_null=True, required=False)
    processed = serializers.BooleanField(required=False)
    duplicate = serializers.BooleanField(required=False)
