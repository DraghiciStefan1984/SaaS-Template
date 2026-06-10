from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Membership, MembershipRole, MembershipStatus, Organization

INVITATION_TOKEN_SALT = "organizations.membership-invitation"


@transaction.atomic
def create_organization_for_owner(owner, name, timezone="UTC", default_language="en"):
    organization = Organization.objects.create(
        owner=owner,
        name=name,
        timezone=timezone,
        default_language=default_language,
    )
    Membership.objects.create(
        organization=organization,
        user=owner,
        role=MembershipRole.OWNER,
    )

    # Billing is optional at template bootstrap. Once default plans exist, every
    # organization receives a free subscription foundation for usage enforcement.
    from apps.billing.services import ensure_free_subscription

    ensure_free_subscription(organization)
    return organization


def build_membership_invitation_token(membership):
    return signing.dumps(
        {
            "membership_id": membership.id,
            "email": membership.invited_email,
        },
        salt=INVITATION_TOKEN_SALT,
        compress=True,
    )


def build_membership_invitation_url(membership):
    token = build_membership_invitation_token(membership)
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/accept-invitation?token={token}"


def send_membership_invitation_email(membership):
    invitation_url = build_membership_invitation_url(membership)
    # TODO(email-provider): Django's email backend supports local testing. Configure
    # SES, Resend, or Postmark credentials before enabling production delivery.
    return send_mail(
        subject=f"You were invited to {membership.organization.name}",
        message=(
            f"You were invited to join {membership.organization.name}.\n\n"
            f"Accept the invitation:\n{invitation_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[membership.invited_email],
        fail_silently=False,
    )


@transaction.atomic
def create_or_refresh_membership_invitation(*, organization, email, role, invited_by):
    normalized_email = email.strip().lower()
    existing_user = get_user_model().objects.filter(email__iexact=normalized_email).first()
    if existing_user and Membership.objects.filter(
        organization=organization,
        user=existing_user,
    ).exists():
        raise ValidationError({"email": "This user already has a membership in the organization."})

    membership = Membership.objects.filter(
        organization=organization,
        user__isnull=True,
        invited_email__iexact=normalized_email,
        status=MembershipStatus.INVITED,
    ).first()
    if membership is None:
        membership = Membership.objects.create(
            organization=organization,
            role=role,
            status=MembershipStatus.INVITED,
            invited_email=normalized_email,
            invited_by=invited_by,
        )
    else:
        membership.role = role
        membership.invited_by = invited_by
        membership.save(update_fields=["role", "invited_by", "updated_at"])

    return membership


def decode_membership_invitation_token(token):
    try:
        return signing.loads(
            token,
            salt=INVITATION_TOKEN_SALT,
            max_age=settings.ORGANIZATION_INVITATION_MAX_AGE,
        )
    except signing.SignatureExpired as exc:
        raise ValidationError({"token": "This invitation has expired."}) from exc
    except signing.BadSignature as exc:
        raise ValidationError({"token": "This invitation token is invalid."}) from exc


@transaction.atomic
def accept_membership_invitation(*, token, user):
    payload = decode_membership_invitation_token(token)
    membership = (
        Membership.objects.select_for_update()
        .select_related("organization")
        .filter(
            id=payload.get("membership_id"),
            status=MembershipStatus.INVITED,
            user__isnull=True,
        )
        .first()
    )
    if membership is None:
        raise ValidationError({"token": "This invitation is no longer available."})

    invited_email = membership.invited_email.strip().lower()
    if payload.get("email", "").strip().lower() != invited_email:
        raise ValidationError({"token": "This invitation token is invalid."})
    if user.email.strip().lower() != invited_email:
        raise ValidationError({"token": "Sign in with the email address that was invited."})
    if Membership.objects.filter(organization=membership.organization, user=user).exists():
        raise ValidationError({"token": "This account already has an organization membership."})

    membership.user = user
    membership.status = MembershipStatus.ACTIVE
    membership.invited_email = ""
    membership.joined_at = timezone.now()
    membership.save(
        update_fields=["user", "status", "invited_email", "joined_at", "updated_at"]
    )
    return membership


@transaction.atomic
def cancel_membership_invitation(membership):
    if membership.status != MembershipStatus.INVITED or membership.user_id is not None:
        raise ValidationError({"invitation": "Only pending invitations can be cancelled."})
    membership.status = MembershipStatus.DISABLED
    membership.save(update_fields=["status", "updated_at"])
    return membership
