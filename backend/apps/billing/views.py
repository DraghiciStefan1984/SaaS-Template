import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import (
    ADMIN_ROLES,
    require_membership,
    require_organization_role,
)

from .models import Plan
from .serializers import (
    CheckoutSerializer,
    CheckoutSessionSerializer,
    CustomerPortalSerializer,
    CustomerPortalSessionSerializer,
    PlanSerializer,
    StripeWebhookResponseSerializer,
    SubscriptionSerializer,
    SubscriptionSummarySerializer,
)
from .services import (
    construct_stripe_event,
    create_checkout_session,
    create_customer_portal_session,
    get_subscription_for_organization,
    process_stripe_event,
)


class PlanListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PlanSerializer
    pagination_class = None

    def get_queryset(self):
        return Plan.objects.filter(is_public=True, is_active=True).order_by("display_order", "name")


class OrganizationBillingMixin:
    def get_user_organization(self, organization_id):
        return get_object_or_404(
            Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__status=MembershipStatus.ACTIVE,
            ).distinct(),
            id=organization_id,
        )


class SubscriptionView(OrganizationBillingMixin, APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="organization_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses=SubscriptionSerializer,
    )
    def get(self, request):
        organization = self.get_user_organization(request.query_params.get("organization_id"))
        membership = require_membership(request.user, organization)
        subscription = get_subscription_for_organization(organization)
        serializer_class = (
            SubscriptionSerializer
            if membership.role in ADMIN_ROLES
            else SubscriptionSummarySerializer
        )
        return Response(serializer_class(subscription).data)


class CheckoutView(OrganizationBillingMixin, APIView):
    throttle_scope = "billing_action"

    @extend_schema(request=CheckoutSerializer, responses={201: CheckoutSessionSerializer})
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = self.get_user_organization(serializer.validated_data["organization_id"])
        require_organization_role(request.user, organization, ADMIN_ROLES)
        plan = get_object_or_404(Plan, slug=serializer.validated_data["plan_slug"], is_active=True)
        log_audit_event(
            action="billing.checkout.requested",
            organization=organization,
            request=request,
            category="billing",
            target_entity_type="plan",
            target_entity_id=plan.slug,
        )

        success_url = serializer.validated_data.get(
            "success_url",
            f"{settings.FRONTEND_BASE_URL}/billing/success",
        )
        cancel_url = serializer.validated_data.get(
            "cancel_url",
            f"{settings.FRONTEND_BASE_URL}/billing/cancel",
        )
        result = create_checkout_session(organization, plan, success_url, cancel_url)
        return Response(result, status=status.HTTP_201_CREATED)


class CustomerPortalView(OrganizationBillingMixin, APIView):
    throttle_scope = "billing_action"

    @extend_schema(request=CustomerPortalSerializer, responses=CustomerPortalSessionSerializer)
    def post(self, request):
        serializer = CustomerPortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = self.get_user_organization(serializer.validated_data["organization_id"])
        require_organization_role(request.user, organization, ADMIN_ROLES)
        subscription = get_subscription_for_organization(organization)
        log_audit_event(
            action="billing.customer_portal.requested",
            organization=organization,
            request=request,
            category="billing",
            target_entity_type="subscription",
            target_entity_id=subscription.id if subscription else "",
        )
        return_url = serializer.validated_data.get(
            "return_url",
            f"{settings.FRONTEND_BASE_URL}/billing",
        )
        result = create_customer_portal_session(subscription, return_url)
        return Response(result)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "billing_action"

    @extend_schema(request=None, responses=StripeWebhookResponseSerializer)
    def post(self, request):
        signature = request.headers.get("Stripe-Signature", "")
        try:
            event = construct_stripe_event(request.body, signature)
        except ValueError:
            return Response(
                {"detail": "Invalid Stripe payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.SignatureVerificationError:
            return Response(
                {"detail": "Invalid Stripe signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = process_stripe_event(event)
        log_audit_event(
            action="billing.stripe_webhook.received",
            request=request,
            category="billing",
            target_entity_type="stripe_event",
            target_entity_id=result.get("event_type") or "",
        )
        return Response(result)
