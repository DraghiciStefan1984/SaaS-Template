import hashlib
import hmac
import json
import time

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.billing.models import Plan, Subscription, SubscriptionStatus
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner
from apps.usage.models import UsageRecord
from apps.usage.services import UsageLimitExceeded, assert_within_usage_limit, record_usage

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def stripe_signature_header(payload, secret):
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}".encode()
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


def test_default_public_plans_are_available_without_authentication():
    client = APIClient()

    response = client.get("/api/v1/billing/plans/")

    assert response.status_code == 200
    slugs = [plan["slug"] for plan in response.json()]
    assert slugs == ["free", "starter", "pro", "agency"]


def test_new_organization_receives_free_subscription(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")

    organization = create_organization_for_owner(owner, "Owner Workspace")

    subscription = Subscription.objects.get(organization=organization)
    assert subscription.plan.slug == "free"
    assert subscription.status == SubscriptionStatus.FREE


def test_subscription_endpoint_returns_org_subscription(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/v1/billing/subscription/?organization_id={organization.id}")

    assert response.status_code == 200
    assert response.json()["plan"]["slug"] == "free"


def test_checkout_requires_admin_role(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.post(
        "/api/v1/billing/checkout/",
        {"organization_id": organization.id, "plan_slug": "starter"},
        format="json",
    )

    assert response.status_code == 403


def test_checkout_returns_descriptive_error_until_stripe_is_configured(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/billing/checkout/",
        {"organization_id": organization.id, "plan_slug": "starter"},
        format="json",
    )

    assert response.status_code == 503
    assert "Stripe is not configured yet" in response.json()["detail"]


def test_customer_portal_returns_descriptive_error_until_stripe_is_configured(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/billing/customer-portal/",
        {"organization_id": organization.id},
        format="json",
    )

    assert response.status_code == 503
    assert "Stripe is not configured yet" in response.json()["detail"]


def test_usage_records_are_summarized_for_current_plan(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    record_usage(organization, "one_click_requests", quantity=2, source="test")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/v1/usage/summary/?organization_id={organization.id}")

    assert response.status_code == 200
    body = response.json()
    metric = next(item for item in body["metrics"] if item["metric_name"] == "one_click_requests")
    assert metric["used"] == "2"
    assert metric["limit"] == 3


def test_usage_limit_service_blocks_requests_over_plan_limit(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    record_usage(organization, "one_click_requests", quantity=3, source="test")

    with pytest.raises(UsageLimitExceeded):
        assert_within_usage_limit(organization, "one_click_requests", quantity=1)


def test_stripe_webhook_requires_configuration():
    client = APIClient()

    response = client.post(
        "/api/v1/billing/webhooks/stripe/",
        data="{}",
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE="t=123,v1=invalid",
    )

    assert response.status_code == 503
    assert "Stripe is not configured yet" in response.json()["detail"]


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_signed_stripe_checkout_webhook_updates_subscription(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    assert organization.subscription.plan.slug == "free"
    assert organization.subscription.status == SubscriptionStatus.FREE

    payload = json.dumps(
        {
            "id": "evt_checkout_completed",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "object": "checkout.session",
                    "customer": "cus_test_123",
                    "subscription": "sub_test_123",
                    "metadata": {
                        "organization_id": str(organization.id),
                        "plan_slug": "starter",
                    },
                }
            },
        },
        separators=(",", ":"),
    )
    client = APIClient()

    response = client.post(
        "/api/v1/billing/webhooks/stripe/",
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=stripe_signature_header(payload, "whsec_test"),
    )

    assert response.status_code == 200
    organization.subscription.refresh_from_db()
    assert organization.subscription.plan == Plan.objects.get(slug="starter")
    assert organization.subscription.status == SubscriptionStatus.ACTIVE
    assert organization.subscription.stripe_customer_id == "cus_test_123"
    assert organization.subscription.stripe_subscription_id == "sub_test_123"
    assert UsageRecord.objects.count() == 0
