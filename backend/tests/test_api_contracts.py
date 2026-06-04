import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.organizations.services import create_organization_for_owner

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def assert_keys(payload, expected_keys):
    missing_keys = set(expected_keys) - set(payload)
    assert not missing_keys, f"Missing keys: {sorted(missing_keys)}"


def test_frontend_contract_auth_and_organization_endpoints(django_user_model):
    password = "SaaSCore!23456"
    user = make_user(django_user_model, email="owner@example.com", password=password)
    create_organization_for_owner(user, "Owner Workspace")
    client = APIClient()

    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": password},
        format="json",
    )
    assert login_response.status_code == 200
    login_body = login_response.json()
    assert_keys(login_body, {"access", "user"})
    assert "refresh" not in login_body
    assert login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
    assert_keys(login_body["user"], {"id", "email", "name", "account_status"})

    client.force_authenticate(user)
    organizations_response = client.get("/api/v1/organizations/")
    assert organizations_response.status_code == 200
    organization = organizations_response.json()["results"][0]
    assert_keys(
        organization,
        {"id", "name", "owner", "timezone", "default_language", "my_role"},
    )


def test_frontend_contract_workspace_summary_endpoints(django_user_model):
    user = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(user, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(user)

    plans_response = client.get("/api/v1/billing/plans/")
    subscription_response = client.get(
        f"/api/v1/billing/subscription/?organization_id={organization.id}"
    )
    usage_response = client.get(f"/api/v1/usage/summary/?organization_id={organization.id}")

    assert plans_response.status_code == 200
    assert_keys(plans_response.json()[0], {"id", "name", "slug", "features", "limits"})
    assert subscription_response.status_code == 200
    assert_keys(subscription_response.json(), {"id", "organization", "plan", "status"})
    assert usage_response.status_code == 200
    assert_keys(usage_response.json(), {"plan", "period", "metrics"})


def test_frontend_contract_ai_execution_plan_and_logs(django_user_model):
    user = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(user, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(user)

    task_profiles_response = client.get("/api/v1/ai/task-profiles/")
    execution_plan_response = client.post(
        "/api/v1/ai/execution-plan/",
        {
            "organization_id": organization.id,
            "task_key": "table_analysis",
            "input_payload": {"rows": 10},
            "constraints": {"can_use_classic_ml": True},
        },
        format="json",
    )
    decision_logs_response = client.get(
        f"/api/v1/ai/decision-logs/?organization_id={organization.id}"
    )

    assert task_profiles_response.status_code == 200
    assert_keys(
        task_profiles_response.json()["results"][0],
        {"id", "key", "name", "default_strategy", "allowed_strategies"},
    )
    assert execution_plan_response.status_code == 200
    assert_keys(
        execution_plan_response.json(),
        {
            "task_key",
            "strategy",
            "provider_slug",
            "model",
            "fallback",
            "reason",
            "configuration",
        },
    )
    assert decision_logs_response.status_code == 200
    assert_keys(
        decision_logs_response.json()["results"][0],
        {"id", "organization", "task_key", "selected_strategy", "decision_reason"},
    )


def test_frontend_contract_create_workflow_endpoints(django_user_model):
    user = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(user, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(user)

    report_response = client.post(
        "/api/v1/reports/",
        {
            "organization_id": organization.id,
            "title": "Contract Report",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": {"metrics": {"revenue": 1000}},
        },
        format="json",
    )
    preference_response = client.post(
        "/api/v1/notifications/preferences/",
        {
            "organization_id": organization.id,
            "event": "report_ready",
            "channel": "email",
            "is_enabled": True,
        },
        format="json",
    )
    product_response = client.post(
        "/api/v1/products/example-insights/requests/",
        {
            "organization_id": organization.id,
            "title": "Contract Insight",
            "input_payload": {"rows": [{"month": "January", "revenue": 1000}]},
            "constraints": {"can_use_classic_ml": True},
        },
        format="json",
    )

    assert report_response.status_code == 201
    assert_keys(report_response.json(), {"id", "title", "status", "requested_format", "job_run_id"})
    assert preference_response.status_code == 200
    assert_keys(preference_response.json(), {"id", "event", "channel", "is_enabled"})
    assert product_response.status_code == 201
    assert_keys(
        product_response.json(),
        {"id", "report", "job_run", "title", "status", "strategy"},
    )
