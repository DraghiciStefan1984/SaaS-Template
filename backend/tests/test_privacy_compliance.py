import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner
from apps.privacy.models import DataDeletionRequest, DataExportRequest, PrivacyRequestStatus
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
    export_request = DataExportRequest.objects.get(organization=organization)
    assert export_request.expires_at is not None
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


def test_account_export_scope_returns_account_payload_for_member(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    other_organization = create_organization_for_owner(member, "Member Workspace")
    client = APIClient()
    client.force_authenticate(member)

    response = client.post(
        "/api/v1/privacy/exports/",
        {"organization_id": organization.id, "scope": "account"},
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()["export_payload"]
    assert payload["account"]["email"] == "member@example.com"
    exported_org_ids = {
        membership["organization"]["id"] for membership in payload["membership_records"]
    }
    assert exported_org_ids == {organization.id, other_organization.id}


def test_account_exports_are_visible_only_to_requester_not_org_admins(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    account_export = DataExportRequest.objects.create(
        organization=organization,
        requested_by=member,
        scope="account",
        export_payload={"account": {"email": "member@example.com"}},
    )
    organization_export = DataExportRequest.objects.create(
        organization=organization,
        requested_by=owner,
        scope="organization",
        export_payload={"organization": {"name": "Owner Workspace"}},
    )
    client = APIClient()

    client.force_authenticate(owner)
    owner_response = client.get(
        f"/api/v1/privacy/exports/?organization_id={organization.id}"
    )
    client.force_authenticate(member)
    member_response = client.get(
        f"/api/v1/privacy/exports/?organization_id={organization.id}"
    )

    assert owner_response.status_code == 200
    assert [item["id"] for item in owner_response.json()["results"]] == [
        organization_export.id
    ]
    assert owner_response.json()["results"][0]["scope"] == "organization"
    assert member_response.status_code == 200
    assert [item["id"] for item in member_response.json()["results"]] == [
        account_export.id
    ]
    assert member_response.json()["results"][0]["export_payload"]["account"]["email"] == (
        "member@example.com"
    )


def test_data_deletion_request_can_be_executed_and_anonymizes_organization(
    django_user_model,
):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)
    export_request = DataExportRequest.objects.create(
        organization=organization,
        requested_by=owner,
        export_payload={"private": "export-copy"},
    )

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
    export_request.refresh_from_db()
    assert export_request.export_payload == {"privacy_deleted": True}
    assert export_request.expires_at is not None
    assert AuditLog.objects.filter(action="privacy.deletion.requested").exists()
    assert AuditLog.objects.filter(action="privacy.deletion.executed").exists()


def test_account_deletion_can_be_requested_by_member_and_disables_all_memberships(
    django_user_model,
):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    other_organization = create_organization_for_owner(member, "Member Workspace")
    DataExportRequest.objects.create(
        organization=organization,
        requested_by=member,
        scope="account",
        export_payload={"private": "account-export"},
    )
    client = APIClient()
    client.force_authenticate(member)

    create_response = client.post(
        "/api/v1/privacy/deletion-requests/",
        {
            "organization_id": organization.id,
            "target": "account",
            "reason": "Delete my account.",
        },
        format="json",
    )
    deletion_request_id = create_response.json()["id"]
    execute_response = client.post(
        f"/api/v1/privacy/deletion-requests/{deletion_request_id}/execute/",
        format="json",
    )

    assert create_response.status_code == 201
    assert execute_response.status_code == 200
    assert execute_response.json()["status"] == PrivacyRequestStatus.COMPLETED
    member.refresh_from_db()
    assert member.account_status == "suspended"
    assert member.is_active is False
    assert not member.organization_memberships.filter(status=MembershipStatus.ACTIVE).exists()
    assert (
        organization.memberships.get(user=member).status
        == other_organization.memberships.get(user=member).status
        == MembershipStatus.DISABLED
    )
    assert DataExportRequest.objects.get(requested_by=member).export_payload == {
        "privacy_deleted": True
    }


def test_owner_cannot_execute_member_account_deletion_request(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    other_organization = create_organization_for_owner(member, "Member Workspace")
    deletion_request = DataDeletionRequest.objects.create(
        organization=organization,
        requested_by=member,
        target="account",
        reason="Delete my account.",
        status=PrivacyRequestStatus.PENDING,
    )
    client = APIClient()
    client.force_authenticate(owner)

    list_response = client.get(
        f"/api/v1/privacy/deletion-requests/?organization_id={organization.id}"
    )
    execute_response = client.post(
        f"/api/v1/privacy/deletion-requests/{deletion_request.id}/execute/",
        format="json",
    )

    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0
    assert execute_response.status_code == 403
    deletion_request.refresh_from_db()
    member.refresh_from_db()
    assert deletion_request.status == PrivacyRequestStatus.PENDING
    assert member.is_active is True
    assert member.account_status == "active"
    assert organization.memberships.get(user=member).status == MembershipStatus.ACTIVE
    assert other_organization.memberships.get(user=member).status == MembershipStatus.ACTIVE


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
