from django.db import transaction

from .models import Membership, MembershipRole, Organization


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
