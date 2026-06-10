# Reports, Jobs, and Notifications

Phase 5 adds reusable foundations for queued reporting workflows and notification
delivery. The implementation is intentionally product-agnostic: it creates the
workflow state, audit logs, generic artifact rendering, and extension points,
while product-specific analysis and real provider delivery can be plugged in later.

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
- `GET /api/v1/reports/{id}/artifacts/{artifact_id}/download/`

Current behavior:

- Default templates are seeded for weekly summaries and table analysis.
- Creating a report also creates a `JobRun`.
- The Celery task `apps.reports.tasks.generate_report_task` selects an AI execution
  plan, creates generic structured artifact content, marks the report succeeded,
  and sends email/in-app notifications.
- Database artifacts are rendered at download time as JSON, CSV, HTML, PDF, or
  DOCX. Product modules should replace or extend the structured content with
  domain-specific results.
- Owner/admin users can download database or safe local-file artifacts through an
  audited, organization-scoped endpoint.
- S3-compatible artifacts require a production storage adapter that returns a
  short-lived presigned URL; this remains intentionally unconfigured.

## Jobs

Core models:

- `JobRun`: queued/running/succeeded/failed/retrying/cancelled workflow state with
  attempts, max attempts, errors, related entity metadata, and timestamps.
- `ScheduledWorkflow`: organization-scoped safe workflow definition. The core
  registry currently permits scheduled report generation only.
- `ScheduledRun`: scheduled/manual execution history linked to its `JobRun`.

Implemented endpoints:

- `GET /api/v1/jobs/?organization_id=...`
- `GET/POST /api/v1/jobs/schedules/`
- `GET /api/v1/jobs/schedules/{id}/runs/`
- `POST /api/v1/jobs/schedules/{id}/run/`
- `POST /api/v1/jobs/schedules/{id}/pause/`
- `POST /api/v1/jobs/schedules/{id}/resume/`

Reusable services:

- `create_job_run(...)`
- `mark_job_started(...)`
- `mark_job_succeeded(...)`
- `mark_job_failed(...)`
- `create_scheduled_workflow(...)`
- `run_scheduled_workflow(...)`
- `set_scheduled_workflow_status(...)`

Current scheduling behavior:

- Schedule management is restricted to organization owners/admins.
- Daily, weekly, and monthly schedules are supported.
- Both the `scheduled_reports` and `reports` features and the report usage limit
  are enforced server-side.
- Celery Beat dispatches due schedules every minute. One failed schedule is
  logged and does not stop the other due schedules.

## Notifications

Core models:

- `NotificationPreference`: organization/user event preferences by channel.
- `NotificationDeliveryLog`: provider-independent delivery tracking.
- `InAppNotification`: user-scoped notification-center state with read timestamps.

Implemented endpoints:

- `GET /api/v1/notifications/preferences/?organization_id=...`
- `POST /api/v1/notifications/preferences/`
- `GET /api/v1/notifications/delivery-logs/?organization_id=...`
- `GET /api/v1/notifications/in-app/?organization_id=...`
- `POST /api/v1/notifications/in-app/{id}/read/`
- `POST /api/v1/notifications/in-app/read-all/`

Current behavior:

- Email notifications use `EMAIL_PROVIDER`.
- `EMAIL_PROVIDER=console` marks delivery as sent with a local placeholder message ID.
- Other email providers return failed delivery logs until SES/Resend/Postmark clients
  are implemented behind the notification service layer.
- In-app notifications create user-visible, organization-scoped records without
  exposing delivery payloads or provider metadata.
- Webhook delivery is intentionally not configured yet.

## Product Extension Rule

Each product should add its own report builder/rendering service and call the
shared report/job/notification services. Do not send email, call AI providers, or
run long jobs directly from views.
