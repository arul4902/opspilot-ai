import pytest
from fastapi.testclient import TestClient


def test_list_shipments(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/shipments", headers=headers)
    assert res.status_code == 200
    shipments = res.json()
    assert len(shipments) > 0


def test_investigate_delayed_delivery(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Find order ORD-2024-1002
    orders_res = client.get("/api/v1/orders?status=shipped", headers=headers)
    order_1002 = next((o for o in orders_res.json() if o["order_number"] == "ORD-2024-1002"), None)
    assert order_1002 is not None

    res = client.get(f"/api/v1/shipments/investigate/order/{order_1002['id']}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["is_delayed"] is True
    assert "delayed" in data["evidence"].lower() or "road closure" in data["evidence"].lower()
    assert "credit" in data["recommended_action"].lower() or "reshipment" in data["recommended_action"].lower()
