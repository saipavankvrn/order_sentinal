import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Verifies root endpoint returns service metadata and docs link."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "OrderFlow Sentinel"
    assert data["version"] == "1.2.1"
    assert data["status"] == "ONLINE"
    assert "/docs" in data["docs"]
    assert "/api/v1/health" in data["health"]


def test_health_endpoint(client: TestClient):
    """Verifies GET /api/v1/health returns HTTP 200 with verified database connectivity."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert "data" in payload
    assert "timestamp" in payload

    health_data = payload["data"]
    assert health_data["status"] == "HEALTHY"

    # Database check
    db_health = health_data["database"]
    assert db_health["status"] == "CONNECTED"
    assert db_health["engine"] == "sqlite"
    assert isinstance(db_health["wal_mode"], bool)

    # AI engine check (optional dependency / fallback mode)
    ai_health = health_data["ai_engine"]
    assert isinstance(ai_health["gemini_available"], bool)
    assert isinstance(ai_health["fallback_mode"], bool)
    assert ai_health["model_configured"] is not None

    # Uptime check
    assert health_data["uptime_seconds"] >= 0

