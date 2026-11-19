import pytest
from fastapi.testclient import TestClient


def test_list_payments_admin(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/v1/payments", headers=headers)
    assert response.status_code == 200
    payments = response.json()
    assert len(payments) > 0


def test_investigate_orphan_payment(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Customer 4 is Diana Prince (CUST-1004) who has the orphan payment TXN-2024-998811
    res = client.get("/api/v1/payments/investigate/customer/4", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_issues"] is True
    assert data["issue_type"] == "PAYMENT_DEDUCTED_ORDER_MISSING"
    assert "REQUEST_HUMAN_APPROVAL" in data["recommended_action"]


def test_investigate_payment_requires_agent_or_admin(client: TestClient, customer_token: str):
    headers = {"Authorization": f"Bearer {customer_token}"}
    res = client.get("/api/v1/payments/investigate/customer/1", headers=headers)
    assert res.status_code == 403

