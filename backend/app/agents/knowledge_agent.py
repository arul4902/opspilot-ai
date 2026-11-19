from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.agents.triage_agent import TriageContext
from backend.app.agents.investigation_agent import InvestigationResult
from backend.app.tools.registry import ToolRegistry


class KnowledgeResult:
    def __init__(self):
        self.citations: List[Dict[str, Any]] = []
        self.policy_summary: str = ""
        self.applicable_clauses: List[str] = []


class KnowledgeAgent:
    """
    Knowledge Agent: Grounding specialist.
    Retrieves verifiable policy documents via RAG and ensures the resolution complies with enterprise SLAs.
    """
    def __init__(self, db: Session):
        self.db = db
        self.registry = ToolRegistry(db)

    def retrieve_grounding(
        self,
        ctx: TriageContext,
        inv: InvestigationResult,
        agent_run_id: Optional[int] = None
    ) -> KnowledgeResult:
        result = KnowledgeResult()
        intent = ctx.classification.intent if ctx.classification else "GENERAL_SUPPORT"

        # Determine optimal query for knowledge retrieval
        if intent in ["DELIVERY_DELAY", "ORDER_TRACKING"]:
            policy_query = "delivery delay courier weather SLA courtesy credit guarantee"
        elif intent == "PAYMENT_DEDUCTED_ORDER_MISSING":
            policy_query = "payment deducted without order confirmation session drop orphan transaction"
        elif intent == "PAYMENT_FAILURE":
            policy_query = "payment failure declined transactions bank authorization"
        elif intent == "REFUND_REQUEST":
            policy_query = "return window 30 days refund eligibility financial workflows"
        elif intent == "RETURN_REQUEST":
            policy_query = "30 calendar days return window exchange product condition"
        elif intent == "POLICY_QUERY":
            policy_query = ctx.query
        else:
            policy_query = ctx.query

        tool = self.registry.get_tool("search_return_policy")
        if tool:
            tool_res = tool.run({"query": policy_query}, agent_run_id=agent_run_id, user_id=ctx.user_id)
            if tool_res.get("success"):
                result.citations = tool_res.get("citations", [])
                result.policy_summary = tool_res.get("policy_summary", "")
                for c in result.citations:
                    result.applicable_clauses.append(f"[{c.get('source_document')}, {c.get('section')}]: {c.get('snippet')}")

        return result

