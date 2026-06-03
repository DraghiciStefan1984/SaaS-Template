import redis
from django.conf import settings
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from redis.exceptions import RedisError

SERVICE_NAME = "saas-core-template"


@require_GET
def health_check(_request):
    return JsonResponse({"status": "ok", "service": SERVICE_NAME})


@require_GET
def liveness_check(_request):
    return JsonResponse({"status": "alive", "service": SERVICE_NAME})


@require_GET
def readiness_check(_request):
    checks = {
        "database": check_database(),
        "redis": check_redis() if settings.HEALTHCHECK_REQUIRE_REDIS else {"status": "skipped"},
    }
    is_ready = all(check["status"] in {"ok", "skipped"} for check in checks.values())
    return JsonResponse(
        {
            "status": "ready" if is_ready else "not_ready",
            "service": SERVICE_NAME,
            "checks": checks,
        },
        status=200 if is_ready else 503,
    )


def check_database():
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return {"status": "error", "detail": exc.__class__.__name__}
    return {"status": "ok"}


def check_redis():
    try:
        client = redis.from_url(
            settings.HEALTHCHECK_REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
    except RedisError as exc:
        return {"status": "error", "detail": exc.__class__.__name__}
    return {"status": "ok"}
