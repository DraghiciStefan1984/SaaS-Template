from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.ai.services import sanitize_constraints, select_ai_execution_plan
from apps.billing.services import assert_feature_enabled
from apps.reports.services import create_report_request
from apps.usage.services import check_and_record_usage

from .models import ExampleInsightRequest, ExampleInsightStatus

EXAMPLE_INSIGHTS_PRODUCT_SCOPE = "example_insights"
EXAMPLE_INSIGHTS_USAGE_METRIC = "one_click_requests"
EXAMPLE_INSIGHTS_FEATURE = "example_insights"


@transaction.atomic
def create_example_insight_request(
    *,
    organization,
    created_by,
    title,
    input_payload=None,
    constraints=None,
):
    input_payload = input_payload or {}
    constraints = constraints or {}
    if not isinstance(input_payload, dict):
        raise ValidationError({"input_payload": "Expected a JSON object."})
    if not isinstance(constraints, dict):
        raise ValidationError({"constraints": "Expected a JSON object."})
    public_constraints = sanitize_constraints(constraints)
    server_constraints = {
        **public_constraints,
        "can_use_classic_ml": True,
    }

    assert_feature_enabled(organization, EXAMPLE_INSIGHTS_FEATURE)
    usage_record = check_and_record_usage(
        organization,
        EXAMPLE_INSIGHTS_USAGE_METRIC,
        quantity=1,
        source="example_insights.create_request",
        product_scope=EXAMPLE_INSIGHTS_PRODUCT_SCOPE,
        metadata={"status": "reserved"},
    )

    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=created_by,
        task_key="table_analysis",
        input_payload=input_payload,
        constraints=server_constraints,
        metadata={
            "product_scope": EXAMPLE_INSIGHTS_PRODUCT_SCOPE,
        },
        log_decision=True,
        trusted_constraints=True,
    )
    report, job_run = create_report_request(
        organization=organization,
        created_by=created_by,
        title=title,
        template_key="table_analysis",
        requested_format="json",
        input_payload={
            "product_scope": EXAMPLE_INSIGHTS_PRODUCT_SCOPE,
            "source_payload": input_payload,
            "ai_constraints": constraints,
        },
        related_entity_type="example_insight_request",
    )

    insight_request = ExampleInsightRequest.objects.create(
        organization=organization,
        created_by=created_by,
        report=report,
        job_run=job_run,
        title=title,
        status=ExampleInsightStatus.PLANNED,
        input_payload=input_payload,
        constraints=constraints,
        ai_execution_plan=execution_plan,
    )
    report.related_entity_id = str(insight_request.id)
    report.save(update_fields=["related_entity_id", "updated_at"])

    usage_record.metadata = {
        "insight_request_id": insight_request.id,
        "report_id": report.id,
        "job_run_id": job_run.id,
        "strategy": execution_plan["strategy"],
    }
    usage_record.save(update_fields=["metadata"])
    return insight_request
