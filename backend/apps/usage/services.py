from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.billing.services import get_subscription_for_organization

from .models import UsageRecord


class UsageLimitExceeded(APIException):
    status_code = 402
    default_detail = "This organization has reached the current plan limit for this action."
    default_code = "usage_limit_exceeded"


def current_month_period(reference_date=None):
    reference_date = reference_date or timezone.localdate()
    start = date(reference_date.year, reference_date.month, 1)
    last_day = monthrange(reference_date.year, reference_date.month)[1]
    end = date(reference_date.year, reference_date.month, last_day)
    return start, end


def get_usage_total(
    organization,
    metric_name,
    period_start=None,
    period_end=None,
    product_scope="",
):
    if period_start is None or period_end is None:
        period_start, period_end = current_month_period()
    total = (
        UsageRecord.objects.filter(
            organization=organization,
            metric_name=metric_name,
            period_start=period_start,
            period_end=period_end,
            product_scope=product_scope,
        ).aggregate(total=Sum("quantity"))["total"]
        or Decimal("0")
    )
    return total


def get_plan_limit(organization, metric_name):
    subscription = get_subscription_for_organization(organization)
    if subscription is None or subscription.plan is None:
        return None
    return subscription.plan.limit_for(metric_name)


def record_usage(
    organization,
    metric_name,
    quantity=1,
    source="",
    product_scope="",
    metadata=None,
    period_start=None,
    period_end=None,
):
    subscription = get_subscription_for_organization(organization)
    if period_start is None or period_end is None:
        period_start, period_end = current_month_period()
    return UsageRecord.objects.create(
        organization=organization,
        subscription=subscription,
        period_start=period_start,
        period_end=period_end,
        metric_name=metric_name,
        quantity=Decimal(str(quantity)),
        source=source,
        product_scope=product_scope,
        metadata=metadata or {},
    )


def assert_within_usage_limit(organization, metric_name, quantity=1, product_scope=""):
    limit = get_plan_limit(organization, metric_name)
    if limit is None:
        return True

    period_start, period_end = current_month_period()
    current_usage = get_usage_total(
        organization,
        metric_name,
        period_start=period_start,
        period_end=period_end,
        product_scope=product_scope,
    )
    requested = Decimal(str(quantity))
    if current_usage + requested > Decimal(str(limit)):
        raise UsageLimitExceeded(
            f"Plan limit exceeded for '{metric_name}'. "
            f"Limit: {limit}; current usage: {current_usage}."
        )
    return True


def usage_summary_for_organization(organization):
    subscription = get_subscription_for_organization(organization)
    if subscription is None:
        return {"plan": None, "period": None, "metrics": []}

    period_start, period_end = current_month_period()
    metrics = []
    for metric_name, limit in subscription.plan.limits.items():
        used = get_usage_total(
            organization,
            metric_name,
            period_start=period_start,
            period_end=period_end,
        )
        metrics.append(
            {
                "metric_name": metric_name,
                "used": str(used),
                "limit": limit,
            }
        )

    return {
        "plan": {
            "slug": subscription.plan.slug,
            "name": subscription.plan.name,
            "status": subscription.status,
        },
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "metrics": metrics,
    }
