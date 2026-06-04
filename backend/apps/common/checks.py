from django.conf import settings
from django.core.checks import Critical, Warning, register

UNSAFE_SECRET_KEY = "unsafe-local-development-key-change-me-before-production"


@register()
def production_security_settings_check(app_configs, **kwargs):
    if settings.DEBUG:
        return []

    issues = []
    if settings.SECRET_KEY == UNSAFE_SECRET_KEY:
        issues.append(
            Critical(
                "DJANGO_SECRET_KEY is using the unsafe local default.",
                id="saas.E001",
            )
        )
    if not settings.ALLOWED_HOSTS:
        issues.append(
            Critical(
                "DJANGO_ALLOWED_HOSTS must be set outside local development.",
                id="saas.E002",
            )
        )
    if "*" in settings.ALLOWED_HOSTS:
        issues.append(
            Warning(
                "DJANGO_ALLOWED_HOSTS contains '*'. Use explicit hosts in production.",
                id="saas.W001",
            )
        )
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        issues.append(
            Warning(
                "DJANGO_SECURE_SSL_REDIRECT is disabled.",
                id="saas.W002",
            )
        )
    if not getattr(settings, "SESSION_COOKIE_SECURE", False):
        issues.append(
            Warning(
                "SESSION_COOKIE_SECURE is disabled.",
                id="saas.W003",
            )
        )
    if not getattr(settings, "CSRF_COOKIE_SECURE", False):
        issues.append(
            Warning(
                "CSRF_COOKIE_SECURE is disabled.",
                id="saas.W004",
            )
        )
    if getattr(settings, "INTEGRATION_CREDENTIALS_KEY", "") == settings.SECRET_KEY:
        issues.append(
            Warning(
                "INTEGRATION_CREDENTIALS_KEY should be distinct from DJANGO_SECRET_KEY.",
                id="saas.W005",
            )
        )
    if getattr(settings, "EMAIL_PROVIDER", "console") == "console":
        issues.append(
            Warning(
                "EMAIL_PROVIDER is set to console. "
                "Configure SES/Resend/Postmark before production.",
                id="saas.W006",
            )
        )
    return issues
