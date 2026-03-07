from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "blindnav-api",
        "environment": "local",
        "status": "ok",
    }


def test_live_health() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_ready_health() -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
