from fastapi.testclient import TestClient

from app.api.routes import health as health_routes
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == settings.SERVICE_NAME
    assert payload["environment"] == settings.ENVIRONMENT
    assert payload["status"] == "ok"


def test_live_health() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_health_shape(monkeypatch) -> None:
    monkeypatch.setattr(health_routes, "check_db", lambda: "ok")
    monkeypatch.setattr(health_routes, "check_redis", lambda: "ok")

    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == settings.SERVICE_NAME
    assert payload["environment"] == settings.ENVIRONMENT
    assert payload["status"] == "ok"
    assert payload["checks"] == {"db": "ok", "redis": "ok"}


def test_ready_health_both_ok(monkeypatch) -> None:
    monkeypatch.setattr(health_routes, "check_db", lambda: "ok")
    monkeypatch.setattr(health_routes, "check_redis", lambda: "ok")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_health_degraded(monkeypatch) -> None:
    monkeypatch.setattr(health_routes, "check_db", lambda: "ok")
    monkeypatch.setattr(health_routes, "check_redis", lambda: "down")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"] == {"db": "ok", "redis": "down"}


def test_ready_health_down(monkeypatch) -> None:
    monkeypatch.setattr(health_routes, "check_db", lambda: "down")
    monkeypatch.setattr(health_routes, "check_redis", lambda: "down")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "down"
    assert response.json()["checks"] == {"db": "down", "redis": "down"}
