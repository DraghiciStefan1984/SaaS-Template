import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.organizations.models import Membership, MembershipRole
from apps.organizations.services import create_organization_for_owner
from apps.privacy.models import DataDeletionRequest, DataExportRequest

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
    assert DataExportRequest.objects.filter(organization=organization).count() == 1
    audit_log = AuditLog.objects.get(action="privacy.export.requested")
    assert audit_log.organization == organization
    assert audit_log.request_id == "privacy-export-1"


def test_data_deletion_request_is_pending_and_does_not_delete_organization(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/privacy/deletion-requests/",
        {
            "organization_id": organization.id,
            "target": "organization",
            "reason": "Customer requested deletion.",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert DataDeletionRequest.objects.filter(organization=organization).count() == 1
    assert organization.__class__.objects.filter(id=organization.id).exists()
    assert AuditLog.objects.filter(action="privacy.deletion.requested").exists()


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
