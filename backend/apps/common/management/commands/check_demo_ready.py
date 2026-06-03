from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from rest_framework.test import APIClient


class Command(BaseCommand):
    help = "Check that the seeded local demo can be used through the API."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@example.com")
        parser.add_argument("--password", default="SaaSCore!23456")
        parser.add_argument("--organization", default="Demo Workspace")
        parser.add_argument(
            "--seed",
            action="store_true",
            help="Run seed_dev_data before checking the demo API flow.",
        )
        parser.add_argument(
            "--migrate",
            action="store_true",
            help="Run database migrations before seeding or checking the demo API flow.",
        )

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]
        organization_name = options["organization"]
        checks = []

        if options["migrate"]:
            call_command("migrate", interactive=False, stdout=self.stdout)

        if options["seed"]:
            call_command(
                "seed_dev_data",
                email=email,
                password=password,
                organization=organization_name,
                stdout=self.stdout,
            )

        client = APIClient(HTTP_HOST="localhost")
        health = self._get(client, "/api/v1/health/", "health")
        self._require(health.get("status") == "ok", "Health endpoint is not healthy.")
        checks.append("health endpoint")

        liveness = self._get(client, "/api/v1/health/live/", "liveness")
        self._require(liveness.get("status") == "alive", "Liveness endpoint is not healthy.")
        checks.append("liveness endpoint")

        readiness = self._get(client, "/api/v1/health/ready/", "readiness")
        self._require(readiness.get("status") == "ready", "Readiness endpoint is not ready.")
        checks.append("readiness endpoint")

        plans = self._get(client, "/api/v1/billing/plans/", "billing plans")
        self._require(
            any(plan.get("slug") == "free" for plan in plans),
            "Demo requires the default free plan.",
        )
        checks.append("public billing plans")

        login = self._post(
            client,
            "/api/v1/auth/login/",
            {"email": email, "password": password},
            "demo login",
        )
        tokens = login.get("tokens") or login
        access_token = tokens.get("access")
        self._require(access_token, "Login response did not include an access token.")
        self._require(
            login.get("user", {}).get("email") == email,
            "Login response user does not match the demo email.",
        )
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        checks.append("demo login")

        organizations = self._results(
            self._get(client, "/api/v1/organizations/", "organizations"),
            "organizations",
        )
        organization = next(
            (
                item
                for item in organizations
                if item.get("name") == organization_name
            ),
            None,
        )
        self._require(organization is not None, "Demo organization was not found.")
        organization_id = organization["id"]
        checks.append("demo organization")

        subscription = self._get(
            client,
            f"/api/v1/billing/subscription/?organization_id={organization_id}",
            "subscription",
        )
        self._require(
            subscription.get("organization") == organization_id,
            "Subscription does not belong to the demo organization.",
        )
        self._require(subscription.get("plan"), "Demo subscription has no plan.")
        checks.append("subscription")

        usage = self._get(
            client,
            f"/api/v1/usage/summary/?organization_id={organization_id}",
            "usage summary",
        )
        self._require(
            any(metric.get("metric_name") == "one_click_requests" for metric in usage["metrics"]),
            "Usage summary is missing one_click_requests.",
        )
        checks.append("usage summary")

        ai_profiles = self._results(
            self._get(client, "/api/v1/ai/task-profiles/", "AI task profiles"),
            "AI task profiles",
        )
        self._require(
            any(profile.get("key") == "table_analysis" for profile in ai_profiles),
            "AI task profiles are missing table_analysis.",
        )
        checks.append("AI task profiles")

        ai_decisions = self._results(
            self._get(
                client,
                f"/api/v1/ai/decision-logs/?organization_id={organization_id}",
                "AI decision logs",
            ),
            "AI decision logs",
        )
        self._require(
            any(
                decision.get("task_key") == "table_analysis"
                and decision.get("selected_strategy") == "classic_ml"
                for decision in ai_decisions
            ),
            "AI decision logs do not include the seeded classic_ml table analysis.",
        )
        checks.append("AI decision logs")

        integration_providers = self._get(
            client,
            "/api/v1/integrations/providers/",
            "integration providers",
        )
        self._require(integration_providers, "No integration providers are configured.")
        checks.append("integration providers")

        example_requests = self._results(
            self._get(
                client,
                f"/api/v1/products/example-insights/requests/?organization_id={organization_id}",
                "example product requests",
            ),
            "example product requests",
        )
        insight_request = next(
            (
                item
                for item in example_requests
                if item.get("title") == "Demo Table Insight"
            ),
            None,
        )
        self._require(insight_request is not None, "Seeded example product request was not found.")
        self._require(
            insight_request.get("ai_execution_plan", {}).get("strategy") == "classic_ml",
            "Seeded example product request should use classic_ml.",
        )
        checks.append("example product request")

        reports = self._results(
            self._get(
                client,
                f"/api/v1/reports/?organization_id={organization_id}",
                "reports",
            ),
            "reports",
        )
        self._require(
            any(report.get("id") == insight_request.get("report") for report in reports),
            "Seeded report was not found.",
        )
        checks.append("reports")

        jobs = self._results(
            self._get(
                client,
                f"/api/v1/jobs/?organization_id={organization_id}",
                "jobs",
            ),
            "jobs",
        )
        self._require(
            any(job.get("id") == insight_request.get("job_run") for job in jobs),
            "Seeded job run was not found.",
        )
        checks.append("jobs")

        preferences = self._results(
            self._get(
                client,
                f"/api/v1/notifications/preferences/?organization_id={organization_id}",
                "notification preferences",
            ),
            "notification preferences",
        )
        self._require(
            any(
                preference.get("event") == "report_ready"
                and preference.get("channel") == "email"
                for preference in preferences
            ),
            "Seeded report_ready email notification preference was not found.",
        )
        checks.append("notification preferences")

        delivery_logs = self._results(
            self._get(
                client,
                f"/api/v1/notifications/delivery-logs/?organization_id={organization_id}",
                "notification delivery logs",
            ),
            "notification delivery logs",
        )
        self._require(
            any(log.get("subject") == "Demo notification: report ready" for log in delivery_logs),
            "Seeded notification delivery log was not found.",
        )
        checks.append("notification delivery logs")

        self._results(
            self._get(
                client,
                f"/api/v1/audit/logs/?organization_id={organization_id}",
                "audit logs",
            ),
            "audit logs",
        )
        checks.append("audit logs endpoint")

        self.stdout.write(self.style.SUCCESS("Demo ready. Checked:"))
        for check in checks:
            self.stdout.write(f"- {check}")

    def _get(self, client, path, label):
        return self._assert_ok(client.get(path), label)

    def _post(self, client, path, data, label):
        return self._assert_ok(client.post(path, data, format="json"), label)

    def _assert_ok(self, response, label):
        if response.status_code != 200:
            payload = getattr(response, "data", None)
            raise CommandError(
                f"{label} returned {response.status_code}; expected 200. Payload: {payload}"
            )
        return self._payload(response, label)

    def _payload(self, response, label):
        payload = getattr(response, "data", None)
        if payload is not None:
            return payload
        try:
            return response.json()
        except ValueError as exc:
            raise CommandError(f"{label} did not return JSON.") from exc

    def _results(self, payload, label):
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("results"), list):
            return payload["results"]
        raise CommandError(f"{label} response is not a list or paginated result.")

    def _require(self, condition, message):
        if not condition:
            raise CommandError(message)
