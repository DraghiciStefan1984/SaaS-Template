from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

ENVIRONMENT = env("ENVIRONMENT", default="local")
DEPLOY_VERSION = env("DEPLOY_VERSION", default="local")

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="unsafe-local-development-key-change-me-before-production",
)
INTEGRATION_CREDENTIALS_KEY = env("INTEGRATION_CREDENTIALS_KEY", default=SECRET_KEY)
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "apps.accounts.apps.AccountsConfig",
    "apps.organizations.apps.OrganizationsConfig",
    "apps.billing.apps.BillingConfig",
    "apps.usage.apps.UsageConfig",
    "apps.integrations.apps.IntegrationsConfig",
    "apps.ai.apps.AiConfig",
    "apps.jobs.apps.JobsConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.privacy.apps.PrivacyConfig",
    "apps.products.example_insights.apps.ExampleInsightsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.common.apps.CommonConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.common.middleware.RequestIDMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_USER_MODEL = "accounts.User"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="sqlite:///db.sqlite3",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.AccountStatusJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_THROTTLE_ANON", default="100/hour"),
        "user": env("DRF_THROTTLE_USER", default="2000/hour"),
        "auth": env("DRF_THROTTLE_AUTH", default="20/minute"),
        "expensive_action": env("DRF_THROTTLE_EXPENSIVE_ACTION", default="60/hour"),
        "billing_action": env("DRF_THROTTLE_BILLING_ACTION", default="30/hour"),
        "product_write": env("DRF_THROTTLE_PRODUCT_WRITE", default="120/hour"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}
AUTH_REFRESH_COOKIE_NAME = env("AUTH_REFRESH_COOKIE_NAME", default="saas_core_refresh_token")
AUTH_REFRESH_COOKIE_PATH = env("AUTH_REFRESH_COOKIE_PATH", default="/api/v1/auth/")
AUTH_REFRESH_COOKIE_DOMAIN = env("AUTH_REFRESH_COOKIE_DOMAIN", default="")
AUTH_REFRESH_COOKIE_SECURE = env.bool("AUTH_REFRESH_COOKIE_SECURE", default=not DEBUG)
AUTH_REFRESH_COOKIE_SAMESITE = env("AUTH_REFRESH_COOKIE_SAMESITE", default="Lax")

SPECTACULAR_SETTINGS = {
    "TITLE": "SaaS Core Template API",
    "DESCRIPTION": "API-first reusable foundation for AI-powered SaaS products.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "UserAccountStatusEnum": "apps.accounts.models.UserAccountStatus.choices",
        "AuditEventStatusEnum": "apps.audit.models.AuditEventStatus.choices",
        "AIExecutionStrategyEnum": "apps.ai.models.AIExecutionStrategy.choices",
        "AIProviderStatusEnum": "apps.ai.models.AIProviderStatus.choices",
        "AICallStatusEnum": "apps.ai.models.AICallStatus.choices",
        "SubscriptionStatusEnum": "apps.billing.models.SubscriptionStatus.choices",
        "StripeWebhookEventStatusEnum": "apps.billing.models.StripeWebhookEventStatus.choices",
        "ProviderAuthTypeEnum": "apps.integrations.models.ProviderAuthType.choices",
        "ProviderStatusEnum": "apps.integrations.models.ProviderStatus.choices",
        "IntegrationAccountStatusEnum": "apps.integrations.models.IntegrationAccountStatus.choices",
        "CredentialTypeEnum": "apps.integrations.models.CredentialType.choices",
        "SyncLogStatusEnum": "apps.integrations.models.SyncLogStatus.choices",
        "JobRunStatusEnum": "apps.jobs.models.JobRunStatus.choices",
        "MembershipRoleEnum": "apps.organizations.models.MembershipRole.choices",
        "MembershipStatusEnum": "apps.organizations.models.MembershipStatus.choices",
        "NotificationChannelEnum": "apps.notifications.models.NotificationChannel.choices",
        "NotificationDeliveryStatusEnum": (
            "apps.notifications.models.NotificationDeliveryStatus.choices"
        ),
        "NotificationEventEnum": "apps.notifications.models.NotificationEvent.choices",
        "ReportFormatEnum": "apps.reports.models.ReportFormat.choices",
        "ReportStatusEnum": "apps.reports.models.ReportStatus.choices",
        "PrivacyRequestStatusEnum": "apps.privacy.models.PrivacyRequestStatus.choices",
        "DataExportScopeEnum": "apps.privacy.models.DataExportScope.choices",
        "ExampleInsightStatusEnum": (
            "apps.products.example_insights.models.ExampleInsightStatus.choices"
        ),
    },
}

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/1",
)
CELERY_TIMEZONE = TIME_ZONE

HEALTHCHECK_REQUIRE_REDIS = env.bool("HEALTHCHECK_REQUIRE_REDIS", default=False)
HEALTHCHECK_REDIS_URL = env("HEALTHCHECK_REDIS_URL", default=REDIS_URL)

FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="http://localhost:5173")
BILLING_ALLOWED_REDIRECT_HOSTS = env.list("BILLING_ALLOWED_REDIRECT_HOSTS", default=[])
MAX_JSON_PAYLOAD_BYTES = env.int("MAX_JSON_PAYLOAD_BYTES", default=65536)
AUDIT_TRUST_X_FORWARDED_FOR = env.bool("AUDIT_TRUST_X_FORWARDED_FOR", default=False)

STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

DEFAULT_AI_PROVIDER = env("DEFAULT_AI_PROVIDER", default="openai")
DEFAULT_AI_MODEL = env("DEFAULT_AI_MODEL", default="")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")

AWS_REGION = env("AWS_REGION", default="eu-central-1")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")

EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="console")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@example.com")

DATA_RETENTION_DAYS = env.int("DATA_RETENTION_DAYS", default=365)
AUDIT_LOG_RETENTION_DAYS = env.int("AUDIT_LOG_RETENTION_DAYS", default=2555)

SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=ENVIRONMENT,
        release=DEPLOY_VERSION,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )

LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOG_FORMAT = env("LOG_FORMAT", default="plain")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        },
        "json": {
            "()": "apps.common.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if LOG_FORMAT == "json" else "plain",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
