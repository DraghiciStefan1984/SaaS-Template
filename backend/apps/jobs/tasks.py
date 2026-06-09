import logging

from celery import shared_task
from django.utils import timezone

from .models import ScheduledRunTrigger, ScheduledWorkflow, ScheduledWorkflowStatus
from .services import run_scheduled_workflow

logger = logging.getLogger(__name__)


@shared_task(name="apps.jobs.tasks.dispatch_due_scheduled_workflows")
def dispatch_due_scheduled_workflows():
    workflow_ids = list(
        ScheduledWorkflow.objects.filter(
            status=ScheduledWorkflowStatus.ACTIVE,
            next_run_at__lte=timezone.now(),
        ).values_list("id", flat=True)
    )
    dispatched = 0
    failed = 0
    for workflow_id in workflow_ids:
        try:
            scheduled_run = run_scheduled_workflow(
                ScheduledWorkflow.objects.get(id=workflow_id),
                trigger=ScheduledRunTrigger.SCHEDULED,
                require_due=True,
            )
        except Exception:
            failed += 1
            logger.exception(
                "Scheduled workflow dispatch failed",
                extra={"workflow_id": workflow_id},
            )
            continue
        if scheduled_run is not None:
            dispatched += 1
    return {"due": len(workflow_ids), "dispatched": dispatched, "failed": failed}
