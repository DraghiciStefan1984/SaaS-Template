from django.conf import settings

from .models import (
    NotificationChannel,
    NotificationDeliveryLog,
    NotificationEvent,
    NotificationPreference,
)


def upsert_notification_preference(
    *,
    organization,
    event,
    channel,
    user=None,
    is_enabled=True,
    config=None,
):
    preference, _created = NotificationPreference.objects.update_or_create(
        organization=organization,
        user=user,
        event=event,
        channel=channel,
        defaults={
            "is_enabled": is_enabled,
            "config": config or {},
        },
    )
    return preference


def notification_is_enabled(*, organization, event, channel, user=None):
    user_preference = None
    if user is not None:
        user_preference = NotificationPreference.objects.filter(
            organization=organization,
            user=user,
            event=event,
            channel=channel,
        ).first()
    if user_preference is not None:
        return user_preference.is_enabled

    organization_preference = NotificationPreference.objects.filter(
        organization=organization,
        user__isnull=True,
        event=event,
        channel=channel,
    ).first()
    if organization_preference is not None:
        return organization_preference.is_enabled
    return True


def create_delivery_log(
    *,
    organization,
    event,
    channel,
    user=None,
    recipient="",
    subject="",
    payload=None,
    provider="",
    metadata=None,
):
    return NotificationDeliveryLog.objects.create(
        organization=organization,
        user=user,
        event=event,
        channel=channel,
        recipient=recipient,
        subject=subject,
        payload=payload or {},
        provider=provider,
        metadata=metadata or {},
    )


def send_notification(
    *,
    organization,
    event,
    channel,
    user=None,
    recipient="",
    subject="",
    payload=None,
    metadata=None,
):
    provider = settings.EMAIL_PROVIDER if channel == NotificationChannel.EMAIL else "internal"
    log = create_delivery_log(
        organization=organization,
        user=user,
        event=event,
        channel=channel,
        recipient=recipient,
        subject=subject,
        payload=payload,
        provider=provider,
        metadata=metadata,
    )

    if not notification_is_enabled(
        organization=organization,
        user=user,
        event=event,
        channel=channel,
    ):
        return log.mark_skipped("Notification preference disabled.")

    if channel == NotificationChannel.EMAIL:
        if provider == "console":
            # Local placeholder: replace with SES/Resend/Postmark client in product deployments.
            return log.mark_sent(provider_message_id=f"console-{log.id}")
        return log.mark_failed(
            f"Email provider '{provider}' is not configured in the core template yet."
        )

    if channel == NotificationChannel.IN_APP:
        return log.mark_sent(provider_message_id=f"in-app-{log.id}")

    return log.mark_failed("Webhook delivery is not configured in the core template yet.")


def send_report_ready_notification(report):
    recipient = report.created_by.email if report.created_by else ""
    return send_notification(
        organization=report.organization,
        user=report.created_by,
        event=NotificationEvent.REPORT_READY,
        channel=NotificationChannel.EMAIL,
        recipient=recipient,
        subject=f"Report ready: {report.title}",
        payload={
            "report_id": report.id,
            "title": report.title,
            "status": report.status,
        },
        metadata={"source": "reports.generate_report_task"},
    )
