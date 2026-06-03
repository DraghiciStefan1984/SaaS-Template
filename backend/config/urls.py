from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.common.views import health_check, liveness_check, readiness_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/health/live/", liveness_check, name="liveness-check"),
    path("api/v1/health/ready/", readiness_check, name="readiness-check"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/organizations/", include("apps.organizations.urls")),
    path("api/v1/billing/", include("apps.billing.urls")),
    path("api/v1/usage/", include("apps.usage.urls")),
    path("api/v1/integrations/", include("apps.integrations.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
    path("api/v1/jobs/", include("apps.jobs.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/privacy/", include("apps.privacy.urls")),
    path(
        "api/v1/products/example-insights/",
        include("apps.products.example_insights.urls"),
    ),
    path("api/v1/audit/", include("apps.audit.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
