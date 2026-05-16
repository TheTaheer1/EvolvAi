from fastapi.testclient import TestClient

from app.main import fastapi_app


def test_health_endpoint() -> None:
    client = TestClient(fastapi_app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
