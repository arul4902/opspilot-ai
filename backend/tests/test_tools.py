import pytest
from sqlalchemy.orm import Session
from backend.app.tools.registry import ToolRegistry


def test_tool_registry_initialization(db_session: Session):
    registry = ToolRegistry(db_session)
    tools = registry.list_tools()
    assert len(tools) == 9
    tool_names = [t["name"] for t in tools]
    assert "get_order_details" in tool_names
    assert "get_payment_details" in tool_names
    assert "check_delivery_status" in tool_names
    assert "search_return_policy" in tool_names
    assert "create_return_request" in tool_names
    assert "initiate_refund_request" in tool_names
    assert "create_support_ticket" in tool_names
    assert "escalate_to_human" in tool_names
    assert "search_customer_history" in tool_names


def test_tool_get_order_details(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("get_order_details")
    assert tool is not None

    res = tool.run({"order_id": "ORD-2024-1001"})
    assert res["success"] is True
    assert res["order_number"] == "ORD-2024-1001"
    assert len(res["products"]) > 0


def test_tool_get_payment_details_orphan(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("get_payment_details")
    res = tool.run({"order_id": "TXN-2024-998811"})
    assert res["success"] is True
    assert res["is_orphan"] is True
    assert res["payment_status"] == "successful"


def test_tool_check_delivery_status(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("check_delivery_status")
    res = tool.run({"order_id": "ORD-2024-1002"})
    assert res["success"] is True
    assert res["is_delayed"] is True
    assert "road closure" in res["evidence"].lower() or "delayed" in res["evidence"].lower()


def test_tool_search_return_policy(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("search_return_policy")
    res = tool.run({"query": "How many days do I have to return an item?"})
    assert res["success"] is True
    assert len(res["citations"]) > 0
    assert any("30" in c["snippet"] for c in res["citations"])


def test_tool_create_return_request(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("create_return_request")
    res = tool.run({"order_id": "ORD-2024-1007", "reason": "Customer needs a different size"})
    assert res["success"] is True
    assert res["eligible"] is True
    assert "RET-" in res["return_request_number"]


def test_tool_initiate_refund_request(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("initiate_refund_request")
    # ORD-2024-1001 is delivered 10 days ago, eligible
    res = tool.run({"order_id": "ORD-2024-1001", "reason": "Customer found sound balance inadequate"})
    assert res["success"] is True
    assert res["is_simulated"] is True
    assert res["requires_approval"] is True
    assert res["status"] == "pending_approval"


def test_tool_create_support_ticket(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("create_support_ticket")
    res = tool.run({
        "customer_id": 1,
        "subject": "Tool Unit Test Ticket",
        "description": "Created from tool test",
        "priority": "low"
    })
    assert res["success"] is True
    assert res["ticket_number"].startswith("TCK-")


def test_tool_escalate_to_human(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("escalate_to_human")
    res = tool.run({
        "customer_id": 1,
        "reason": "Customer disputes charge amount",
        "priority": "urgent"
    })
    assert res["success"] is True
    assert res["status"] == "pending"
    assert "Escalation ID" in res["message"]


def test_tool_search_customer_history(db_session: Session):
    registry = ToolRegistry(db_session)
    tool = registry.get_tool("search_customer_history")
    res = tool.run({"customer_id": 1})
    assert res["success"] is True
    assert res["history"]["customer_id"] == 1
    assert "recent_orders" in res["history"]

