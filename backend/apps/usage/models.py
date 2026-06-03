from decimal import Decimal

from django.db import models


class UsageRecord(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="usage_records",
    )
    subscription = models.ForeignKey(
        "billing.Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usage_records",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    metric_name = models.CharField(max_length=120)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, default=Decimal("0"))
    source = models.CharField(max_length=120, blank=True)
    product_scope = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "metric_name", "period_start", "period_end"]),
            models.Index(fields=["organization", "product_scope", "period_start"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"{self.organization} {self.metric_name} {self.quantity}"

