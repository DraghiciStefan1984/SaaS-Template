import pytest


def test_health_endpoint(client):
    response = client.get("/api/v1/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "saas-core-template",
    }


def test_liveness_endpoint(client):
    response = client.get("/api/v1/health/live/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "alive",
        "service": "saas-core-template",
    }


def test_request_id_header_is_returned(client):
    response = client.get("/api/v1/health/live/", HTTP_X_REQUEST_ID="req-test-123")

    assert response.status_code == 200
    assert response["X-Request-ID"] == "req-test-123"


@pytest.mark.django_db
def test_readiness_endpoint_checks_database_and_skips_redis_by_default(client, settings):
    settings.HEALTHCHECK_REQUIRE_REDIS = False

    response = client.get("/api/v1/health/ready/")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "skipped"
