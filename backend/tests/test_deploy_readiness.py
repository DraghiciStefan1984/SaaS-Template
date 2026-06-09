from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

BASE_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "prod-secret-key-with-enough-length",
    "INTEGRATION_CREDENTIALS_KEY": "integration-secret-key-with-enough-length",
    "DJANGO_ALLOWED_HOSTS": "api.staging.example.test",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://app.staging.example.test",
    "CORS_ALLOWED_ORIGINS": "https://app.staging.example.test",
    "DATABASE_URL": "postgres://user:password@db.example.test:5432/app",
    "REDIS_URL": "redis://redis.example.test:6379/0",
    "CELERY_BROKER_URL": "redis://redis.example.test:6379/0",
    "CELERY_RESULT_BACKEND": "redis://redis.example.test:6379/1",
    "FRONTEND_BASE_URL": "https://app.staging.example.test",
    "AWS_REGION": "eu-central-1",
}


def clear_relevant_env(monkeypatch):
    for key in {
        *BASE_ENV.keys(),
        "DJANGO_DEBUG",
        "ENVIRONMENT",
        "DEPLOY_VERSION",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "SENTRY_DSN",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "GOOGLE_OAUTH_CLIENT_ID",
    }:
        monkeypatch.delenv(key, raising=False)


def set_base_env(monkeypatch):
    clear_relevant_env(monkeypatch)
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)


def test_check_deploy_ready_fails_when_base_env_is_missing(monkeypatch):
    clear_relevant_env(monkeypatch)

    with pytest.raises(CommandError) as exc:
        call_command("check_deploy_ready")

    assert "DJANGO_SECRET_KEY" in str(exc.value)
    assert "DATABASE_URL" in str(exc.value)


def test_check_deploy_ready_passes_for_complete_staging_base_env(monkeypatch):
    stdout = StringIO()
    set_base_env(monkeypatch)

    call_command("check_deploy_ready", stdout=stdout)

    assert "Deploy readiness passed for staging" in stdout.getvalue()


def test_check_deploy_ready_requires_stripe_when_billing_is_enabled(monkeypatch):
    set_base_env(monkeypatch)

    with pytest.raises(CommandError) as exc:
        call_command("check_deploy_ready", require_billing=True)

    assert "STRIPE_SECRET_KEY" in str(exc.value)
    assert "STRIPE_WEBHOOK_SECRET" in str(exc.value)


def test_check_deploy_ready_requires_distinct_integration_credentials_key(monkeypatch):
    set_base_env(monkeypatch)
    monkeypatch.setenv("INTEGRATION_CREDENTIALS_KEY", BASE_ENV["DJANGO_SECRET_KEY"])

    with pytest.raises(CommandError) as exc:
        call_command("check_deploy_ready")

    assert "INTEGRATION_CREDENTIALS_KEY" in str(exc.value)
    assert "distinct from DJANGO_SECRET_KEY" in str(exc.value)


def test_check_deploy_ready_rejects_local_urls_for_production(monkeypatch):
    set_base_env(monkeypatch)
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:5173")

    with pytest.raises(CommandError) as exc:
        call_command("check_deploy_ready", environment="production")

    assert "FRONTEND_BASE_URL" in str(exc.value)
    assert "local URL/host" in str(exc.value)


def test_check_deploy_ready_requires_observability_values_when_enabled(monkeypatch):
    set_base_env(monkeypatch)

    with pytest.raises(CommandError) as exc:
        call_command("check_deploy_ready", require_observability=True)

    assert "SENTRY_DSN" in str(exc.value)
    assert "DEPLOY_VERSION" in str(exc.value)


def test_check_deploy_ready_requires_google_client_id_when_enabled(monkeypatch):
    set_base_env(monkeypatch)

    with pytest.raises(CommandError) as exc:
        call_command("check_deploy_ready", require_google_login=True)

    assert "GOOGLE_OAUTH_CLIENT_ID" in str(exc.value)


def test_check_deploy_ready_accepts_production_observability_values(monkeypatch):
    stdout = StringIO()
    set_base_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEPLOY_VERSION", "release-1")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FORMAT", "json")
    monkeypatch.setenv("SENTRY_DSN", "https://public@example.ingest.sentry.io/1")

    call_command(
        "check_deploy_ready",
        environment="production",
        require_observability=True,
        stdout=stdout,
    )

    assert "Deploy readiness passed for production" in stdout.getvalue()
