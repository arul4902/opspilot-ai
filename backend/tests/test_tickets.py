import pytest
from fastapi.testclient import TestClient


def test_list_tickets(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/tickets", headers=headers)
    assert res.status_code == 200
    tickets = res.json()
    assert len(tickets) >= 10


def test_create_and_patch_ticket(client: TestClient, admin_token: str, agent_token: str, customer_token: str):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    customer_headers = {"Authorization": f"Bearer {customer_token}"}

    # 1. Customer creates a ticket
    payload = {
        "subject": "Missing instruction manual",
        "description": "The product package did not include the printed setup guide.",
        "priority": "low"
    }
    create_res = client.post("/api/v1/tickets", json=payload, headers=customer_headers)
    assert create_res.status_code == 201
    ticket = create_res.json()
    assert ticket["status"] == "open"
    ticket_id = ticket["id"]

    # 2. Operations Agent updates status to in_progress
    patch_payload = {
        "status": "in_progress",
        "priority": "medium"
    }
    patch_res = client.patch(f"/api/v1/tickets/{ticket_id}", json=patch_payload, headers=agent_headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "in_progress"
    assert patch_res.json()["priority"] == "medium"

    # 3. Customer is forbidden from updating ticket status directly
    forbidden_res = client.patch(f"/api/v1/tickets/{ticket_id}", json={"status": "resolved"}, headers=customer_headers)
    assert forbidden_res.status_code == 403

