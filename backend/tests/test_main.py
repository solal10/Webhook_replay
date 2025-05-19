from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "settings" in data
    settings = data["settings"]
    assert "database_url" in settings
    assert "stripe_signing_secret" in settings
    assert "aws_region" in settings
    assert "events_bucket" in settings
