import json
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from backend.tests.conftest import TestingSessionLocal
from backend.app.models.models import (
    Order, OrderStatus, ApprovalRequest, ApprovalStatus, RefundRequest, RefundStatus,
    AgentRun, AgentEvent, ToolExecutionLog, AuditLog, Customer
)
from backend.app.core.broadcaster import EventBroadcaster


def test_acceptance_01_create_order_and_verify_in_dashboard(client: TestClient, admin_headers: dict):
    """
    TEST 1: Create an order and verify it appears in the orders dashboard.
    """
    with TestingSessionLocal() as db:
        customer = db.query(Customer).first()
        assert customer is not None, "Customer required for order creation"
        cust_id = customer.id

    create_payload = {
        "customer_id": cust_id,
        "shipping_address": "452 Industrial Parkway, Austin, TX 78701",
        "currency": "USD",
        "items": [
            {
                "product_id": 1,
                "quantity": 2,
                "unit_price": 99.50
            }
        ]
    }

    # 1. Create order
    res = client.post("/api/v1/orders", json=create_payload, headers=admin_headers)
    assert res.status_code == 201, f"Failed to create order: {res.text}"
    created_order = res.json()
    order_id = created_order["id"]
    order_number = created_order["order_number"]
    assert float(created_order["total_amount"]) == 199.00
    assert created_order["status"] == OrderStatus.CONFIRMED.value

    # 2. Verify order appears in list endpoint
    list_res = client.get("/api/v1/orders", headers=admin_headers)
    assert list_res.status_code == 200
    orders_list = list_res.json()
    matching = [o for o in orders_list if o["id"] == order_id]
    assert len(matching) == 1
    assert matching[0]["order_number"] == order_number


def test_acceptance_02_delayed_delivery_retrieves_actual_shipment(client: TestClient, auth_headers: dict):
    """
    TEST 2: Submit a delayed-delivery query and verify the agent retrieves the actual shipment record.
    """
    query = "Where is my order ORD-2024-1002? It has not arrived yet."
    res = client.post("/api/v1/agent/message", json={"query": query, "customer_id": 2}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "DELIVERY_DELAY"
    assert data["status"] == "completed"

    # Verify backend tools executed
    tool_names = [t["tool"] for t in data["tools_executed"]]
    assert "get_order_details" in tool_names or "check_delivery_status" in tool_names

    # Verify actual shipment delay evidence is retrieved
    assert "delay" in data["final_response"].lower() or "weather" in data["final_response"].lower()


def test_acceptance_03_payment_deducted_order_missing_retrieves_transaction(client: TestClient, auth_headers: dict):
    """
    TEST 3: Submit a payment issue and verify the correct transaction is retrieved.
    """
    query = "My payment was deducted for TXN-2024-998811, but no order confirmation was received."
    res = client.post("/api/v1/agent/message", json={"query": query, "customer_id": 4}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["intent"] == "PAYMENT_DEDUCTED_ORDER_MISSING"
    tool_names = [t["tool"] for t in data["tools_executed"]]
    assert "get_payment_details" in tool_names

    # Verify orphan payment was identified
    payment_tools = [t for t in data["tools_executed"] if t["tool"] == "get_payment_details"]
    assert len(payment_tools) > 0
    p_res = payment_tools[0]["result"]
    assert p_res.get("is_orphan") is True
    assert p_res.get("transaction_id") == "TXN-2024-998811"


def test_acceptance_04_rag_retrieval_returns_grounded_policy_citations(client: TestClient, auth_headers: dict):
    """
    TEST 4: Verify that RAG retrieves relevant sections for operational policies.
    """
    res = client.get("/api/v1/knowledge/search?query=return%20policy%2030%20days&top_k=3", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_results"] > 0
    citations = data["citations"]
    assert len(citations) > 0
    first = citations[0]
    assert "source_document" in first
    assert "snippet" in first
    assert first["relevance_score"] >= 0.0


def test_acceptance_05_refund_request_creates_pending_approval(client: TestClient, auth_headers: dict):
    """
    TEST 5: Request a refund and verify that a pending approval is stored in the database.
    """
    query = "I would like to request a refund for order ORD-2024-1005 because the items were defective."
    res = client.post("/api/v1/agent/message", json={"query": query, "customer_id": 5}, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["requires_human_approval"] is True
    app_id = data["approval_request_id"]
    assert app_id is not None

    # Verify directly in the database
    with TestingSessionLocal() as db:
        app_req = db.query(ApprovalRequest).filter(ApprovalRequest.id == app_id).first()
        assert app_req is not None
        assert app_req.status == ApprovalStatus.PENDING.value
        assert app_req.request_type == "refund"


def test_acceptance_06_operator_approves_request_and_updates_database(client: TestClient, admin_headers: dict):
    """
    TEST 6: Approve the request as an authorized operator and verify the database changes.
    """
    with TestingSessionLocal() as db:
        pending = db.query(ApprovalRequest).filter(ApprovalRequest.status == ApprovalStatus.PENDING.value).first()
        assert pending is not None, "Pending approval request required"
        pending_id = pending.id

    approve_url = f"/api/v1/approvals/{pending_id}/approve"
    res = client.post(approve_url, json={"comments": "Accepted under operational warranty exception."}, headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == ApprovalStatus.APPROVED.value
    assert data["comments"] == "Accepted under operational warranty exception."
    assert data["reviewed_by"] is not None

    # Verify immutable audit log was created
    with TestingSessionLocal() as db:
        audit = db.query(AuditLog).filter(
            AuditLog.entity_type == "approval_request",
            AuditLog.entity_id == str(pending_id),
            AuditLog.action == "APPROVAL_REQUEST_APPROVED"
        ).first()
        assert audit is not None


def test_acceptance_07_realtime_operational_events_broadcasting():
    """
    TEST 7: Verify that the real-time SSE broadcaster dispatches operational events across sessions.
    """
    queue = EventBroadcaster.subscribe()
    try:
        test_payload = {"order_id": 9999, "status": "shipped"}
        EventBroadcaster.broadcast("order.updated", test_payload)

        # Subscriber queue receives the event
        assert not queue.empty()
        item = queue.get_nowait()
        assert item["type"] == "order.updated"
        assert item["data"]["order_id"] == 9999
        assert item["data"]["status"] == "shipped"
    finally:
        EventBroadcaster.unsubscribe(queue)


def test_acceptance_08_inspect_agent_execution_history_and_events(client: TestClient, admin_headers: dict):
    """
    TEST 8: Inspect agent execution history and verify actual tool calls and persisted SSE events.
    """
    runs_res = client.get("/api/v1/agent/runs?limit=1", headers=admin_headers)
    assert runs_res.status_code == 200
    runs = runs_res.json()
    assert len(runs) > 0
    first_run_id = runs[0]["id"]

    # Verify detailed trace
    detail_res = client.get(f"/api/v1/agent/runs/{first_run_id}", headers=admin_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "tool_logs" in detail

    # Verify persisted SSE events endpoint
    events_res = client.get(f"/api/v1/agent/runs/{first_run_id}/events", headers=admin_headers)
    assert events_res.status_code == 200
    events = events_res.json()
    assert len(events) > 0
    event_types = [e["event_type"] for e in events]
    assert "agent.started" in event_types


def test_acceptance_09_persistence_after_reload():
    """
    TEST 9: Verify that orders, approvals, audit logs, and agent runs persist in the database.
    """
    with TestingSessionLocal() as db:
        orders_count = db.query(Order).count()
        assert orders_count > 0

        runs_count = db.query(AgentRun).count()
        assert runs_count > 0

        audit_count = db.query(AuditLog).count()
        assert audit_count > 0


def test_acceptance_10_production_health_check_and_deployment_readiness(client: TestClient):
    """
    TEST 10: Production health check and deployment readiness.
    """
    res1 = client.get("/health")
    assert res1.status_code == 200
    h1 = res1.json()
    assert h1["status"] == "healthy"
    assert h1["database"] == "connected"

    res2 = client.get("/api/v1/health")
    assert res2.status_code == 200
    h2 = res2.json()
    assert h2["status"] == "healthy"
    assert "indexed_policy_vectors" in h2
