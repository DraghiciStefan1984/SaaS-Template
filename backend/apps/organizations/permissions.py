from rest_framework.exceptions import PermissionDenied

from .models import Membership, MembershipRole, MembershipStatus


def get_active_membership(user, organization):
    if not user or not user.is_authenticated:
        return None

    return Membership.objects.filter(
        user=user,
        organization=organization,
        status=MembershipStatus.ACTIVE,
    ).first()


def require_membership(user, organization):
    membership = get_active_membership(user, organization)
    if membership is None:
        raise PermissionDenied("You do not have access to this organization.")
    return membership


def require_organization_role(user, organization, allowed_roles):
    membership = require_membership(user, organization)
    if membership.role not in allowed_roles:
        raise PermissionDenied("You do not have permission to perform this action.")
    return membership


ADMIN_ROLES = {MembershipRole.OWNER, MembershipRole.ADMIN}
OWNER_ROLES = {MembershipRole.OWNER}

