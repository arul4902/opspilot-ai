import pytest
from fastapi.testclient import TestClient


def test_list_orders_admin(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/api/v1/orders", headers=headers)
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) > 0
    assert any(o["order_number"] == "ORD-2024-1001" for o in orders)


def test_get_order_detail(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Fetch list to get a valid order id
    list_res = client.get("/api/v1/orders", headers=headers)
    assert list_res.status_code == 200
    order_id = list_res.json()[0]["id"]

    res = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total_amount" in data
    assert "status" in data


def test_get_nonexistent_order(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/orders/999999", headers=headers)
    assert res.status_code == 404

