from rest_framework import serializers

from .models import Membership, MembershipStatus, Organization
from .permissions import get_active_membership
from .services import create_organization_for_owner


class OrganizationUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    name = serializers.CharField()


class OrganizationSerializer(serializers.ModelSerializer):
    owner = OrganizationUserSerializer(read_only=True)
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = (
            "id",
            "name",
            "owner",
            "timezone",
            "default_language",
            "my_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "my_role", "created_at", "updated_at")

    def get_my_role(self, obj) -> str | None:
        request = self.context.get("request")
        user = self.context.get("current_user") or getattr(request, "user", None)
        if not user:
            return None

        membership = get_active_membership(user, obj)
        return membership.role if membership else None

    def create(self, validated_data):
        return create_organization_for_owner(owner=self.context["request"].user, **validated_data)


class MembershipSerializer(serializers.ModelSerializer):
    user = OrganizationUserSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Membership
        fields = (
            "id",
            "organization",
            "user",
            "role",
            "status",
            "invited_email",
            "joined_at",
            "created_at",
        )
        read_only_fields = (
            "id",
            "organization",
            "user",
            "status",
            "invited_email",
            "joined_at",
            "created_at",
        )


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=("admin", "member"), default="member")

    def create(self, validated_data):
        organization = self.context["organization"]
        invited_by = self.context["request"].user

        # Email delivery is intentionally not connected yet. When the selected
        # email provider account exists, route invite sending through NotificationService.
        return Membership.objects.create(
            organization=organization,
            user=None,
            role=validated_data["role"],
            status=MembershipStatus.INVITED,
            invited_email=validated_data["email"],
            invited_by=invited_by,
        )
