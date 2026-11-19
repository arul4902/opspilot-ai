import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.models import ApprovalRequest, ApprovalStatus, RefundRequest, RefundStatus, Order


def test_list_approvals_api(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/approvals", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) > 0
    assert "status" in items[0]
    assert "payload" in items[0]


def test_get_approval_detail(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/approvals", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()
    first_id = items[0]["id"]

    detail_res = client.get(f"/api/v1/approvals/{first_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == first_id


def test_approve_flow(client: TestClient, auth_headers: dict, db_session: Session):
    # Find a pending approval
    pending = db_session.query(ApprovalRequest).filter(ApprovalRequest.status == ApprovalStatus.PENDING.value).first()
    assert pending is not None
    target_id = pending.id

    approve_res = client.post(
        f"/api/v1/approvals/{target_id}/approve",
        headers=auth_headers,
        json={"comments": "Approved after reviewing carrier proof"}
    )
    assert approve_res.status_code == 200
    data = approve_res.json()
    assert data["status"] == "approved"
    assert data["reviewed_by"] is not None
    assert "SIM-REF-" in str(data["execution_result"])

    # Verify db status
    db_session.expire_all()
    updated = db_session.query(ApprovalRequest).filter(ApprovalRequest.id == target_id).first()
    assert updated.status == "approved"


def test_reject_flow(client: TestClient, auth_headers: dict, db_session: Session):
    # Create or find a pending approval to test rejection
    from datetime import datetime, timezone
    import json

    test_appr = ApprovalRequest(
        request_type="refund",
        payload_json=json.dumps({"reason": "Customer changed mind", "amount": 49.99}),
        status=ApprovalStatus.PENDING.value,
        requested_by_agent="OpsPilot Test Agent",
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(test_appr)
    db_session.commit()
    db_session.refresh(test_appr)

    reject_res = client.post(
        f"/api/v1/approvals/{test_appr.id}/reject",
        headers=auth_headers,
        json={"comments": "Item shows visible signs of usage, violates section 2.1"}
    )
    assert reject_res.status_code == 200
    data = reject_res.json()
    assert data["status"] == "rejected"
    assert "violates section 2.1" in data["comments"]


def test_approval_rbac_forbidden_for_customer(client: TestClient, customer_token: str):
    headers = {"Authorization": f"Bearer {customer_token}"}
    res = client.get("/api/v1/approvals", headers=headers)
    assert res.status_code == 403

