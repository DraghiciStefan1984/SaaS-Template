from rest_framework import serializers

from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
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


class CheckoutSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    plan_slug = serializers.SlugField()
    success_url = serializers.URLField(required=False)
    cancel_url = serializers.URLField(required=False)


class CustomerPortalSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    return_url = serializers.URLField(required=False)


class CheckoutSessionSerializer(serializers.Serializer):
    checkout_url = serializers.URLField()
    checkout_session_id = serializers.CharField()


class CustomerPortalSessionSerializer(serializers.Serializer):
    portal_url = serializers.URLField()


class StripeWebhookResponseSerializer(serializers.Serializer):
    received = serializers.BooleanField()
    event_type = serializers.CharField(allow_null=True, required=False)
