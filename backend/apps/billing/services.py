from datetime import UTC, datetime

import stripe
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import Plan, Subscription, SubscriptionStatus

FREE_PLAN_SLUG = "free"


class BillingProviderNotConfigured(APIException):
    status_code = 503
    default_detail = (
        "Stripe is not configured yet. Create a Stripe account, add test API keys, "
        "configure price IDs, and set STRIPE_WEBHOOK_SECRET before enabling billing."
    )
    default_code = "billing_provider_not_configured"


class FeatureNotAvailable(APIException):
    status_code = 403
    default_detail = "This feature is not available on the current plan."
    default_code = "feature_not_available"


def get_free_plan():
    return Plan.objects.filter(slug=FREE_PLAN_SLUG, is_active=True).first()


def ensure_free_subscription(organization):
    try:
        return organization.subscription
    except ObjectDoesNotExist:
        pass

    plan = get_free_plan()
    if plan is None:
        return None

    return Subscription.objects.create(
        organization=organization,
        plan=plan,
        status=SubscriptionStatus.FREE,
    )


def get_subscription_for_organization(organization):
    return ensure_free_subscription(organization)


def get_plan_feature(organization, feature_name, default=False):
    subscription = get_subscription_for_organization(organization)
    if subscription is None or subscription.plan is None:
        return default
    return subscription.plan.features.get(feature_name, default)


def feature_enabled_for_organization(organization, feature_name, default=False):
    return bool(get_plan_feature(organization, feature_name, default=default))


def assert_feature_enabled(organization, feature_name, default=False):
    if not feature_enabled_for_organization(organization, feature_name, default=default):
        raise FeatureNotAvailable(
            f"Feature '{feature_name}' is not available on the current plan."
        )
    return True


def _stripe_timestamp_to_datetime(value):
    if not value:
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _object_get(value, key, default=None):
    if isinstance(value, dict):
        return value.get(key, default)
    try:
        return value[key]
    except (KeyError, TypeError):
        return default


def create_checkout_session(organization, plan, success_url, cancel_url):
    if not settings.STRIPE_SECRET_KEY:
        raise BillingProviderNotConfigured()
    if not plan.stripe_price_id:
        raise serializers.ValidationError(
            {"plan_slug": "This plan does not have a Stripe price ID configured yet."}
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_creation="always",
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        metadata={
            "organization_id": str(organization.id),
            "plan_slug": plan.slug,
        },
        subscription_data={
            "metadata": {
                "organization_id": str(organization.id),
                "plan_slug": plan.slug,
            }
        },
    )
    return {"checkout_url": session.url, "checkout_session_id": session.id}


def create_customer_portal_session(subscription, return_url):
    if not settings.STRIPE_SECRET_KEY:
        raise BillingProviderNotConfigured()
    if not subscription or not subscription.stripe_customer_id:
        raise serializers.ValidationError(
            {"organization_id": "This organization does not have a Stripe customer yet."}
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY
    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=return_url,
    )
    return {"portal_url": session.url}


def construct_stripe_event(payload, signature):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise BillingProviderNotConfigured()
    event = stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )
    return event


@transaction.atomic
def sync_checkout_session_completed(session):
    metadata = _object_get(session, "metadata", {}) or {}
    organization_id = _object_get(metadata, "organization_id")
    plan_slug = _object_get(metadata, "plan_slug")
    if not organization_id or not plan_slug:
        return None

    from apps.organizations.models import Organization

    organization = Organization.objects.get(id=organization_id)
    plan = Plan.objects.get(slug=plan_slug)
    subscription = ensure_free_subscription(organization)
    subscription.plan = plan
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.stripe_customer_id = _object_get(session, "customer") or ""
    subscription.stripe_subscription_id = _object_get(session, "subscription") or ""
    subscription.save(
        update_fields=[
            "plan",
            "status",
            "stripe_customer_id",
            "stripe_subscription_id",
            "updated_at",
        ]
    )
    return subscription


@transaction.atomic
def sync_stripe_subscription(stripe_subscription):
    subscription_id = _object_get(stripe_subscription, "id")
    metadata = _object_get(stripe_subscription, "metadata", {}) or {}
    organization_id = _object_get(metadata, "organization_id")
    plan_slug = _object_get(metadata, "plan_slug")

    subscription = Subscription.objects.filter(stripe_subscription_id=subscription_id).first()
    if subscription is None and organization_id:
        from apps.organizations.models import Organization

        organization = Organization.objects.get(id=organization_id)
        subscription = ensure_free_subscription(organization)

    if subscription is None:
        return None

    if plan_slug:
        subscription.plan = Plan.objects.get(slug=plan_slug)

    subscription.status = _object_get(stripe_subscription, "status") or subscription.status
    subscription.stripe_customer_id = _object_get(stripe_subscription, "customer") or ""
    subscription.stripe_subscription_id = subscription_id or ""
    subscription.current_period_start = _stripe_timestamp_to_datetime(
        _object_get(stripe_subscription, "current_period_start")
    )
    subscription.current_period_end = _stripe_timestamp_to_datetime(
        _object_get(stripe_subscription, "current_period_end")
    )
    subscription.trial_end = _stripe_timestamp_to_datetime(
        _object_get(stripe_subscription, "trial_end")
    )
    subscription.cancel_at_period_end = bool(
        _object_get(stripe_subscription, "cancel_at_period_end")
    )
    subscription.metadata = metadata
    subscription.save()
    return subscription


def process_stripe_event(event):
    event_type = _object_get(event, "type")
    data_object = _object_get(_object_get(event, "data", {}), "object", {})

    if event_type == "checkout.session.completed":
        sync_checkout_session_completed(data_object)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        sync_stripe_subscription(data_object)

    return {"received": True, "event_type": event_type}
