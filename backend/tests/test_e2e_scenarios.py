import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.models.models import ApprovalRequest, ApprovalStatus, AuditLog, RefundRequest


def test_scenario_a_delayed_delivery(client: TestClient, auth_headers: dict):
    """
    Scenario A: Customer inquires about delayed delivery for ORD-2024-1002.
    Agent must:
    1. Classify intent as DELIVERY_DELAY
    2. Check order and tracking details via backend tools
    3. Detect weather delay breaching delivery SLA
    4. Retrieve Shipping SLA Policy (POL-LOG-2026-v2)
    5. Propose courtesy credit without requiring human approval
    """
    payload = {
        "query": "Where is my order ORD-2024-1002? It has not arrived yet.",
        "customer_id": 2
    }
    resp = client.post("/api/v1/agent/message", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] in ["DELIVERY_DELAY", "ORDER_TRACKING"]
    assert data["status"] == "completed"
    assert data["requires_human_approval"] is False

    # Check tools executed
    tools = [t["tool"] for t in data["tools_executed"]]
    assert "get_order_details" in tools
    assert "check_delivery_status" in tools

    # Check grounded knowledge citations
    assert len(data["knowledge_sources"]) > 0
    assert any("delay" in c["snippet"].lower() or "sla" in c["snippet"].lower() for c in data["knowledge_sources"])

    # Check response text
    assert "ORD-2024-1002" in data["final_response"]
    assert "delay" in data["final_response"].lower() or "courtesy" in data["final_response"].lower()


def test_scenario_b_payment_deducted_order_missing(client: TestClient, auth_headers: dict):
    """
    Scenario B: Customer had payment captured but order is missing.
    Agent must:
    1. Classify intent as PAYMENT_DEDUCTED_ORDER_MISSING
    2. Detect orphan transaction TXN-2024-998811
    3. Retrieve Payment Discrepancy Policy (POL-PAY-2026-v2)
    4. Escalate to human and mark requires_human_approval = True
    """
    payload = {
        "query": "My payment TXN-2024-998811 was deducted from my bank account, but I have no order confirmation!",
        "customer_id": 2
    }
    resp = client.post("/api/v1/agent/message", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "PAYMENT_DEDUCTED_ORDER_MISSING"
    assert data["requires_human_approval"] is True

    # Check tools executed
    tools = [t["tool"] for t in data["tools_executed"]]
    assert "get_payment_details" in tools
    assert "escalate_to_human" in tools

    # Check grounded citations
    assert len(data["knowledge_sources"]) > 0
    assert any("payment" in c["snippet"].lower() or "orphan" in c["snippet"].lower() or "discrepancy" in c["snippet"].lower() for c in data["knowledge_sources"])

    # Check response indicates human review
    assert "human" in data["final_response"].lower() or "escalat" in data["final_response"].lower() or "review" in data["final_response"].lower()


def test_scenario_c_failed_payment_investigation(client: TestClient, auth_headers: dict):
    """
    Scenario C: Customer inquires why payment failed for ORD-2024-1003.
    Agent must:
    1. Classify intent as PAYMENT_FAILURE
    2. Retrieve payment record showing status = failed
    3. Retrieve Payment Policy
    4. Clarify bank decline without staging unwarranted human approval
    """
    payload = {
        "query": "Why did my payment fail for order ORD-2024-1003?",
        "customer_id": 3
    }
    resp = client.post("/api/v1/agent/message", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "PAYMENT_FAILURE"
    assert data["requires_human_approval"] is False

    tools = [t["tool"] for t in data["tools_executed"]]
    assert "get_payment_details" in tools

    assert "ORD-2024-1003" in data["final_response"]
    assert "declined" in data["final_response"].lower() or "failed" in data["final_response"].lower() or "bank" in data["final_response"].lower()


def test_scenario_d_return_policy_inquiry(client: TestClient, auth_headers: dict):
    """
    Scenario D: Customer asks for general return policy.
    Agent must:
    1. Classify intent as POLICY_QUERY
    2. Perform RAG vector retrieval against knowledge base
    3. Ground response with Return Policy (POL-RET-2026-v2) 30-day window
    4. Avoid triggering unauthorized database mutations
    """
    payload = {
        "query": "What is your return policy and how many days do I have to return an item?",
        "customer_id": 1
    }
    resp = client.post("/api/v1/agent/message", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "POLICY_QUERY"
    assert len(data["knowledge_sources"]) > 0

    # Ensure POL-RET or 30-day clause is retrieved
    has_policy_citation = any("30" in c["snippet"] or "return" in c["snippet"].lower() for c in data["knowledge_sources"])
    assert has_policy_citation is True

    # Final response must cite 30 days
    assert "30" in data["final_response"]
    assert "return" in data["final_response"].lower()


def test_scenario_e_high_value_refund_and_hitl_approval(client: TestClient, auth_headers: dict, admin_headers: dict, db_session: Session):
    """
    Scenario E: Consequential refund workflow with Human-In-The-Loop approval gate.
    1. Agent receives refund request for delivered order ORD-2024-1005
    2. Validates order status = delivered
    3. Initiates simulated refund with status pending_approval
    4. Stages ApprovalRequest record in queue (requires_human_approval = True)
    5. Operations Manager reviews and approves via POST /api/v1/approvals/{id}/approve
    6. Verifies state mutation, refund status update, and audit log creation
    """
    payload = {
        "query": "I would like to request a refund for order ORD-2024-1005 because the items were defective.",
        "customer_id": 5
    }
    resp = client.post("/api/v1/agent/message", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "REFUND_REQUEST"
    assert data["requires_human_approval"] is True
    approval_id = data["approval_request_id"]
    assert approval_id is not None

    # Step 5: Human Operator reviews approval queue
    appr_resp = client.get(f"/api/v1/approvals/{approval_id}", headers=admin_headers)
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()
    assert appr_data["status"] == "pending"
    assert appr_data["request_type"] == "refund_request"

    # Step 6: Operator approves request with verified comments
    approve_resp = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"comments": "Approved after reviewing photographic evidence of defective goods."},
        headers=admin_headers
    )
    assert approve_resp.status_code == 200
    appr_result = approve_resp.json()
    assert appr_result["status"] == "approved"
    assert "SIMULATED_REFUND_COMPLETED" in appr_result["execution_result"].get("status", "")

    # Step 7: Verify refund state in database
    refund = db_session.query(RefundRequest).filter(RefundRequest.order_id == appr_data["order_id"]).first()
    assert refund is not None
    assert refund.status == "approved"

    # Step 8: Verify immutable audit log
    audit = db_session.query(AuditLog).filter(
        AuditLog.action == "APPROVAL_REQUEST_APPROVED",
        AuditLog.entity_id == str(approval_id)
    ).first()
    assert audit is not None


def test_scenario_f_return_request_creation(client: TestClient, auth_headers: dict):
    """
    Scenario F: Valid return request creation for ORD-2024-1007.
    Agent must:
    1. Classify intent as RETURN_REQUEST
    2. Check order delivery date and 30-day window
    3. Execute create_return_request tool
    4. Generate real return request number (RET-...)
    5. Return authorized response with shipping instructions
    """
    payload = {
        "query": "I want to return order ORD-2024-1007 because the size was too large.",
        "customer_id": 7
    }
    resp = client.post("/api/v1/agent/message", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["intent"] == "RETURN_REQUEST"
    tools = [t["tool"] for t in data["tools_executed"]]
    assert "create_return_request" in tools

    # Verify return request generated in results
    create_ret_tool = next(t for t in data["tools_executed"] if t["tool"] == "create_return_request")
    assert create_ret_tool["result"]["success"] is True
    assert create_ret_tool["result"]["return_request_number"].startswith("RET-")

    assert "ORD-2024-1007" in data["final_response"]
    assert "return" in data["final_response"].lower()

