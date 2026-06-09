import pytest
from django.conf import settings
from django.core.checks import run_checks
from django.test import override_settings
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.views import LoginView, RegisterView
from apps.audit.models import AuditLog
from apps.audit.services import get_request_ip_address
from apps.billing.views import CheckoutView
from apps.common.checks import production_security_settings_check
from apps.integrations.views import ReconnectIntegrationView
from apps.jobs.views import ScheduledWorkflowRunView
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner
from apps.products.example_insights.views import ExampleInsightRequestListCreateView
from apps.reports.views import ReportArtifactDownloadView

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def test_report_creation_writes_audit_log(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/reports/",
        {
            "organization_id": organization.id,
            "title": "Audited Report",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": {"metrics": {"revenue": 1000}},
        },
        format="json",
        HTTP_USER_AGENT="pytest",
        HTTP_X_REQUEST_ID="req-audit-1",
    )

    assert response.status_code == 201
    audit_log = AuditLog.objects.get(action="reports.request.created")
    assert audit_log.organization == organization
    assert audit_log.user == owner
    assert audit_log.target_entity_type == "report"
    assert audit_log.target_entity_id == str(response.json()["id"])
    assert audit_log.request_id == "req-audit-1"
    assert audit_log.user_agent == "pytest"


def test_audit_logs_are_organization_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    other_organization = create_organization_for_owner(other, "Other Workspace")
    AuditLog.objects.create(
        organization=organization,
        user=owner,
        action="test.owner",
        category="test",
    )
    AuditLog.objects.create(
        organization=other_organization,
        user=other,
        action="test.other",
        category="test",
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/v1/audit/logs/?organization_id={organization.id}")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["action"] == "test.owner"


def test_audit_logs_require_admin_role(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    AuditLog.objects.create(
        organization=organization,
        user=owner,
        action="test.owner",
        category="test",
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.get(f"/api/v1/audit/logs/?organization_id={organization.id}")

    assert response.status_code == 403


def test_audit_ip_ignores_x_forwarded_for_by_default():
    request = APIRequestFactory().get(
        "/",
        HTTP_X_FORWARDED_FOR="203.0.113.10",
        REMOTE_ADDR="10.0.0.5",
    )

    assert get_request_ip_address(request) == "10.0.0.5"


def test_audit_ip_uses_x_forwarded_for_only_when_trusted():
    request = APIRequestFactory().get(
        "/",
        HTTP_X_FORWARDED_FOR="203.0.113.10, 10.0.0.5",
        REMOTE_ADDR="10.0.0.5",
    )

    with override_settings(AUDIT_TRUST_X_FORWARDED_FOR=True):
        assert get_request_ip_address(request) == "203.0.113.10"


def test_security_throttle_scopes_are_configured():
    throttle_classes = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]
    throttle_rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]

    assert "rest_framework.throttling.ScopedRateThrottle" in throttle_classes
    assert throttle_rates["auth"]
    assert throttle_rates["billing_action"]
    assert throttle_rates["product_write"]
    assert RegisterView.throttle_scope == "auth"
    assert LoginView.throttle_scope == "auth"
    assert CheckoutView.throttle_scope == "billing_action"
    assert ExampleInsightRequestListCreateView.throttle_scope == "product_write"
    assert ReconnectIntegrationView.throttle_scope == "product_write"
    assert ScheduledWorkflowRunView.throttle_scope == "expensive_action"
    assert ReportArtifactDownloadView.throttle_scope == "expensive_action"


def test_production_security_check_flags_unsafe_secret():
    with override_settings(
        DEBUG=False,
        SECRET_KEY="unsafe-local-development-key-change-me-before-production",
    ):
        issues = production_security_settings_check(None)

    assert any(issue.id == "saas.E001" for issue in issues)


def test_django_check_registry_loads_saas_security_checks():
    with override_settings(DEBUG=True):
        issues = run_checks()

    assert not any(issue.id == "saas.E001" for issue in issues)
