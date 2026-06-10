import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from django.db import close_old_connections, connection
from django.test import override_settings
from rest_framework.test import APIClient

from apps.billing.models import (
    Plan,
    StripeWebhookEvent,
    StripeWebhookEventStatus,
    Subscription,
    SubscriptionStatus,
)
from apps.billing.services import (
    create_checkout_session,
    create_customer_portal_session,
    feature_enabled_for_organization,
)
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner
from apps.usage.models import UsageRecord
from apps.usage.services import (
    UsageLimitExceeded,
    assert_within_usage_limit,
    check_and_record_usage,
    record_usage,
)

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


def test_entitlements_endpoint_returns_only_safe_boolean_plan_features(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    plan = organization.subscription.plan
    plan.features = {
        **plan.features,
        "safe_enabled": True,
        "safe_disabled": False,
        "internal_configuration": {"provider": "private"},
    }
    plan.save(update_fields=["features", "updated_at"])
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/v1/billing/entitlements/?organization_id={organization.id}")

    assert response.status_code == 200
    assert response.json()["organization"] == organization.id
    assert response.json()["plan"]["slug"] == "free"
    assert response.json()["features"]["safe_enabled"] is True
    assert response.json()["features"]["safe_disabled"] is False
    assert "internal_configuration" not in response.json()["features"]
    public_plans = client.get("/api/v1/billing/plans/").json()
    public_free_plan = next(item for item in public_plans if item["slug"] == "free")
    assert "internal_configuration" not in public_free_plan["features"]


def test_entitlements_endpoint_is_organization_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(other)

    response = client.get(f"/api/v1/billing/entitlements/?organization_id={organization.id}")

    assert response.status_code == 404


def test_subscription_endpoint_hides_stripe_identifiers_from_members(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    organization.subscription.stripe_customer_id = "cus_private"
    organization.subscription.stripe_subscription_id = "sub_private"
    organization.subscription.save(
        update_fields=["stripe_customer_id", "stripe_subscription_id", "updated_at"]
    )
    client = APIClient()

    client.force_authenticate(member)
    member_response = client.get(
        f"/api/v1/billing/subscription/?organization_id={organization.id}"
    )
    client.force_authenticate(owner)
    owner_response = client.get(
        f"/api/v1/billing/subscription/?organization_id={organization.id}"
    )

    assert member_response.status_code == 200
    assert "stripe_customer_id" not in member_response.json()
    assert "stripe_subscription_id" not in member_response.json()
    assert owner_response.status_code == 200
    assert owner_response.json()["stripe_customer_id"] == "cus_private"
    assert owner_response.json()["stripe_subscription_id"] == "sub_private"


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


@override_settings(
    FRONTEND_BASE_URL="http://localhost:5173",
    BILLING_ALLOWED_REDIRECT_HOSTS=[],
)
def test_checkout_rejects_unapproved_redirect_hosts(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/billing/checkout/",
        {
            "organization_id": organization.id,
            "plan_slug": "starter",
            "success_url": "https://evil.example/success",
            "cancel_url": "http://localhost:5173/cancel",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "success_url" in response.json()


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


@override_settings(
    FRONTEND_BASE_URL="http://localhost:5173",
    BILLING_ALLOWED_REDIRECT_HOSTS=[],
)
def test_customer_portal_rejects_unapproved_return_url(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/billing/customer-portal/",
        {
            "organization_id": organization.id,
            "return_url": "https://evil.example/billing",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "return_url" in response.json()


@override_settings(STRIPE_SECRET_KEY="sk_test_placeholder")
def test_configured_checkout_service_calls_stripe_with_org_and_plan_metadata(
    django_user_model,
    monkeypatch,
):
    owner = make_user(django_user_model, email="stripe-checkout@example.com")
    organization = create_organization_for_owner(owner, "Stripe Checkout Workspace")
    plan = Plan.objects.get(slug="starter")
    plan.stripe_price_id = "price_starter_test"
    plan.save(update_fields=["stripe_price_id", "updated_at"])
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/session", id="cs_test_123")

    monkeypatch.setattr("stripe.checkout.Session.create", fake_create)

    result = create_checkout_session(
        organization,
        plan,
        "http://localhost:5173/dashboard/plan",
        "http://localhost:5173/dashboard/plan",
    )

    assert result == {
        "checkout_url": "https://checkout.stripe.test/session",
        "checkout_session_id": "cs_test_123",
    }
    assert calls[0]["line_items"] == [{"price": "price_starter_test", "quantity": 1}]
    assert calls[0]["metadata"] == {
        "organization_id": str(organization.id),
        "plan_slug": "starter",
    }
    assert calls[0]["subscription_data"]["metadata"] == calls[0]["metadata"]


@override_settings(STRIPE_SECRET_KEY="sk_test_placeholder")
def test_configured_customer_portal_service_calls_stripe_for_subscription(
    django_user_model,
    monkeypatch,
):
    owner = make_user(django_user_model, email="stripe-portal@example.com")
    organization = create_organization_for_owner(owner, "Stripe Portal Workspace")
    subscription = organization.subscription
    subscription.stripe_customer_id = "cus_test_123"
    subscription.save(update_fields=["stripe_customer_id", "updated_at"])
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(url="https://billing.stripe.test/session")

    monkeypatch.setattr("stripe.billing_portal.Session.create", fake_create)

    result = create_customer_portal_session(
        subscription,
        "http://localhost:5173/dashboard/plan",
    )

    assert result == {"portal_url": "https://billing.stripe.test/session"}
    assert calls == [
        {
            "customer": "cus_test_123",
            "return_url": "http://localhost:5173/dashboard/plan",
        }
    ]


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


def test_inactive_subscription_uses_free_plan_for_features_and_limits(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    organization.subscription.plan = Plan.objects.get(slug="pro")
    organization.subscription.status = SubscriptionStatus.PAST_DUE
    organization.subscription.save(update_fields=["plan", "status", "updated_at"])

    assert feature_enabled_for_organization(organization, "advanced_ai_models") is False
    assert_within_usage_limit(organization, "one_click_requests", quantity=3)
    with pytest.raises(UsageLimitExceeded):
        assert_within_usage_limit(organization, "one_click_requests", quantity=4)


def test_atomic_usage_check_records_or_blocks_in_one_operation(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")

    usage_record = check_and_record_usage(
        organization,
        "one_click_requests",
        quantity=3,
        source="test.atomic",
    )

    assert usage_record.quantity == 3
    with pytest.raises(UsageLimitExceeded):
        check_and_record_usage(
            organization,
            "one_click_requests",
            quantity=1,
            source="test.atomic",
        )
    assert UsageRecord.objects.filter(organization=organization).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_usage_reservations_cannot_exceed_limit_on_postgresql(django_user_model):
    if connection.vendor != "postgresql":
        pytest.skip("SELECT FOR UPDATE concurrency semantics require PostgreSQL.")

    owner = make_user(django_user_model, email="concurrent-usage@example.com")
    organization = create_organization_for_owner(owner, "Concurrent Usage Workspace")

    def reserve_full_limit():
        close_old_connections()
        try:
            check_and_record_usage(
                organization,
                "one_click_requests",
                quantity=3,
                source="test.concurrent",
            )
            return "recorded"
        except UsageLimitExceeded:
            return "blocked"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _index: reserve_full_limit(), range(2)))

    assert sorted(outcomes) == ["blocked", "recorded"]
    assert UsageRecord.objects.filter(
        organization=organization,
        metric_name="one_click_requests",
    ).count() == 1


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
    assert StripeWebhookEvent.objects.get(event_id="evt_checkout_completed").status == (
        StripeWebhookEventStatus.PROCESSED
    )


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_stripe_webhook_duplicate_event_is_idempotent(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    payload = json.dumps(
        {
            "id": "evt_duplicate_checkout",
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

    first_response = client.post(
        "/api/v1/billing/webhooks/stripe/",
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=stripe_signature_header(payload, "whsec_test"),
    )
    second_response = client.post(
        "/api/v1/billing/webhooks/stripe/",
        data=payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=stripe_signature_header(payload, "whsec_test"),
    )

    assert first_response.status_code == 200
    assert first_response.json()["duplicate"] is False
    assert second_response.status_code == 200
    assert second_response.json()["duplicate"] is True
    assert StripeWebhookEvent.objects.filter(event_id="evt_duplicate_checkout").count() == 1


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
def test_stripe_webhook_invalid_metadata_is_skipped_without_500():
    payload = json.dumps(
        {
            "id": "evt_invalid_metadata",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "object": "checkout.session",
                    "metadata": {
                        "organization_id": "999999",
                        "plan_slug": "missing-plan",
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
    assert response.json()["processed"] is False
    assert StripeWebhookEvent.objects.get(event_id="evt_invalid_metadata").status == (
        StripeWebhookEventStatus.SKIPPED
    )


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
@pytest.mark.parametrize(
    ("event_type", "stripe_status", "cancel_at_period_end"),
    [
        ("customer.subscription.updated", "active", True),
        ("customer.subscription.deleted", "canceled", False),
    ],
)
def test_signed_subscription_webhooks_sync_subscription_lifecycle(
    django_user_model,
    event_type,
    stripe_status,
    cancel_at_period_end,
):
    owner = make_user(django_user_model, email=f"{stripe_status}@example.com")
    organization = create_organization_for_owner(owner, f"{stripe_status} Workspace")
    subscription = organization.subscription
    subscription.stripe_subscription_id = "sub_lifecycle_123"
    subscription.save(update_fields=["stripe_subscription_id", "updated_at"])
    payload = json.dumps(
        {
            "id": f"evt_{stripe_status}",
            "object": "event",
            "type": event_type,
            "data": {
                "object": {
                    "id": "sub_lifecycle_123",
                    "object": "subscription",
                    "customer": "cus_lifecycle_123",
                    "status": stripe_status,
                    "cancel_at_period_end": cancel_at_period_end,
                    "current_period_start": 1_700_000_000,
                    "current_period_end": 1_702_592_000,
                    "metadata": {
                        "organization_id": str(organization.id),
                        "plan_slug": "pro",
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
    assert response.json()["processed"] is True
    subscription.refresh_from_db()
    assert subscription.plan.slug == "pro"
    assert subscription.status == stripe_status
    assert subscription.stripe_customer_id == "cus_lifecycle_123"
    assert subscription.cancel_at_period_end is cancel_at_period_end
    assert subscription.current_period_start is not None
    assert subscription.current_period_end is not None
