import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.models import UserAccountStatus
from apps.audit.models import AuditLog
from apps.organizations.models import Membership, MembershipRole, MembershipStatus, Organization
from apps.organizations.services import create_organization_for_owner
from apps.privacy.models import DataDeletionRequest, PrivacyRequestStatus

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def test_register_creates_user_default_organization_owner_membership(django_user_model):
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "founder@example.com",
            "password": "SaaSCore!23456",
            "name": "Founder",
            "organization_name": "Founder Labs",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "founder@example.com"
    assert body["organization"]["name"] == "Founder Labs"
    assert body["organization"]["my_role"] == MembershipRole.OWNER
    assert body["tokens"]["access"]
    assert "refresh" not in body["tokens"]
    refresh_cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    assert refresh_cookie.value
    assert refresh_cookie["httponly"]

    user = django_user_model.objects.get(email="founder@example.com")
    organization = Organization.objects.get(name="Founder Labs")
    assert Membership.objects.get(user=user, organization=organization).role == MembershipRole.OWNER


def test_login_returns_tokens_and_user(django_user_model):
    make_user(django_user_model, email="member@example.com", password="SaaSCore!23456")
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "member@example.com", "password": "SaaSCore!23456"},
        format="json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access"]
    assert "refresh" not in body
    assert body["user"]["email"] == "member@example.com"
    refresh_cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    assert refresh_cookie.value
    assert refresh_cookie["httponly"]


def test_suspended_user_cannot_login(django_user_model):
    make_user(
        django_user_model,
        email="suspended@example.com",
        password="SaaSCore!23456",
        account_status=UserAccountStatus.SUSPENDED,
    )
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {"email": "suspended@example.com", "password": "SaaSCore!23456"},
        format="json",
    )

    assert response.status_code == 401


def test_suspended_user_cannot_refresh_existing_token(django_user_model):
    user = make_user(django_user_model, email="refresh@example.com", password="SaaSCore!23456")
    client = APIClient()
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "SaaSCore!23456"},
        format="json",
    )
    refresh_token = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
    user.account_status = UserAccountStatus.SUSPENDED
    user.save(update_fields=["account_status"])

    refresh_response = client.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )

    assert refresh_response.status_code == 401


def test_suspended_user_cannot_use_existing_access_token(django_user_model):
    user = make_user(django_user_model, email="access@example.com", password="SaaSCore!23456")
    create_organization_for_owner(user, "Access Workspace")
    client = APIClient()
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "SaaSCore!23456"},
        format="json",
    )
    access_token = login_response.json()["access"]
    user.account_status = UserAccountStatus.SUSPENDED
    user.save(update_fields=["account_status"])

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    response = client.get("/api/v1/auth/me/")

    assert response.status_code == 401


def test_logout_blacklists_refresh_token(django_user_model):
    user = make_user(django_user_model, email="logout@example.com", password="SaaSCore!23456")
    client = APIClient()
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "SaaSCore!23456"},
        format="json",
    )
    tokens = login_response.json()
    refresh_token = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
    client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = refresh_token

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    logout_response = client.post("/api/v1/auth/logout/", {}, format="json")

    assert logout_response.status_code == 204
    assert logout_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value == ""

    refresh_response = client.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )
    assert refresh_response.status_code == 401


def test_refresh_endpoint_accepts_httponly_cookie_and_rotates_cookie(django_user_model):
    user = make_user(
        django_user_model,
        email="cookie-refresh@example.com",
        password="SaaSCore!23456",
    )
    client = APIClient()
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "SaaSCore!23456"},
        format="json",
    )
    client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = login_response.cookies[
        settings.AUTH_REFRESH_COOKIE_NAME
    ].value

    response = client.post("/api/v1/auth/refresh/", {}, format="json")

    assert response.status_code == 200
    assert response.json()["access"]
    assert "refresh" not in response.json()
    refresh_cookie = response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]
    assert refresh_cookie.value
    assert refresh_cookie["httponly"]


def test_authenticated_user_can_list_their_organizations(django_user_model):
    user = make_user(django_user_model, email="owner@example.com")
    create_organization_for_owner(user, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/organizations/")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["name"] == "Owner Workspace"
    assert body["results"][0]["my_role"] == MembershipRole.OWNER


def test_user_cannot_access_another_organization(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    hidden_organization = create_organization_for_owner(owner, "Hidden Workspace")
    client = APIClient()
    client.force_authenticate(user=other)

    response = client.get(f"/api/v1/organizations/{hidden_organization.id}/")

    assert response.status_code == 404


def test_member_cannot_update_organization_settings(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Team Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(user=member)

    response = client.patch(
        f"/api/v1/organizations/{organization.id}/",
        {"name": "Renamed Workspace"},
        format="json",
    )

    assert response.status_code == 403
    organization.refresh_from_db()
    assert organization.name == "Team Workspace"


def test_admin_can_update_organization_settings(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    admin = make_user(django_user_model, email="admin@example.com")
    organization = create_organization_for_owner(owner, "Team Workspace")
    Membership.objects.create(
        organization=organization,
        user=admin,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.patch(
        f"/api/v1/organizations/{organization.id}/",
        {"name": "Renamed Workspace"},
        format="json",
    )

    assert response.status_code == 200
    organization.refresh_from_db()
    assert organization.name == "Renamed Workspace"


def test_owner_delete_anonymizes_organization_without_hard_delete(django_user_model):
    owner = make_user(django_user_model, email="owner-delete@example.com")
    organization = create_organization_for_owner(owner, "Delete Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.delete(f"/api/v1/organizations/{organization.id}/")

    assert response.status_code == 204
    assert Organization.objects.filter(id=organization.id).exists()
    organization.refresh_from_db()
    assert organization.name == f"Deleted organization {organization.id}"
    assert organization.memberships.get(user=owner).status == MembershipStatus.DISABLED
    deletion_request = DataDeletionRequest.objects.get(organization=organization)
    assert deletion_request.status == PrivacyRequestStatus.COMPLETED
    assert deletion_request.metadata["source"] == "organization_destroy"
    audit_log = AuditLog.objects.get(action="organizations.deleted")
    assert audit_log.organization == organization
    assert audit_log.target_entity_id == str(organization.id)
    assert audit_log.metadata["deletion_request_id"] == deletion_request.id


def test_invite_member_creates_pending_invitation_without_sending_email(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Team Workspace")
    client = APIClient()
    client.force_authenticate(user=owner)

    response = client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": "new.member@example.com", "role": MembershipRole.MEMBER},
        format="json",
    )

    assert response.status_code == 201
    invitation = Membership.objects.get(
        organization=organization,
        invited_email="new.member@example.com",
    )
    assert invitation.user is None
    assert invitation.status == MembershipStatus.INVITED
