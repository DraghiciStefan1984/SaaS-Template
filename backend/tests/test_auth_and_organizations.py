from urllib.parse import parse_qs, urlparse

import pytest
from django.conf import settings
from django.core import mail, signing
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from apps.accounts.models import UserAccountStatus
from apps.accounts.services import (
    InvalidGoogleIdentity,
    get_or_create_google_user,
    verify_google_identity_token,
)
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
    assert len(mail.outbox) == 1
    assert "/verify-email?token=" in mail.outbox[0].body


def test_email_verification_link_marks_registered_user_verified(django_user_model):
    client = APIClient()
    register_response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "verify@example.com",
            "password": "SaaSCore!23456",
            "organization_name": "Verify Workspace",
        },
        format="json",
    )
    verification_url = mail.outbox[0].body.splitlines()[-1]
    token = parse_qs(urlparse(verification_url).query)["token"][0]

    response = client.post("/api/v1/auth/email/verify/", {"token": token}, format="json")

    assert register_response.status_code == 201
    assert response.status_code == 200
    user = django_user_model.objects.get(email="verify@example.com")
    assert user.is_email_verified is True
    assert AuditLog.objects.filter(action="auth.email_verified", user=user).exists()


def test_email_verification_rejects_invalid_token():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/email/verify/",
        {"token": "invalid"},
        format="json",
    )

    assert response.status_code == 400


def test_authenticated_user_can_resend_email_verification(django_user_model):
    user = make_user(django_user_model, email="resend-verification@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post("/api/v1/auth/email/verification/resend/", {}, format="json")

    assert response.status_code == 202
    assert len(mail.outbox) == 1
    assert "/verify-email?token=" in mail.outbox[0].body


def test_verified_user_resend_does_not_send_duplicate_email(django_user_model):
    user = make_user(
        django_user_model,
        email="already-verified@example.com",
        is_email_verified=True,
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post("/api/v1/auth/email/verification/resend/", {}, format="json")

    assert response.status_code == 202
    assert len(mail.outbox) == 0


def test_google_login_status_is_disabled_without_client_id():
    client = APIClient()

    response = client.get("/api/v1/auth/social/google/status/")

    assert response.status_code == 200
    assert response.json() == {"enabled": False, "client_id": "", "nonce": ""}


@override_settings(GOOGLE_OAUTH_CLIENT_ID="test-google-client-id")
def test_google_login_status_sets_short_lived_httponly_nonce_cookie():
    client = APIClient()

    response = client.get("/api/v1/auth/social/google/status/")

    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert response.json()["client_id"] == "test-google-client-id"
    assert response.json()["nonce"]
    nonce_cookie = response.cookies[settings.GOOGLE_OAUTH_NONCE_COOKIE_NAME]
    assert nonce_cookie.value == response.json()["nonce"]
    assert nonce_cookie["httponly"]


@override_settings(GOOGLE_OAUTH_CLIENT_ID="test-google-client-id")
def test_google_login_uses_verified_provider_identity_and_creates_workspace(
    django_user_model,
    monkeypatch,
):
    def verify_identity(credential, expected_nonce):
        assert credential == "provider-issued-id-token"
        assert expected_nonce == "test-login-nonce"
        return {
            "email": "google-user@example.com",
            "email_verified": True,
            "name": "Google User",
        }

    monkeypatch.setattr(
        "apps.accounts.views.verify_google_identity_token",
        verify_identity,
    )
    client = APIClient()
    client.cookies[settings.GOOGLE_OAUTH_NONCE_COOKIE_NAME] = "test-login-nonce"

    response = client.post(
        "/api/v1/auth/social/google/",
        {"credential": "provider-issued-id-token"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["access"]
    assert response.json()["user"]["email"] == "google-user@example.com"
    assert response.json()["user"]["is_email_verified"] is True
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME]["httponly"]
    assert response.cookies[settings.GOOGLE_OAUTH_NONCE_COOKIE_NAME].value == ""
    user = django_user_model.objects.get(email="google-user@example.com")
    assert user.organization_memberships.filter(status=MembershipStatus.ACTIVE).exists()
    assert AuditLog.objects.filter(action="auth.google_login", user=user).exists()


def test_google_login_returns_not_configured_without_client_id():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/social/google/",
        {"credential": "provider-issued-id-token"},
        format="json",
    )

    assert response.status_code == 503


@override_settings(GOOGLE_OAUTH_CLIENT_ID="test-google-client-id")
def test_google_identity_verification_requires_nonce_before_provider_call(monkeypatch):
    provider_call = lambda *_args, **_kwargs: pytest.fail("Provider must not be called")  # noqa: E731
    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", provider_call)

    with pytest.raises(InvalidGoogleIdentity, match="missing or expired"):
        verify_google_identity_token("provider-token", "")


@override_settings(GOOGLE_OAUTH_CLIENT_ID="test-google-client-id")
@pytest.mark.parametrize(
    ("claims", "expected_message"),
    [
        (
            {
                "iss": "https://untrusted.example",
                "email": "user@example.com",
                "email_verified": True,
                "nonce": "expected-nonce",
            },
            "Google identity could not be verified",
        ),
        (
            {
                "iss": "https://accounts.google.com",
                "email": "user@example.com",
                "email_verified": False,
                "nonce": "expected-nonce",
            },
            "email is not verified",
        ),
        (
            {
                "iss": "https://accounts.google.com",
                "email": "user@example.com",
                "email_verified": True,
                "nonce": "wrong-nonce",
            },
            "missing or expired",
        ),
    ],
)
def test_google_identity_verification_rejects_untrusted_claims(
    monkeypatch,
    claims,
    expected_message,
):
    monkeypatch.setattr(
        "google.oauth2.id_token.verify_oauth2_token",
        lambda *_args, **_kwargs: claims,
    )

    with pytest.raises(InvalidGoogleIdentity, match=expected_message):
        verify_google_identity_token("provider-token", "expected-nonce")


def test_google_identity_cannot_reactivate_suspended_existing_user(django_user_model):
    user = make_user(
        django_user_model,
        email="suspended-google@example.com",
        account_status=UserAccountStatus.SUSPENDED,
    )

    with pytest.raises(AuthenticationFailed, match="not active"):
        get_or_create_google_user(
            {
                "email": user.email,
                "email_verified": True,
                "name": "Suspended User",
            }
        )

    user.refresh_from_db()
    assert user.account_status == UserAccountStatus.SUSPENDED
    assert not user.organization_memberships.exists()


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


def test_password_recovery_request_returns_generic_response(django_user_model):
    user = make_user(django_user_model, email="recover@example.com", password="SaaSCore!23456")
    client = APIClient()

    response = client.post(
        "/api/v1/auth/password/recover/",
        {"email": user.email},
        format="json",
    )
    unknown_response = client.post(
        "/api/v1/auth/password/recover/",
        {"email": "unknown@example.com"},
        format="json",
    )

    assert response.status_code == 202
    assert unknown_response.status_code == 202
    assert response.json()["detail"] == unknown_response.json()["detail"]
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to
    assert "/reset-password?" in mail.outbox[0].body
    assert AuditLog.objects.filter(action="auth.password_recovery_requested").count() == 2


def test_password_reset_link_changes_password_revokes_refresh_and_is_single_use(django_user_model):
    user = make_user(django_user_model, email="reset@example.com", password="SaaSCore!23456")
    client = APIClient()
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "SaaSCore!23456"},
        format="json",
    )
    refresh_token = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
    client.post("/api/v1/auth/password/recover/", {"email": user.email}, format="json")
    reset_url = mail.outbox[0].body.splitlines()[-1]
    query = parse_qs(urlparse(reset_url).query)
    payload = {
        "uid": query["uid"][0],
        "token": query["token"][0],
        "new_password": "ResetSaaSCore!23456",
    }

    response = client.post("/api/v1/auth/password/reset/", payload, format="json")
    reused_response = client.post("/api/v1/auth/password/reset/", payload, format="json")
    refresh_response = client.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )

    assert response.status_code == 200
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value == ""
    assert reused_response.status_code == 400
    assert refresh_response.status_code == 401
    user.refresh_from_db()
    assert user.check_password("ResetSaaSCore!23456")
    assert AuditLog.objects.filter(action="auth.password_reset_completed", user=user).exists()


def test_authenticated_user_can_change_password_and_revoke_refresh_tokens(django_user_model):
    user = make_user(
        django_user_model,
        email="change-password@example.com",
        password="SaaSCore!23456",
    )
    client = APIClient()
    login_response = client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": "SaaSCore!23456"},
        format="json",
    )
    access_token = login_response.json()["access"]
    refresh_token = login_response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
    client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = refresh_token
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

    response = client.post(
        "/api/v1/auth/password/change/",
        {
            "current_password": "SaaSCore!23456",
            "new_password": "NewSaaSCore!23456",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value == ""
    user.refresh_from_db()
    assert user.check_password("NewSaaSCore!23456")
    assert AuditLog.objects.filter(action="auth.password_changed", user=user).exists()

    refresh_response = client.post(
        "/api/v1/auth/refresh/",
        {"refresh": refresh_token},
        format="json",
    )

    assert refresh_response.status_code == 401


def test_password_change_requires_current_password(django_user_model):
    user = make_user(django_user_model, email="bad-current-password@example.com")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/v1/auth/password/change/",
        {
            "current_password": "WrongPassword!23456",
            "new_password": "NewSaaSCore!23456",
        },
        format="json",
    )

    assert response.status_code == 400
    user.refresh_from_db()
    assert user.check_password("SaaSCore!23456")


def test_authenticated_user_can_update_profile_name(django_user_model):
    user = make_user(django_user_model, email="profile@example.com", name="Old Name")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.patch(
        "/api/v1/auth/me/",
        {"name": "New Name", "email": "changed@example.com"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["email"] == "profile@example.com"
    user.refresh_from_db()
    assert user.name == "New Name"
    assert user.email == "profile@example.com"


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


def test_invite_member_creates_pending_invitation_and_sends_email(django_user_model):
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
    assert len(mail.outbox) == 1
    assert "/accept-invitation?token=" in mail.outbox[0].body
    assert AuditLog.objects.filter(
        action="organizations.invitation.sent",
        organization=organization,
    ).exists()


def test_invited_user_can_accept_membership_invitation(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    invited_user = make_user(django_user_model, email="new.member@example.com")
    organization = create_organization_for_owner(owner, "Team Workspace")
    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)
    invite_response = owner_client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": invited_user.email, "role": MembershipRole.MEMBER},
        format="json",
    )
    invitation_url = mail.outbox[0].body.splitlines()[-1]
    token = parse_qs(urlparse(invitation_url).query)["token"][0]
    invited_client = APIClient()
    invited_client.force_authenticate(user=invited_user)

    response = invited_client.post(
        "/api/v1/organizations/invitations/accept/",
        {"token": token},
        format="json",
    )

    assert invite_response.status_code == 201
    assert response.status_code == 200
    membership = Membership.objects.get(id=response.json()["id"])
    assert membership.user == invited_user
    assert membership.status == MembershipStatus.ACTIVE
    assert membership.invited_email == ""
    assert AuditLog.objects.filter(
        action="organizations.invitation.accepted",
        organization=organization,
        user=invited_user,
    ).exists()


def test_invitation_rejects_user_with_different_email(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other_user = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Team Workspace")
    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)
    owner_client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": "invited@example.com", "role": MembershipRole.MEMBER},
        format="json",
    )
    invitation_url = mail.outbox[0].body.splitlines()[-1]
    token = parse_qs(urlparse(invitation_url).query)["token"][0]
    client = APIClient()
    client.force_authenticate(user=other_user)

    response = client.post(
        "/api/v1/organizations/invitations/accept/",
        {"token": token},
        format="json",
    )

    assert response.status_code == 400
    assert Membership.objects.get(organization=organization, invited_email="invited@example.com")


def test_admin_can_resend_and_cancel_pending_invitation(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Team Workspace")
    client = APIClient()
    client.force_authenticate(user=owner)
    invite_response = client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": "invited@example.com", "role": MembershipRole.MEMBER},
        format="json",
    )
    membership_id = invite_response.json()["id"]

    resend_response = client.post(
        f"/api/v1/organizations/{organization.id}/invitations/{membership_id}/resend/",
        {},
        format="json",
    )
    cancel_response = client.post(
        f"/api/v1/organizations/{organization.id}/invitations/{membership_id}/cancel/",
        {},
        format="json",
    )

    assert resend_response.status_code == 200
    assert cancel_response.status_code == 200
    assert len(mail.outbox) == 2
    assert Membership.objects.get(id=membership_id).status == MembershipStatus.DISABLED
    assert AuditLog.objects.filter(action="organizations.invitation.resent").exists()
    assert AuditLog.objects.filter(action="organizations.invitation.cancelled").exists()


def test_member_cannot_manage_organization_invitations(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Team Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)
    invitation_id = owner_client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": "invited@example.com", "role": MembershipRole.MEMBER},
        format="json",
    ).json()["id"]
    client = APIClient()
    client.force_authenticate(user=member)

    invite_response = client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": "second@example.com", "role": MembershipRole.MEMBER},
        format="json",
    )
    resend_response = client.post(
        f"/api/v1/organizations/{organization.id}/invitations/{invitation_id}/resend/",
        {},
        format="json",
    )
    cancel_response = client.post(
        f"/api/v1/organizations/{organization.id}/invitations/{invitation_id}/cancel/",
        {},
        format="json",
    )

    assert invite_response.status_code == 403
    assert resend_response.status_code == 403
    assert cancel_response.status_code == 403


def test_invitation_rejects_invalid_and_reused_tokens(django_user_model):
    owner = make_user(django_user_model, email="invite-owner@example.com")
    invited_user = make_user(django_user_model, email="invitee@example.com")
    organization = create_organization_for_owner(owner, "Invite Workspace")
    owner_client = APIClient()
    owner_client.force_authenticate(owner)
    owner_client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": invited_user.email, "role": MembershipRole.MEMBER},
        format="json",
    )
    invitation_url = mail.outbox[0].body.splitlines()[-1]
    token = parse_qs(urlparse(invitation_url).query)["token"][0]
    invited_client = APIClient()
    invited_client.force_authenticate(invited_user)

    invalid_response = invited_client.post(
        "/api/v1/organizations/invitations/accept/",
        {"token": f"{token}tampered"},
        format="json",
    )
    first_response = invited_client.post(
        "/api/v1/organizations/invitations/accept/",
        {"token": token},
        format="json",
    )
    reused_response = invited_client.post(
        "/api/v1/organizations/invitations/accept/",
        {"token": token},
        format="json",
    )

    assert invalid_response.status_code == 400
    assert first_response.status_code == 200
    assert reused_response.status_code == 400
    assert (
        organization.memberships.filter(
            user=invited_user,
            status=MembershipStatus.ACTIVE,
        ).count()
        == 1
    )


def test_invitation_rejects_token_with_mismatched_signed_email(django_user_model):
    owner = make_user(django_user_model, email="signed-owner@example.com")
    invited_user = make_user(django_user_model, email="signed-invitee@example.com")
    organization = create_organization_for_owner(owner, "Signed Invite Workspace")
    owner_client = APIClient()
    owner_client.force_authenticate(owner)
    response = owner_client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": invited_user.email, "role": MembershipRole.MEMBER},
        format="json",
    )
    token = signing.dumps(
        {
            "membership_id": response.json()["id"],
            "email": "different@example.com",
        },
        salt="organizations.membership-invitation",
        compress=True,
    )
    invited_client = APIClient()
    invited_client.force_authenticate(invited_user)

    accept_response = invited_client.post(
        "/api/v1/organizations/invitations/accept/",
        {"token": token},
        format="json",
    )

    assert accept_response.status_code == 400
    membership = Membership.objects.get(id=response.json()["id"])
    assert membership.status == MembershipStatus.INVITED
    assert membership.user is None


def test_inviting_existing_organization_member_is_rejected(django_user_model):
    owner = make_user(django_user_model, email="existing-owner@example.com")
    member = make_user(django_user_model, email="existing-member@example.com")
    organization = create_organization_for_owner(owner, "Existing Member Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        f"/api/v1/organizations/{organization.id}/invite-member/",
        {"email": member.email, "role": MembershipRole.ADMIN},
        format="json",
    )

    assert response.status_code == 400
    assert organization.memberships.filter(user=member).count() == 1
