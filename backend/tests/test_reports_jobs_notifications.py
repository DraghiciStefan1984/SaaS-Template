from datetime import UTC, datetime, timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.ai.models import AIModelDecisionLog
from apps.audit.models import AuditLog
from apps.jobs.models import (
    JobRun,
    JobRunStatus,
    ScheduledRun,
    ScheduledRunTrigger,
    ScheduledWorkflowStatus,
    ScheduleFrequency,
)
from apps.jobs.services import (
    calculate_next_run_at,
    create_job_run,
    create_scheduled_workflow,
    mark_job_failed,
    mark_job_started,
    run_scheduled_workflow,
    set_scheduled_workflow_status,
)
from apps.jobs.tasks import dispatch_due_scheduled_workflows
from apps.notifications.models import (
    InAppNotification,
    NotificationChannel,
    NotificationDeliveryLog,
    NotificationDeliveryStatus,
    NotificationEvent,
    NotificationPreference,
)
from apps.notifications.services import (
    create_in_app_notification,
    notification_is_enabled,
    send_notification,
    send_report_ready_notification,
    upsert_notification_preference,
)
from apps.organizations.models import Membership, MembershipRole, MembershipStatus
from apps.organizations.services import create_organization_for_owner
from apps.reports.models import Report, ReportArtifact, ReportStatus, ReportTemplate
from apps.reports.renderers import render_report_artifact
from apps.reports.services import (
    ReportArtifactDownloadUnavailable,
    create_report_request,
    report_artifact_download,
)
from apps.reports.tasks import generate_report_task
from apps.usage.models import UsageRecord

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


def enable_scheduled_reports(organization, generated_reports=10):
    plan = organization.subscription.plan
    plan.features = {**plan.features, "scheduled_reports": True, "reports": True}
    plan.limits = {**plan.limits, "generated_reports": generated_reports}
    plan.save(update_fields=["features", "limits", "updated_at"])


def test_default_report_templates_are_available(django_user_model):
    user = make_user(django_user_model, email="owner@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/reports/templates/")

    assert response.status_code == 200
    template_keys = {template["key"] for template in response.json()}
    assert {"weekly_summary", "table_analysis"}.issubset(template_keys)
    weekly_summary = ReportTemplate.objects.get(key="weekly_summary")
    assert weekly_summary.ai_task_profile.key == "recurring_ai_report"


def test_report_request_endpoint_creates_report_and_job_run(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/reports/",
        {
            "organization_id": organization.id,
            "title": "Weekly KPI Summary",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": {"metrics": {"revenue": 1000}},
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == ReportStatus.QUEUED
    assert body["job_run_id"] == JobRun.objects.get().id
    report = Report.objects.get(id=body["id"])
    assert report.template.key == "weekly_summary"
    assert report.organization == organization
    assert UsageRecord.objects.filter(
        organization=organization,
        metric_name="generated_reports",
        source="reports.create_request",
    ).exists()


def test_create_report_request_enqueues_generation_task(
    django_user_model,
    django_capture_on_commit_callbacks,
    monkeypatch,
):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    calls = []

    class TaskResult:
        id = "celery-task-123"

    def fake_delay(report_id, job_run_id):
        calls.append((report_id, job_run_id))
        return TaskResult()

    monkeypatch.setattr("apps.reports.tasks.generate_report_task.delay", fake_delay)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        report, job_run = create_report_request(
            organization=organization,
            created_by=owner,
            title="Queued Report",
            template_key="weekly_summary",
            input_payload={"metrics": {"revenue": 1000}},
        )

    job_run.refresh_from_db()
    assert len(callbacks) == 1
    assert calls == [(report.id, job_run.id)]
    assert job_run.metadata["celery_task_id"] == "celery-task-123"


def test_report_request_endpoint_respects_generated_report_limit(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)
    payload = {
        "organization_id": organization.id,
        "title": "Weekly KPI Summary",
        "template_key": "weekly_summary",
        "requested_format": "json",
        "input_payload": {"metrics": {"revenue": 1000}},
    }

    first_response = client.post("/api/v1/reports/", payload, format="json")
    second_response = client.post(
        "/api/v1/reports/",
        {**payload, "title": "Second KPI Summary"},
        format="json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 402
    assert Report.objects.filter(organization=organization).count() == 1
    assert (
        UsageRecord.objects.filter(
            organization=organization,
            metric_name="generated_reports",
        ).count()
        == 1
    )


def test_report_request_endpoint_respects_report_feature_flag(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    organization.subscription.plan.features = {
        **organization.subscription.plan.features,
        "reports": False,
    }
    organization.subscription.plan.save(update_fields=["features", "updated_at"])
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/reports/",
        {
            "organization_id": organization.id,
            "title": "Blocked Report",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": {"metrics": {"revenue": 1000}},
        },
        format="json",
    )

    assert response.status_code == 403
    assert Report.objects.filter(organization=organization).count() == 0
    assert UsageRecord.objects.filter(organization=organization).count() == 0


def test_report_request_rejects_unknown_template_key(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/reports/",
        {
            "organization_id": organization.id,
            "title": "Typo Report",
            "template_key": "wekly-summary",
            "requested_format": "json",
            "input_payload": {"metrics": {"revenue": 1000}},
        },
        format="json",
    )

    assert response.status_code == 400
    assert "template_key" in response.json()
    assert Report.objects.filter(organization=organization).count() == 0
    assert UsageRecord.objects.filter(organization=organization).count() == 0


def test_report_request_rejects_non_object_input_payload(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/reports/",
        {
            "organization_id": organization.id,
            "title": "Invalid Payload Report",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": ["not", "an", "object"],
        },
        format="json",
    )

    assert response.status_code == 400
    assert "input_payload" in response.json()
    assert Report.objects.filter(organization=organization).count() == 0
    assert UsageRecord.objects.filter(organization=organization).count() == 0


@override_settings(MAX_JSON_PAYLOAD_BYTES=20)
def test_report_request_rejects_oversized_input_payload(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/reports/",
        {
            "organization_id": organization.id,
            "title": "Oversized Report",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": {"large": "x" * 100},
        },
        format="json",
    )

    assert response.status_code == 400


def test_generate_report_task_creates_artifact_ai_decision_and_notification(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    template = ReportTemplate.objects.get(key="weekly_summary")
    report = Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Weekly KPI Summary",
        template=template,
        error_message="old transient error",
        input_payload={"metrics": {"revenue": 1000}},
    )
    job_run = create_job_run(
        organization=organization,
        created_by=owner,
        name="Generate report",
        task_name="apps.reports.tasks.generate_report_task",
        related_entity_type="report",
        related_entity_id=str(report.id),
        metadata={"report_id": report.id, "template_key": template.key},
    )

    result = generate_report_task(report.id, job_run.id)

    report.refresh_from_db()
    job_run.refresh_from_db()
    assert report.status == ReportStatus.SUCCEEDED
    assert report.error_message == ""
    assert job_run.status == JobRunStatus.SUCCEEDED
    assert result["report_id"] == report.id
    artifact = ReportArtifact.objects.get(report=report)
    assert artifact.content["status"] == "generated"
    assert artifact.content["execution_plan"]["strategy"] == "low_cost_llm"
    assert AIModelDecisionLog.objects.filter(
        organization=organization,
        task_key="recurring_ai_report",
    ).exists()
    assert NotificationDeliveryLog.objects.filter(
        organization=organization,
        event="report_ready",
        status=NotificationDeliveryStatus.SENT,
    ).exists()
    assert InAppNotification.objects.filter(
        organization=organization,
        user=owner,
        event=NotificationEvent.REPORT_READY,
        is_read=False,
    ).exists()


def test_admin_can_create_run_pause_and_resume_scheduled_report(django_user_model):
    owner = make_user(django_user_model, email="schedule-owner@example.com")
    organization = create_organization_for_owner(owner, "Scheduled Workspace")
    enable_scheduled_reports(organization)
    client = APIClient()
    client.force_authenticate(owner)

    create_response = client.post(
        "/api/v1/jobs/schedules/",
        {
            "organization_id": organization.id,
            "name": "Weekly KPI schedule",
            "frequency": "weekly",
            "timezone": "Europe/Bucharest",
            "title": "Weekly KPI report",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": {"metrics": {"revenue": 1000}},
        },
        format="json",
    )
    workflow_id = create_response.json()["id"]
    run_response = client.post(f"/api/v1/jobs/schedules/{workflow_id}/run/")
    pause_response = client.post(f"/api/v1/jobs/schedules/{workflow_id}/pause/")
    resume_response = client.post(f"/api/v1/jobs/schedules/{workflow_id}/resume/")

    assert create_response.status_code == 201
    assert run_response.status_code == 200
    assert run_response.json()["trigger"] == "manual"
    assert pause_response.json()["status"] == ScheduledWorkflowStatus.PAUSED
    assert resume_response.json()["status"] == ScheduledWorkflowStatus.ACTIVE
    assert ScheduledRun.objects.filter(workflow_id=workflow_id, trigger="manual").exists()
    assert Report.objects.filter(
        organization=organization,
        related_entity_type="scheduled_workflow",
        related_entity_id=str(workflow_id),
    ).exists()
    assert UsageRecord.objects.filter(
        organization=organization,
        source="jobs.run_scheduled_workflow",
    ).exists()
    assert AuditLog.objects.filter(action="jobs.scheduled_workflow.run").exists()


def test_scheduled_dispatch_runs_due_workflow_once_and_advances_next_run(django_user_model):
    owner = make_user(django_user_model, email="due-schedule@example.com")
    organization = create_organization_for_owner(owner, "Due Schedule Workspace")
    enable_scheduled_reports(organization)
    due_at = timezone.now() - timedelta(minutes=5)
    workflow = create_scheduled_workflow(
        organization=organization,
        created_by=owner,
        name="Daily due report",
        frequency="daily",
        timezone_name="UTC",
        next_run_at=due_at,
        config={
            "title": "Daily report",
            "template_key": "weekly_summary",
            "requested_format": "json",
            "input_payload": {},
        },
    )

    result = dispatch_due_scheduled_workflows()

    workflow.refresh_from_db()
    assert result["dispatched"] == 1
    assert workflow.next_run_at > timezone.now()
    assert ScheduledRun.objects.filter(workflow=workflow, trigger="scheduled").count() == 1


def test_scheduled_dispatch_continues_after_one_workflow_fails(django_user_model, monkeypatch):
    owner = make_user(django_user_model, email="dispatch-failure@example.com")
    organization = create_organization_for_owner(owner, "Dispatch Failure Workspace")
    enable_scheduled_reports(organization)
    due_at = timezone.now() - timedelta(minutes=5)
    workflows = [
        create_scheduled_workflow(
            organization=organization,
            created_by=owner,
            name=f"Due report {index}",
            frequency="daily",
            timezone_name="UTC",
            next_run_at=due_at,
            config={"title": "Daily report", "template_key": "weekly_summary"},
        )
        for index in range(2)
    ]
    calls = []

    def run_or_fail(workflow, **_kwargs):
        calls.append(workflow.id)
        if workflow.id == workflows[0].id:
            raise RuntimeError("Invalid schedule")
        return object()

    monkeypatch.setattr("apps.jobs.tasks.run_scheduled_workflow", run_or_fail)

    result = dispatch_due_scheduled_workflows()

    assert result == {"due": 2, "dispatched": 1, "failed": 1}
    assert calls == [workflow.id for workflow in workflows]


def test_schedule_calculation_handles_month_end_and_rejects_unsupported_frequency():
    january_31 = datetime(2024, 1, 31, 10, tzinfo=UTC)
    february_29 = calculate_next_run_at(january_31, ScheduleFrequency.MONTHLY)
    march_29 = calculate_next_run_at(february_29, ScheduleFrequency.MONTHLY)

    assert february_29.day == 29
    assert march_29.day == 29
    assert calculate_next_run_at(january_31, ScheduleFrequency.DAILY) == january_31 + timedelta(
        days=1
    )
    assert calculate_next_run_at(january_31, ScheduleFrequency.WEEKLY) == january_31 + timedelta(
        days=7
    )
    with pytest.raises(ValidationError, match="Unsupported schedule frequency"):
        calculate_next_run_at(january_31, "hourly")


def test_scheduled_workflow_skips_paused_or_not_due_runs_and_resumes_future_schedule(
    django_user_model,
):
    owner = make_user(django_user_model, email="schedule-guard@example.com")
    organization = create_organization_for_owner(owner, "Schedule Guard Workspace")
    enable_scheduled_reports(organization)
    workflow = create_scheduled_workflow(
        organization=organization,
        created_by=owner,
        name="Guarded schedule",
        frequency=ScheduleFrequency.DAILY,
        timezone_name="UTC",
        next_run_at=timezone.now() + timedelta(hours=1),
        config={"title": "Guarded report", "template_key": "weekly_summary"},
    )

    assert (
        run_scheduled_workflow(
            workflow,
            trigger=ScheduledRunTrigger.SCHEDULED,
            require_due=True,
        )
        is None
    )

    workflow.status = ScheduledWorkflowStatus.PAUSED
    workflow.next_run_at = timezone.now() - timedelta(days=2)
    workflow.save(update_fields=["status", "next_run_at", "updated_at"])
    assert run_scheduled_workflow(workflow, trigger=ScheduledRunTrigger.SCHEDULED) is None

    set_scheduled_workflow_status(workflow, ScheduledWorkflowStatus.ACTIVE)
    workflow.refresh_from_db()
    assert workflow.status == ScheduledWorkflowStatus.ACTIVE
    assert workflow.next_run_at > timezone.now()


def test_scheduled_workflow_rejects_unsupported_workflow_type(django_user_model):
    owner = make_user(django_user_model, email="unsupported-workflow@example.com")
    organization = create_organization_for_owner(owner, "Unsupported Workflow Workspace")
    enable_scheduled_reports(organization)
    workflow = create_scheduled_workflow(
        organization=organization,
        created_by=owner,
        name="Unsupported schedule",
        frequency=ScheduleFrequency.DAILY,
        timezone_name="UTC",
        next_run_at=timezone.now() - timedelta(minutes=1),
        config={},
    )
    workflow.workflow_type = "unsupported"
    workflow.save(update_fields=["workflow_type", "updated_at"])

    with pytest.raises(ValidationError, match="Unsupported scheduled workflow type"):
        run_scheduled_workflow(workflow, trigger=ScheduledRunTrigger.MANUAL)

    assert not ScheduledRun.objects.filter(workflow=workflow).exists()


def test_free_plan_cannot_create_scheduled_workflow(django_user_model):
    owner = make_user(django_user_model, email="free-schedule@example.com")
    organization = create_organization_for_owner(owner, "Free Schedule Workspace")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/jobs/schedules/",
        {
            "organization_id": organization.id,
            "name": "Weekly KPI schedule",
            "frequency": "weekly",
            "timezone": "UTC",
            "title": "Weekly KPI report",
            "template_key": "weekly_summary",
        },
        format="json",
    )

    assert response.status_code == 403


def test_member_cannot_manage_scheduled_workflows(django_user_model):
    owner = make_user(django_user_model, email="schedule-owner@example.com")
    member = make_user(django_user_model, email="schedule-member@example.com")
    organization = create_organization_for_owner(owner, "Scheduled Workspace")
    enable_scheduled_reports(organization)
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    client = APIClient()
    client.force_authenticate(member)

    response = client.get(f"/api/v1/jobs/schedules/?organization_id={organization.id}")

    assert response.status_code == 403


def test_admin_can_download_database_artifact_and_member_cannot(django_user_model):
    owner = make_user(django_user_model, email="artifact-owner@example.com")
    member = make_user(django_user_model, email="artifact-member@example.com")
    organization = create_organization_for_owner(owner, "Artifact Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    report = Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Downloadable report",
        status=ReportStatus.SUCCEEDED,
    )
    artifact = ReportArtifact.objects.create(
        report=report,
        format="json",
        content={"status": "ready"},
    )
    client = APIClient()
    client.force_authenticate(owner)

    owner_response = client.get(
        f"/api/v1/reports/{report.id}/artifacts/{artifact.id}/download/"
    )
    client.force_authenticate(member)
    member_response = client.get(
        f"/api/v1/reports/{report.id}/artifacts/{artifact.id}/download/"
    )

    assert owner_response.status_code == 200
    assert owner_response["Content-Type"] == "application/json"
    assert "attachment;" in owner_response["Content-Disposition"]
    assert b'"status": "ready"' in owner_response.content
    assert member_response.status_code == 403


@pytest.mark.parametrize(
    ("artifact_format", "content_type", "signature"),
    [
        ("json", "application/json", b'"status": "ready"'),
        ("csv", "text/csv; charset=utf-8", b"key,value"),
        ("html", "text/html; charset=utf-8", b"<!doctype html>"),
        ("pdf", "application/pdf", b"%PDF"),
        (
            "docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            b"PK",
        ),
    ],
)
def test_database_artifact_download_renders_requested_format(
    django_user_model,
    artifact_format,
    content_type,
    signature,
):
    owner = make_user(django_user_model, email=f"{artifact_format}@example.com")
    organization = create_organization_for_owner(owner, f"{artifact_format} Workspace")
    report = Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Rendered report",
        status=ReportStatus.SUCCEEDED,
    )
    artifact = ReportArtifact.objects.create(
        report=report,
        format=artifact_format,
        content={"status": "ready", "metrics": {"revenue": 1000}},
    )

    download = report_artifact_download(artifact)

    assert download["kind"] == "content"
    assert download["content_type"] == content_type
    assert download["filename"].endswith(f".{artifact_format}")
    assert download["content"].startswith(signature) or signature in download["content"]


def test_local_artifact_download_allows_media_file_and_rejects_escape_or_missing_file(
    django_user_model,
    tmp_path,
):
    owner = make_user(django_user_model, email="local-artifact@example.com")
    organization = create_organization_for_owner(owner, "Local Artifact Workspace")
    report = Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Local artifact",
        status=ReportStatus.SUCCEEDED,
    )
    artifact_file = tmp_path / "reports" / "artifact.json"
    artifact_file.parent.mkdir()
    artifact_file.write_text('{"ready": true}', encoding="utf-8")
    artifact = ReportArtifact.objects.create(
        report=report,
        format="json",
        storage_backend="local",
        file_path="reports/artifact.json",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        download = report_artifact_download(artifact)
        assert download["kind"] == "file"
        assert download["path"] == artifact_file

        artifact.file_path = "../outside.json"
        with pytest.raises(ReportArtifactDownloadUnavailable):
            report_artifact_download(artifact)

        artifact.file_path = "reports/missing.json"
        with pytest.raises(ReportArtifactDownloadUnavailable):
            report_artifact_download(artifact)


def test_report_artifact_download_rejects_unconfigured_storage_and_unknown_format(
    django_user_model,
):
    owner = make_user(django_user_model, email="storage-artifact@example.com")
    organization = create_organization_for_owner(owner, "Storage Artifact Workspace")
    report = Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Storage artifact",
        status=ReportStatus.SUCCEEDED,
    )
    artifact = ReportArtifact.objects.create(
        report=report,
        format="json",
        storage_backend="s3",
        file_path="reports/private.json",
    )

    with pytest.raises(ReportArtifactDownloadUnavailable):
        report_artifact_download(artifact)
    with pytest.raises(ValidationError, match="Unsupported report artifact format"):
        render_report_artifact(format="xml", content={}, title="Unsupported")


def test_generate_report_task_keeps_report_queued_during_retry(
    django_user_model,
    monkeypatch,
):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    template = ReportTemplate.objects.get(key="weekly_summary")
    report = Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Retrying Report",
        template=template,
        input_payload={"metrics": {"revenue": 1000}},
    )
    job_run = create_job_run(
        organization=organization,
        created_by=owner,
        name="Generate report",
        task_name="apps.reports.tasks.generate_report_task",
        related_entity_type="report",
        related_entity_id=str(report.id),
        metadata={"report_id": report.id, "template_key": template.key},
    )

    def raise_transient_failure(**_kwargs):
        raise RuntimeError("Transient provider failure")

    monkeypatch.setattr("apps.reports.tasks.create_report_artifact", raise_transient_failure)

    with pytest.raises(RuntimeError, match="Transient provider failure"):
        generate_report_task(report.id, job_run.id)

    report.refresh_from_db()
    job_run.refresh_from_db()
    assert report.status == ReportStatus.QUEUED
    assert report.error_message == "Transient provider failure"
    assert report.completed_at is None
    assert job_run.status == JobRunStatus.RETRYING


def test_generate_report_task_marks_report_failed_after_retry_budget_is_exhausted(
    django_user_model,
    monkeypatch,
):
    owner = make_user(django_user_model, email="final-failure@example.com")
    organization = create_organization_for_owner(owner, "Final Failure Workspace")
    template = ReportTemplate.objects.get(key="weekly_summary")
    report = Report.objects.create(
        organization=organization,
        created_by=owner,
        title="Failed Report",
        template=template,
        input_payload={"metrics": {"revenue": 1000}},
    )
    job_run = create_job_run(
        organization=organization,
        created_by=owner,
        name="Generate report",
        task_name="apps.reports.tasks.generate_report_task",
        max_attempts=1,
    )
    monkeypatch.setattr(
        "apps.reports.tasks.create_report_artifact",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("Permanent provider failure")),
    )

    with pytest.raises(RuntimeError, match="Permanent provider failure"):
        generate_report_task(report.id, job_run.id)

    report.refresh_from_db()
    job_run.refresh_from_db()
    assert report.status == ReportStatus.FAILED
    assert report.error_message == "Permanent provider failure"
    assert report.completed_at is not None
    assert job_run.status == JobRunStatus.FAILED
    assert job_run.attempts == 1


def test_job_run_failure_marks_retrying_until_attempts_are_exhausted(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    job_run = create_job_run(
        organization=organization,
        created_by=owner,
        name="Test job",
        task_name="tests.example",
        max_attempts=2,
    )

    mark_job_started(job_run)
    mark_job_failed(job_run, "Temporary failure", retryable=True)

    assert job_run.status == JobRunStatus.RETRYING
    assert job_run.last_error == "Temporary failure"

    mark_job_started(job_run)
    mark_job_failed(job_run, "Still failing", retryable=True)

    assert job_run.status == JobRunStatus.FAILED
    assert job_run.last_error == "Still failing"


def test_disabled_notification_preference_skips_delivery(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    report, _job_run = create_report_request(
        organization=organization,
        created_by=owner,
        title="Weekly KPI Summary",
        template_key="weekly_summary",
    )
    upsert_notification_preference(
        organization=organization,
        user=owner,
        event="report_ready",
        channel="email",
        is_enabled=False,
    )

    delivery_log = send_report_ready_notification(report)

    assert delivery_log.status == NotificationDeliveryStatus.SKIPPED
    assert "disabled" in delivery_log.error_message


@override_settings(EMAIL_PROVIDER="resend")
def test_unconfigured_email_and_webhook_notifications_fail_descriptively(django_user_model):
    owner = make_user(django_user_model, email="notification-provider@example.com")
    organization = create_organization_for_owner(owner, "Notification Provider Workspace")

    email_log = send_notification(
        organization=organization,
        user=owner,
        event=NotificationEvent.SYSTEM_ALERT,
        channel=NotificationChannel.EMAIL,
        recipient=owner.email,
        subject="Email alert",
    )
    webhook_log = send_notification(
        organization=organization,
        user=owner,
        event=NotificationEvent.SYSTEM_ALERT,
        channel=NotificationChannel.WEBHOOK,
        subject="Webhook alert",
    )

    assert email_log.status == NotificationDeliveryStatus.FAILED
    assert "resend" in email_log.error_message
    assert webhook_log.status == NotificationDeliveryStatus.FAILED
    assert "not configured" in webhook_log.error_message


def test_in_app_notification_requires_user_and_sanitizes_external_target(django_user_model):
    owner = make_user(django_user_model, email="safe-target@example.com")
    organization = create_organization_for_owner(owner, "Safe Target Workspace")

    with pytest.raises(ValueError, match="require a target user"):
        create_in_app_notification(
            organization=organization,
            user=None,
            event=NotificationEvent.SYSTEM_ALERT,
            title="Missing user",
        )

    notification = create_in_app_notification(
        organization=organization,
        user=owner,
        event=NotificationEvent.SYSTEM_ALERT,
        title="Unsafe target",
        target_url="https://evil.example/phishing",
    )
    assert notification.target_url == ""


def test_user_notification_preference_overrides_organization_default(django_user_model):
    owner = make_user(django_user_model, email="preference@example.com")
    organization = create_organization_for_owner(owner, "Preference Workspace")
    upsert_notification_preference(
        organization=organization,
        event=NotificationEvent.SYSTEM_ALERT,
        channel=NotificationChannel.EMAIL,
        is_enabled=False,
    )
    assert (
        notification_is_enabled(
            organization=organization,
            user=owner,
            event=NotificationEvent.SYSTEM_ALERT,
            channel=NotificationChannel.EMAIL,
        )
        is False
    )

    upsert_notification_preference(
        organization=organization,
        user=owner,
        event=NotificationEvent.SYSTEM_ALERT,
        channel=NotificationChannel.EMAIL,
        is_enabled=True,
    )
    assert (
        notification_is_enabled(
            organization=organization,
            user=owner,
            event=NotificationEvent.SYSTEM_ALERT,
            channel=NotificationChannel.EMAIL,
        )
        is True
    )


def test_member_can_only_update_own_notification_preference(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    other_member = make_user(django_user_model, email="other-member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    for user in (member, other_member):
        Membership.objects.create(
            organization=organization,
            user=user,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
    client = APIClient()
    client.force_authenticate(member)
    base_payload = {
        "organization_id": organization.id,
        "event": NotificationEvent.REPORT_READY,
        "channel": NotificationChannel.EMAIL,
        "is_enabled": False,
    }

    org_wide_response = client.post(
        "/api/v1/notifications/preferences/",
        base_payload,
        format="json",
    )
    other_user_response = client.post(
        "/api/v1/notifications/preferences/",
        {**base_payload, "user_id": other_member.id},
        format="json",
    )
    own_response = client.post(
        "/api/v1/notifications/preferences/",
        {**base_payload, "user_id": member.id},
        format="json",
    )

    assert org_wide_response.status_code == 403
    assert other_user_response.status_code == 403
    assert own_response.status_code == 200
    assert NotificationPreference.objects.get(
        organization=organization,
        user=member,
        event=NotificationEvent.REPORT_READY,
        channel=NotificationChannel.EMAIL,
    ).is_enabled is False


def test_member_can_list_and_mark_only_own_in_app_notifications(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    other_member = make_user(django_user_model, email="other-member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    for user in (member, other_member):
        Membership.objects.create(
            organization=organization,
            user=user,
            role=MembershipRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        )
    member_log = send_notification(
        organization=organization,
        user=member,
        event=NotificationEvent.SYSTEM_ALERT,
        channel=NotificationChannel.IN_APP,
        subject="Member alert",
        payload={"message": "Visible to member", "target_url": "/dashboard"},
    )
    send_notification(
        organization=organization,
        user=other_member,
        event=NotificationEvent.SYSTEM_ALERT,
        channel=NotificationChannel.IN_APP,
        subject="Other alert",
    )
    member_notification = InAppNotification.objects.get(
        user=member,
        id=int(member_log.provider_message_id.removeprefix("in-app-")),
    )
    other_notification = InAppNotification.objects.get(user=other_member)
    client = APIClient()
    client.force_authenticate(member)

    list_response = client.get(
        f"/api/v1/notifications/in-app/?organization_id={organization.id}"
    )
    other_read_response = client.post(
        f"/api/v1/notifications/in-app/{other_notification.id}/read/",
        {},
        format="json",
    )
    read_response = client.post(
        f"/api/v1/notifications/in-app/{member_notification.id}/read/",
        {},
        format="json",
    )

    assert list_response.status_code == 200
    assert [item["title"] for item in list_response.json()["results"]] == ["Member alert"]
    assert other_read_response.status_code == 404
    assert read_response.status_code == 200
    member_notification.refresh_from_db()
    assert member_notification.is_read is True
    assert member_notification.read_at is not None


def test_member_can_mark_all_own_in_app_notifications_read(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    for index in range(2):
        send_notification(
            organization=organization,
            user=owner,
            event=NotificationEvent.SYSTEM_ALERT,
            channel=NotificationChannel.IN_APP,
            subject=f"Alert {index}",
        )
    client = APIClient()
    client.force_authenticate(owner)

    response = client.post(
        "/api/v1/notifications/in-app/read-all/",
        {"organization_id": organization.id},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["updated"] == 2
    assert not InAppNotification.objects.filter(user=owner, is_read=False).exists()


def test_member_cannot_list_sensitive_job_or_notification_logs(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    create_job_run(
        organization=organization,
        created_by=owner,
        name="Sensitive job",
        task_name="tests.example",
    )
    NotificationDeliveryLog.objects.create(
        organization=organization,
        user=owner,
        event=NotificationEvent.REPORT_READY,
        channel=NotificationChannel.EMAIL,
        recipient="owner@example.com",
        subject="Private report",
        payload={"private": True},
    )
    client = APIClient()
    client.force_authenticate(member)

    jobs_response = client.get(f"/api/v1/jobs/?organization_id={organization.id}")
    delivery_logs_response = client.get(
        f"/api/v1/notifications/delivery-logs/?organization_id={organization.id}"
    )

    assert jobs_response.status_code == 403
    assert delivery_logs_response.status_code == 403


def test_report_and_job_lists_are_organization_scoped(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    other = make_user(django_user_model, email="other@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    other_organization = create_organization_for_owner(other, "Other Workspace")
    create_report_request(
        organization=organization,
        created_by=owner,
        title="Owner Report",
        template_key="weekly_summary",
    )
    create_report_request(
        organization=other_organization,
        created_by=other,
        title="Other Report",
        template_key="weekly_summary",
    )
    client = APIClient()
    client.force_authenticate(owner)

    reports_response = client.get(f"/api/v1/reports/?organization_id={organization.id}")
    jobs_response = client.get(f"/api/v1/jobs/?organization_id={organization.id}")

    assert reports_response.status_code == 200
    assert reports_response.json()["count"] == 1
    assert reports_response.json()["results"][0]["title"] == "Owner Report"
    assert jobs_response.status_code == 200
    assert jobs_response.json()["count"] == 1


def test_report_sensitive_payloads_require_admin_role(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    member = make_user(django_user_model, email="member@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    Membership.objects.create(
        organization=organization,
        user=member,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    )
    report, _job_run = create_report_request(
        organization=organization,
        created_by=owner,
        title="Sensitive Report",
        template_key="weekly_summary",
        input_payload={"private": "input"},
    )
    ReportArtifact.objects.create(
        report=report,
        format="json",
        content={"private": "artifact"},
        file_path="s3://private/report.json",
        metadata={"private": True},
    )
    client = APIClient()
    client.force_authenticate(member)

    list_response = client.get(f"/api/v1/reports/?organization_id={organization.id}")
    detail_response = client.get(f"/api/v1/reports/{report.id}/")
    artifacts_response = client.get(f"/api/v1/reports/{report.id}/artifacts/")

    assert list_response.status_code == 200
    listed_report = list_response.json()["results"][0]
    assert listed_report["title"] == "Sensitive Report"
    assert "input_payload" not in listed_report
    assert "result_summary" not in listed_report
    assert "error_message" not in listed_report
    assert detail_response.status_code == 403
    assert artifacts_response.status_code == 403
