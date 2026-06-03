import pytest
from rest_framework.test import APIClient

from apps.accounts.models import UserAccountStatus
from apps.organizations.models import Membership, MembershipRole, MembershipStatus, Organization
from apps.organizations.services import create_organization_for_owner

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
    assert body["tokens"]["refresh"]

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
    assert body["refresh"]
    assert body["user"]["email"] == "member@example.com"


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


def test_logout_blacklists_refresh_token(django_user_model):
    user = make_user(django_user_model, email="logout@example.com", password="SaaSCore!23456")
    client = APIClient()
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "SaaSCore!23456"},
        format="json",
    )
    tokens = login_response.json()

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    logout_response = client.post(
        "/api/v1/auth/logout/",
        {"refresh": tokens["refresh"]},
        format="json",
    )

    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/api/v1/auth/refresh/",
        {"refresh": tokens["refresh"]},
        format="json",
    )
    assert refresh_response.status_code == 401


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
