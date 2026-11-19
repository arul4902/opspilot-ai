import pytest
from fastapi.testclient import TestClient


def test_refund_eligibility_checks(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    orders_res = client.get("/api/v1/orders?limit=50", headers=headers)
    orders = orders_res.json()

    # Find ORD-2024-1005 (Eligible: delivered 7 days ago, refund pending)
    # Note: in seed data, REF-2024-8001 was already created for ORD-2024-1005!
    # So duplicate refund check prevents duplicate
    order_1005 = next(o for o in orders if o["order_number"] == "ORD-2024-1005")
    res_1005 = client.get(f"/api/v1/refunds/eligibility/{order_1005['id']}", headers=headers)
    assert res_1005.status_code == 200
    assert "already exists" in res_1005.json()["reason"]

    # Find ORD-2024-1006 (Ineligible: delivered 48 days ago)
    order_1006 = next(o for o in orders if o["order_number"] == "ORD-2024-1006")
    res_1006 = client.get(f"/api/v1/refunds/eligibility/{order_1006['id']}", headers=headers)
    assert res_1006.status_code == 200
    data_1006 = res_1006.json()
    assert data_1006["eligible"] is False
    assert "30 days" in data_1006["reason"]


def test_create_return_request(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Create return for delivered order ORD-2024-1001
    orders_res = client.get("/api/v1/orders", headers=headers)
    order_1001 = next(o for o in orders_res.json() if o["order_number"] == "ORD-2024-1001")

    payload = {
        "order_id": order_1001["id"],
        "reason": "Customer found sound balance inadequate"
    }
    res = client.post("/api/v1/returns", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "requested"
    assert data["order_id"] == order_1001["id"]
