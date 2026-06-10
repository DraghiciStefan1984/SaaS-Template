from django.conf import settings

from .models import (
    InAppNotification,
    NotificationChannel,
    NotificationDeliveryLog,
    NotificationEvent,
    NotificationPreference,
)


def create_in_app_notification(
    *,
    organization,
    user,
    event,
    title,
    message="",
    target_url="",
    metadata=None,
):
    if user is None:
        raise ValueError("In-app notifications require a target user.")
    safe_target_url = (
        target_url if target_url.startswith("/") and not target_url.startswith("//") else ""
    )
    return InAppNotification.objects.create(
        organization=organization,
        user=user,
        event=event,
        title=title,
        message=message,
        target_url=safe_target_url,
        metadata=metadata or {},
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
        if user is None:
            return log.mark_failed("In-app notifications require a target user.")
        notification = create_in_app_notification(
            organization=organization,
            user=user,
            event=event,
            title=subject or event.replace("_", " ").title(),
            message=(payload or {}).get("message", ""),
            target_url=(payload or {}).get("target_url", ""),
            metadata=metadata,
        )
        return log.mark_sent(provider_message_id=f"in-app-{notification.id}")

    return log.mark_failed("Webhook delivery is not configured in the core template yet.")


def send_report_ready_notification(report):
    recipient = report.created_by.email if report.created_by else ""
    email_log = send_notification(
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
    if report.created_by:
        send_notification(
            organization=report.organization,
            user=report.created_by,
            event=NotificationEvent.REPORT_READY,
            channel=NotificationChannel.IN_APP,
            subject=f"Report ready: {report.title}",
            payload={
                "message": "Your report is ready to review.",
                "target_url": "/dashboard/reports",
            },
            metadata={"source": "reports.generate_report_task", "report_id": report.id},
        )
    return email_log
