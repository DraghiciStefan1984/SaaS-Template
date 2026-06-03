import pytest
from rest_framework.test import APIClient

from apps.ai.models import AIModelDecisionLog
from apps.jobs.models import JobRun, JobRunStatus
from apps.jobs.services import create_job_run, mark_job_failed, mark_job_started
from apps.notifications.models import NotificationDeliveryLog, NotificationDeliveryStatus
from apps.notifications.services import (
    send_report_ready_notification,
    upsert_notification_preference,
)
from apps.organizations.services import create_organization_for_owner
from apps.reports.models import Report, ReportArtifact, ReportStatus, ReportTemplate
from apps.reports.services import create_report_request
from apps.reports.tasks import generate_report_task

pytestmark = pytest.mark.django_db


def make_user(django_user_model, email="user@example.com", password="SaaSCore!23456", **extra):
    return django_user_model.objects.create_user(email=email, password=password, **extra)


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


def test_generate_report_task_creates_artifact_ai_decision_and_notification(django_user_model):
    owner = make_user(django_user_model, email="owner@example.com")
    organization = create_organization_for_owner(owner, "Owner Workspace")
    report, job_run = create_report_request(
        organization=organization,
        created_by=owner,
        title="Weekly KPI Summary",
        template_key="weekly_summary",
        input_payload={"metrics": {"revenue": 1000}},
    )

    result = generate_report_task(report.id, job_run.id)

    report.refresh_from_db()
    job_run.refresh_from_db()
    assert report.status == ReportStatus.SUCCEEDED
    assert job_run.status == JobRunStatus.SUCCEEDED
    assert result["report_id"] == report.id
    artifact = ReportArtifact.objects.get(report=report)
    assert artifact.content["status"] == "placeholder"
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
