import pytest
from fastapi.testclient import TestClient


def test_analytics_overview(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_orders"] >= 30
    assert data["total_revenue"] > 1000.0
    assert "orders_by_status" in data
    assert data["delayed_shipments_count"] >= 1
    assert data["orphan_payments_count"] >= 1
    assert data["agent_success_rate_percent"] > 0


def test_analytics_trends(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/analytics/trends?days=7", headers=auth_headers)
    assert res.status_code == 200
    trends = res.json()
    assert isinstance(trends, list)
    assert len(trends) == 7
    assert "date" in trends[0]
    assert "orders_count" in trends[0]


def test_analytics_rbac_customer_forbidden(client: TestClient, customer_token: str):
    headers = {"Authorization": f"Bearer {customer_token}"}
    res = client.get("/api/v1/analytics/overview", headers=headers)
    assert res.status_code == 403

