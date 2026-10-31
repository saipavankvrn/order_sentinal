import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_analytics_metrics_endpoint(client: TestClient):
    """Verifies that GET /api/v1/analytics/metrics returns aggregate counts matching specification."""
    resp = client.get("/api/v1/analytics/metrics")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    data = payload["data"]
    assert "total_orders" in data
    assert "completed_orders" in data
    assert "failed_orders" in data
    assert "delayed_orders" in data
    assert "pending_approvals" in data
    assert "in_progress_orders" in data
    assert isinstance(data["total_orders"], int)
    assert isinstance(data["pending_approvals"], int)


def test_analytics_distribution_endpoint(client: TestClient):
    """Verifies that GET /api/v1/analytics/distribution returns failure category grouping."""
    resp = client.get("/api/v1/analytics/distribution")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    data = payload["data"]
    assert "categories" in data
    assert "total_incidents" in data
    assert isinstance(data["categories"], list)

