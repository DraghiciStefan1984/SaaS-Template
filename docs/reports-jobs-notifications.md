# Reports, Jobs, and Notifications

Phase 5 adds reusable foundations for queued reporting workflows and notification
delivery. The implementation is intentionally product-agnostic: it creates the
workflow state, audit logs, and extension points, while product-specific report
rendering and real provider delivery can be plugged in later.

## Reports

Core models:

- `ReportTemplate`: reusable template registry connected to an optional AI task profile.
- `Report`: organization-scoped report request and lifecycle state.
- `ReportArtifact`: generated output metadata/content for JSON, HTML, PDF, CSV, or DOCX.

Implemented endpoints:

- `GET /api/v1/reports/templates/`
- `GET /api/v1/reports/?organization_id=...`
- `POST /api/v1/reports/`
- `GET /api/v1/reports/{id}/`
- `GET /api/v1/reports/{id}/artifacts/`

Current behavior:

- Default templates are seeded for weekly summaries and table analysis.
- Creating a report also creates a `JobRun`.
- The Celery task `apps.reports.tasks.generate_report_task` is a safe placeholder:
  it selects an AI execution plan, creates a JSON artifact, marks the report
  succeeded, and sends a console notification.
- Product-specific report rendering should replace the placeholder artifact logic.

## Jobs

Core model:

- `JobRun`: queued/running/succeeded/failed/retrying/cancelled workflow state with
  attempts, max attempts, errors, related entity metadata, and timestamps.

Implemented endpoint:

- `GET /api/v1/jobs/?organization_id=...`

Reusable services:

- `create_job_run(...)`
- `mark_job_started(...)`
- `mark_job_succeeded(...)`
- `mark_job_failed(...)`

## Notifications

Core models:

- `NotificationPreference`: organization/user event preferences by channel.
- `NotificationDeliveryLog`: provider-independent delivery tracking.

Implemented endpoints:

- `GET /api/v1/notifications/preferences/?organization_id=...`
- `POST /api/v1/notifications/preferences/`
- `GET /api/v1/notifications/delivery-logs/?organization_id=...`

Current behavior:

- Email notifications use `EMAIL_PROVIDER`.
- `EMAIL_PROVIDER=console` marks delivery as sent with a local placeholder message ID.
- Other email providers return failed delivery logs until SES/Resend/Postmark clients
  are implemented behind the notification service layer.
- In-app notifications are marked sent locally.
- Webhook delivery is intentionally not configured yet.

## Product Extension Rule

Each product should add its own report builder/rendering service and call the
shared report/job/notification services. Do not send email, call AI providers, or
run long jobs directly from views.
