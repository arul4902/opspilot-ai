import pytest
from sqlalchemy.orm import Session
from backend.app.agents.triage_agent import TriageAgent
from backend.app.agents.investigation_agent import InvestigationAgent
from backend.app.agents.knowledge_agent import KnowledgeAgent
from backend.app.agents.resolution_agent import ResolutionAgent
from backend.app.agents.orchestrator import AgentOrchestrator


def test_triage_agent_resolution(db_session: Session):
    triage = TriageAgent(db_session)
    ctx = triage.triage(
        query="Order ORD-2024-1002 is late, where is it?",
        customer_id=2
    )

    assert ctx.classification.intent in ["DELIVERY_DELAY", "ORDER_TRACKING"]
    assert ctx.active_order_ref == "ORD-2024-1002"
    assert ctx.customer_id == 2
    assert ctx.customer_name is not None


def test_investigation_agent_delay_detection(db_session: Session):
    triage = TriageAgent(db_session)
    ctx = triage.triage(query="Order ORD-2024-1002 is late", customer_id=2)

    inv_agent = InvestigationAgent(db_session)
    inv = inv_agent.investigate(ctx)

    assert inv.is_delayed is True
    assert inv.order_details is not None
    assert inv.tracking_details is not None
    assert len(inv.evidence) >= 2


def test_knowledge_agent_retrieval(db_session: Session):
    triage = TriageAgent(db_session)
    ctx = triage.triage(query="Order ORD-2024-1002 is delayed", customer_id=2)

    inv_agent = InvestigationAgent(db_session)
    inv = inv_agent.investigate(ctx)

    know_agent = KnowledgeAgent(db_session)
    know = know_agent.retrieve_grounding(ctx, inv)

    assert len(know.citations) > 0
    assert any("delay" in c["snippet"].lower() or "sla" in c["snippet"].lower() for c in know.citations)


def test_resolution_agent_synthesis(db_session: Session):
    triage = TriageAgent(db_session)
    ctx = triage.triage(query="Order ORD-2024-1002 is delayed", customer_id=2)

    inv_agent = InvestigationAgent(db_session)
    inv = inv_agent.investigate(ctx)

    know_agent = KnowledgeAgent(db_session)
    know = know_agent.retrieve_grounding(ctx, inv)

    res_agent = ResolutionAgent(db_session)
    res = res_agent.resolve(ctx, inv, know)

    assert res.final_response is not None
    assert len(res.final_response) > 20
    assert "courtesy credit" in res.recommended_action.lower() or "delay" in res.recommended_action.lower()


def test_orchestrator_multi_agent_pipeline(db_session: Session):
    orchestrator = AgentOrchestrator(db_session)
    result = orchestrator.process_request(
        query="Order ORD-2024-1002 is delayed, please update me",
        customer_id=2
    )

    assert result.status == "completed"
    assert len(result.timeline) >= 6
    assert len(result.tools_executed) >= 2
    assert len(result.knowledge_sources) > 0

