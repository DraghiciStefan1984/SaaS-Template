import os

from django.core.management.base import BaseCommand, CommandError

UNSAFE_SECRET = "unsafe-local-development-key-change-me-before-production"

BASE_REQUIRED_ENV = (
    "DJANGO_SETTINGS_MODULE",
    "DJANGO_SECRET_KEY",
    "INTEGRATION_CREDENTIALS_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "CORS_ALLOWED_ORIGINS",
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "FRONTEND_BASE_URL",
    "AWS_REGION",
)

BILLING_REQUIRED_ENV = (
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
)

AI_REQUIRED_ENV = (
    "DEFAULT_AI_PROVIDER",
    "OPENAI_API_KEY",
)

EMAIL_REQUIRED_ENV = (
    "EMAIL_PROVIDER",
    "DEFAULT_FROM_EMAIL",
)

STORAGE_REQUIRED_ENV = (
    "AWS_STORAGE_BUCKET_NAME",
)

OBSERVABILITY_REQUIRED_ENV = (
    "ENVIRONMENT",
    "DEPLOY_VERSION",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "SENTRY_DSN",
)

PUBLIC_URL_ENV = (
    "DJANGO_ALLOWED_HOSTS",
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "CORS_ALLOWED_ORIGINS",
    "FRONTEND_BASE_URL",
)


class Command(BaseCommand):
    help = "Validate environment variables required before deploying a SaaS environment."

    def add_arguments(self, parser):
        parser.add_argument(
            "--environment",
            choices=("staging", "production"),
            default="staging",
        )
        parser.add_argument("--require-billing", action="store_true")
        parser.add_argument("--require-ai", action="store_true")
        parser.add_argument("--require-email", action="store_true")
        parser.add_argument("--require-storage", action="store_true")
        parser.add_argument("--require-observability", action="store_true")

    def handle(self, *args, **options):
        environment = options["environment"]
        required_names = list(BASE_REQUIRED_ENV)
        required_names += list(BILLING_REQUIRED_ENV) if options["require_billing"] else []
        required_names += list(AI_REQUIRED_ENV) if options["require_ai"] else []
        required_names += list(EMAIL_REQUIRED_ENV) if options["require_email"] else []
        required_names += list(STORAGE_REQUIRED_ENV) if options["require_storage"] else []
        required_names += (
            list(OBSERVABILITY_REQUIRED_ENV) if options["require_observability"] else []
        )

        failures = []
        for name in required_names:
            value = os.environ.get(name, "")
            failure = self.validate_value(name, value, environment)
            if failure:
                failures.append(f"- {name}: {failure}")

        if os.environ.get("DJANGO_DEBUG", "").lower() in {"1", "true", "yes", "on"}:
            failures.append("- DJANGO_DEBUG: must not be true outside local development.")
        if os.environ.get("INTEGRATION_CREDENTIALS_KEY") == os.environ.get("DJANGO_SECRET_KEY"):
            failures.append(
                "- INTEGRATION_CREDENTIALS_KEY: must be distinct from DJANGO_SECRET_KEY."
            )

        if failures:
            raise CommandError(
                "Deploy readiness failed for "
                f"{environment}. Missing or unsafe values:\n" + "\n".join(failures)
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Deploy readiness passed for {environment}. No external APIs were called."
            )
        )

    def validate_value(self, name, value, environment):
        if not value:
            return "missing"

        normalized = value.lower()
        if "change-me" in normalized or "todo" in normalized:
            return "placeholder value"
        if name == "DJANGO_SECRET_KEY" and value == UNSAFE_SECRET:
            return "unsafe local default secret"
        if name == "DJANGO_SETTINGS_MODULE" and value != "config.settings.production":
            return "must be config.settings.production for staging/production deploys"
        if name == "DJANGO_ALLOWED_HOSTS" and "*" in [item.strip() for item in value.split(",")]:
            return "wildcard hosts are not allowed"
        if environment == "production" and name in PUBLIC_URL_ENV:
            if "localhost" in normalized or "127.0.0.1" in normalized:
                return "local URL/host is not allowed in production"
        if environment == "production" and name == "DEFAULT_FROM_EMAIL":
            if normalized.endswith("@example.com"):
                return "example.com sender is not allowed in production"
        if environment == "production" and name == "DEPLOY_VERSION" and value == "local":
            return "local deploy version is not allowed in production"
        if environment == "production" and name == "LOG_FORMAT" and value != "json":
            return "production logs must use json format"
        return ""
