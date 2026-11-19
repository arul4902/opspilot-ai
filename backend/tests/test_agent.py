import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.app.agents.intent_classifier import IntentClassifier
from backend.app.agents.orchestrator import AgentOrchestrator
from backend.app.models.models import AgentRun, ToolExecutionLog, Escalation


def test_intent_classifier_intents():
    classifier = IntentClassifier()

    # Test delivery delay intent & entity extraction
    res1 = classifier.classify("Where is my order ORD-2024-1002? It has not arrived yet!")
    assert res1.intent in ["DELIVERY_DELAY", "ORDER_TRACKING"]
    assert res1.entities.order_number == "ORD-2024-1002"

    # Test orphan payment intent & entity extraction
    res2 = classifier.classify("My payment was deducted for TXN-2024-998811, but no order was created!")
    assert res2.intent == "PAYMENT_DEDUCTED_ORDER_MISSING"
    assert res2.entities.transaction_reference == "TXN-2024-998811"

    # Test refund request intent
    res3 = classifier.classify("I want a refund for order ORD-2024-1001 because the item was defective.")
    assert res3.intent == "REFUND_REQUEST"
    assert res3.entities.order_number == "ORD-2024-1001"

    # Test return request intent
    res4 = classifier.classify("Can I return order ORD-2024-1003? The size is wrong.")
    assert res4.intent == "RETURN_REQUEST"
    assert res4.entities.order_number == "ORD-2024-1003"

    # Test policy query intent
    res5 = classifier.classify("What is your standard return policy window?")
    assert res5.intent == "POLICY_QUERY"


def test_orchestrator_delivery_delay(db_session: Session):
    orchestrator = AgentOrchestrator(db_session)
    result = orchestrator.process_request(
        query="Why is my order ORD-2024-1002 delayed? When will it get here?",
        customer_id=2
    )

    assert result.intent in ["DELIVERY_DELAY", "ORDER_TRACKING"]
    assert result.status == "completed"
    assert len(result.timeline) >= 6
    assert any(t["tool"] == "get_order_details" for t in result.tools_executed)
    assert any(t["tool"] == "check_delivery_status" for t in result.tools_executed)
    assert len(result.knowledge_sources) > 0
    assert "ORD-2024-1002" in result.final_response or "delayed" in result.final_response.lower()

    # Verify agent run was recorded in DB
    run = db_session.query(AgentRun).filter(AgentRun.id == result.run_id).first()
    assert run is not None
    assert run.status == "completed"
    assert len(run.tool_logs) >= 2


def test_orchestrator_orphan_payment(db_session: Session):
    orchestrator = AgentOrchestrator(db_session)
    result = orchestrator.process_request(
        query="My payment was deducted under transaction TXN-2024-998811, but I received no order confirmation!",
        customer_id=1
    )

    assert result.intent == "PAYMENT_DEDUCTED_ORDER_MISSING"
    assert result.requires_human_approval is True
    assert any(t["tool"] == "get_payment_details" for t in result.tools_executed)

    # Check that escalation was created
    escalation = db_session.query(Escalation).filter(Escalation.customer_id == 1).first()
    assert escalation is not None


def test_orchestrator_refund_initiation(db_session: Session):
    orchestrator = AgentOrchestrator(db_session)
    result = orchestrator.process_request(
        query="I need a refund for my order ORD-2024-1010",
        customer_id=10
    )

    assert result.intent == "REFUND_REQUEST"
    assert result.requires_human_approval is True
    assert result.approval_request_id is not None
    assert any(t["tool"] == "initiate_refund_request" for t in result.tools_executed)


def test_agent_message_api(client: TestClient, auth_headers: dict):
    response = client.post(
        "/api/v1/agent/message",
        headers=auth_headers,
        json={
            "query": "Where is my shipment for ORD-2024-1002?",
            "customer_id": 2
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "timeline" in data
    assert len(data["timeline"]) > 0
    assert "final_response" in data


def test_agent_runs_list_and_detail_api(client: TestClient, auth_headers: dict):
    # First invoke a query
    client.post(
        "/api/v1/agent/message",
        headers=auth_headers,
        json={"query": "What is the return policy?", "customer_id": 1}
    )

    # List runs
    list_res = client.get("/api/v1/agent/runs", headers=auth_headers)
    assert list_res.status_code == 200
    runs = list_res.json()
    assert len(runs) > 0
    first_run_id = runs[0]["id"]

    # Get run detail
    detail_res = client.get(f"/api/v1/agent/runs/{first_run_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == first_run_id
    assert "tool_logs" in detail

