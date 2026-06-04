import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner
from apps.privacy.models import DataDeletionRequest, DataExportRequest
from apps.products.example_insights.models import ExampleInsightRequest
from apps.reports.models import Report

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def test_data_export_request_creates_payload_and_audit_log(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/privacy/exports/",
        {"organization_id": organization.id, "scope": "organization"},
        format="json",
        HTTP_X_REQUEST_ID="privacy-export-1",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["export_payload"]["organization"]["name"] == "Owner Workspace"
    assert body["export_payload"]["retention"]["data_retention_days"]
    assert body["export_payload"]["membership_records"][0]["user"]["email"] == owner.email
    assert DataExportRequest.objects.filter(organization=organization).count() == 1
    audit_log = AuditLog.objects.get(action="privacy.export.requested")
    assert audit_log.organization == organization
    assert audit_log.request_id == "privacy-export-1"


def test_data_export_payload_includes_real_report_records(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Exported Report",
        input_payload={"private": "input"},
        result_summary={"private": "result"},
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/privacy/exports/",
        {"organization_id": organization.id, "scope": "organization"},
        format="json",
    )

    assert response.status_code == 201
    report_record = response.json()["export_payload"]["report_records"][0]
    assert report_record["title"] == "Exported Report"
    assert report_record["input_payload"] == {"private": "input"}
    assert report_record["result_summary"] == {"private": "result"}


def test_data_export_payload_includes_product_module_records(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    ExampleInsightRequest.objects.create(
        organization=organization,
        created_by=owner,
        title="Exported Insight",
        input_payload={"private": "input"},
        constraints={"private": "constraints"},
        ai_execution_plan={"private": "plan"},
        error_message="provider error",
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/privacy/exports/",
        {"organization_id": organization.id, "scope": "organization"},
        format="json",
    )

    assert response.status_code == 201
    product_record = response.json()["export_payload"]["product_records"][
        "example_insight_requests"
    ][0]
    assert product_record["title"] == "Exported Insight"
    assert product_record["input_payload"] == {"private": "input"}
    assert product_record["constraints"] == {"private": "constraints"}
    assert product_record["ai_execution_plan"] == {"private": "plan"}
    assert product_record["error_message"] == "provider error"


def test_data_deletion_request_can_be_executed_and_anonymizes_organization(
    django_user_model,
):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Sensitive Report",
        input_payload={"private": "input"},
        result_summary={"private": "result"},
    )
    ExampleInsightRequest.objects.create(
        organization=organization,
        created_by=owner,
        title="Sensitive Insight",
        input_payload={"private": "input"},
        constraints={"private": "constraints"},
        ai_execution_plan={"private": "plan"},
        error_message="provider error",
    )

    create_response = client.post(
        "/api/v1/privacy/deletion-requests/",
        {
            "organization_id": organization.id,
            "target": "organization",
            "reason": "Customer requested deletion.",
        },
        format="json",
    )
    deletion_request_id = create_response.json()["id"]
    execute_response = client.post(
        f"/api/v1/privacy/deletion-requests/{deletion_request_id}/execute/",
        format="json",
    )

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "pending"
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == "completed"
    assert organization.__class__.objects.filter(id=organization.id).exists()
    organization.refresh_from_db()
    assert organization.name == f"Deleted organization {organization.id}"
    assert organization.memberships.get(user=owner).status == MembershipStatus.DISABLED
    report = Report.objects.get(organization=organization)
    assert report.input_payload == {}
    assert report.result_summary == {}
    insight_request = ExampleInsightRequest.objects.get(organization=organization)
    assert insight_request.title == "Deleted insight request"
    assert insight_request.input_payload == {}
    assert insight_request.constraints == {}
    assert insight_request.ai_execution_plan == {}
    assert insight_request.error_message == ""
    assert AuditLog.objects.filter(action="privacy.deletion.requested").exists()
    assert AuditLog.objects.filter(action="privacy.deletion.executed").exists()


def test_privacy_requests_are_organization_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    other_organization = create_organization_for_owner(other, "Other Workspace")
    DataExportRequest.objects.create(
        organization=organization,
        requested_by=owner,
        export_payload={"organization": {"name": "Owner Workspace"}},
    )
    DataExportRequest.objects.create(
        organization=other_organization,
        requested_by=other,
        export_payload={"organization": {"name": "Other Workspace"}},
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(f"/api/v1/privacy/exports/?organization_id={organization.id}")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["organization"] == organization.id


def test_deletion_request_requires_owner_role(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    admin = make_user(django_user_model, email="admin@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=admin,
        role=MembershipRole.ADMIN,
    )
    client = APIClient()
    client.force_authenticate(admin)

    response = client.post(
        "/api/v1/privacy/deletion-requests/",
        {"organization_id": organization.id, "target": "organization"},
        format="json",
    )

    assert response.status_code == 403
    assert DataDeletionRequest.objects.count() == 0
