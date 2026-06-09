from io import StringIO

import pytest
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import UserAccountStatus
from apps.ai.models import AIModelDecisionLog
from apps.billing.services import feature_enabled_for_organization
from apps.jobs.models import JobRun
from apps.notifications.models import (
    NotificationDeliveryLog,
    NotificationDeliveryStatus,
    NotificationPreference,
)
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner
from apps.products.example_insights.models import ExampleInsightRequest
from apps.reports.models import Report
from apps.usage.models import UsageRecord

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def test_example_insight_endpoint_creates_full_template_workflow(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/products/example-insights/requests/",
        {
            "organization_id": organization.id,
            "title": "Revenue Trend",
            "input_payload": {
                "rows": [
                    {"month": "January", "revenue": 1000},
                    {"month": "February", "revenue": 1250},
                ]
            },
            "constraints": {"can_use_classic_ml": True},
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "planned"
    assert body["strategy"] == "classic_ml"
    assert body["report"] == Report.objects.get().id
    assert body["job_run"] == JobRun.objects.get().id
    assert AIModelDecisionLog.objects.filter(
        organization=organization,
        task_key="table_analysis",
        selected_strategy="classic_ml",
    ).exists()
    assert UsageRecord.objects.filter(
        organization=organization,
        metric_name="one_click_requests",
        product_scope="example_insights",
    ).exists()
    assert feature_enabled_for_organization(organization, "example_insights") is True


def test_example_insight_endpoint_ignores_client_forced_ai_strategy(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/products/example-insights/requests/",
        {
            "organization_id": organization.id,
            "title": "Revenue Trend",
            "input_payload": {"rows": [{"month": "January", "revenue": 1000}]},
            "constraints": {
                "force_strategy": "advanced_llm",
                "requires_advanced_reasoning": True,
            },
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["strategy"] == "classic_ml"
    decision_log = AIModelDecisionLog.objects.filter(
        organization=organization,
        selected_strategy="classic_ml",
    ).first()
    assert decision_log is not None
    assert "force_strategy" not in decision_log.constraints


def test_example_insight_endpoint_rejects_non_object_payload_fields(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    input_response = client.post(
        "/api/v1/products/example-insights/requests/",
        {
            "organization_id": organization.id,
            "title": "Revenue Trend",
            "input_payload": ["not", "an", "object"],
            "constraints": {"can_use_classic_ml": True},
        },
        format="json",
    )
    constraints_response = client.post(
        "/api/v1/products/example-insights/requests/",
        {
            "organization_id": organization.id,
            "title": "Revenue Trend",
            "input_payload": {"rows": []},
            "constraints": ["can_use_classic_ml"],
        },
        format="json",
    )

    assert input_response.status_code == 400
    assert constraints_response.status_code == 400
    assert "input_payload" in input_response.json()
    assert "constraints" in constraints_response.json()
    assert ExampleInsightRequest.objects.count() == 0
    assert Report.objects.count() == 0
    assert UsageRecord.objects.count() == 0


def test_example_insight_endpoint_respects_plan_feature_flag(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    organization.subscription.plan.features = {
        **organization.subscription.plan.features,
        "example_insights": False,
    }
    organization.subscription.plan.save(update_fields=["features", "updated_at"])
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/products/example-insights/requests/",
        {
            "organization_id": organization.id,
            "title": "Revenue Trend",
            "input_payload": {"rows": []},
        },
        format="json",
    )

    assert response.status_code == 403
    assert "example_insights" in response.json()["detail"]
    assert ExampleInsightRequest.objects.count() == 0


def test_example_insight_requests_are_organization_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    other_organization = create_organization_for_owner(other, "Other Workspace")
    ExampleInsightRequest.objects.create(
        organization=organization,
        created_by=owner,
        title="Owner Insight",
        ai_execution_plan={"strategy": "classic_ml"},
    )
    ExampleInsightRequest.objects.create(
        organization=other_organization,
        created_by=other,
        title="Other Insight",
        ai_execution_plan={"strategy": "classic_ml"},
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(
        f"/api/v1/products/example-insights/requests/?organization_id={organization.id}"
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["title"] == "Owner Insight"


def test_example_insight_request_list_uses_safe_summary_for_members(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    ExampleInsightRequest.objects.create(
        organization=organization,
        created_by=owner,
        title="Sensitive Insight",
        input_payload={"private": "input"},
        constraints={"private": "constraints"},
        ai_execution_plan={"strategy": "classic_ml", "private": "plan"},
        error_message="provider details",
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.get(
        f"/api/v1/products/example-insights/requests/?organization_id={organization.id}"
    )

    assert response.status_code == 200
    body = response.json()["results"][0]
    assert body["strategy"] == "classic_ml"
    assert "input_payload" not in body
    assert "constraints" not in body
    assert "ai_execution_plan" not in body
    assert "error_message" not in body


def test_seed_dev_data_is_idempotent(django_user_model):
    call_command("seed_dev_data")
    call_command("seed_dev_data")

    assert django_user_model.objects.filter(email="demo@example.com").count() == 1
    assert ExampleInsightRequest.objects.filter(title="Demo Table Insight").count() == 1
    insight_request = ExampleInsightRequest.objects.get(title="Demo Table Insight")
    assert insight_request.organization.name == "Demo Workspace"
    assert insight_request.ai_execution_plan["strategy"] == "classic_ml"


def test_seed_dev_data_resets_existing_demo_user_for_local_login(django_user_model):
    user = django_user_model.objects.create_user(
        email="demo@example.com",
        password="OldPassword!23456",
        account_status=UserAccountStatus.SUSPENDED,
        is_email_verified=False,
    )

    call_command("seed_dev_data")

    user.refresh_from_db()
    assert user.account_status == UserAccountStatus.ACTIVE
    assert user.is_email_verified is True
    assert user.organization_memberships.filter(
        organization__name="Demo Workspace",
    ).exists()
    assert authenticate(email="demo@example.com", password="SaaSCore!23456") == user


def test_seed_dev_data_creates_notification_demo_state():
    call_command("seed_dev_data")

    preference = NotificationPreference.objects.get(
        organization__name="Demo Workspace",
        event="report_ready",
        channel="email",
    )
    assert preference.is_enabled is True
    delivery_log = NotificationDeliveryLog.objects.get(
        organization=preference.organization,
        subject="Demo notification: report ready",
    )
    assert delivery_log.status == NotificationDeliveryStatus.SENT


def test_check_demo_ready_with_seed_validates_local_api_flow():
    cache.clear()
    stdout = StringIO()

    call_command("check_demo_ready", seed=True, stdout=stdout)

    output = stdout.getvalue()
    assert "Demo ready. Checked:" in output
    assert "- demo login" in output
    assert "- example product request" in output
