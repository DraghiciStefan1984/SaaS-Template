from django.urls import path

from .views import (
    CheckoutView,
    CustomerPortalView,
    PlanListView,
    StripeWebhookView,
    SubscriptionView,
)

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="billing-plans"),
    path("subscription/", SubscriptionView.as_view(), name="billing-subscription"),
    path("checkout/", CheckoutView.as_view(), name="billing-checkout"),
    path("customer-portal/", CustomerPortalView.as_view(), name="billing-customer-portal"),
    path("webhooks/stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
]

