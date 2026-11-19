import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.models import Escalation, EscalationStatus, AuditLog


def test_list_escalations(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/escalations", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) > 0
    assert "priority" in items[0]
    assert "status" in items[0]


def test_patch_escalation(client: TestClient, auth_headers: dict, db_session: Session):
    esc = db_session.query(Escalation).first()
    assert esc is not None

    patch_res = client.patch(
        f"/api/v1/escalations/{esc.id}",
        headers=auth_headers,
        json={
            "status": EscalationStatus.RESOLVED.value,
            "resolution_notes": "Issued bank verification letter and updated tracking."
        }
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["status"] == EscalationStatus.RESOLVED.value
    assert data["resolution_notes"] is not None


def test_list_audit_logs(client: TestClient, auth_headers: dict):
    res = client.get("/api/v1/audit-logs", headers=auth_headers)
    assert res.status_code == 200
    logs = res.json()
    assert isinstance(logs, list)
    assert len(logs) > 0
    assert "action" in logs[0]
    assert "entity_type" in logs[0]
    assert "timestamp" in logs[0]

