from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "env" in data
    assert data["env"]["db"].endswith("webhooks_test")
    assert data["env"]["bucket"] == "webhook-payloads-test"
