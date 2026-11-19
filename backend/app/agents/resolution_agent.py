import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.core.llm import get_llm_client
from backend.app.agents.triage_agent import TriageContext
from backend.app.agents.investigation_agent import InvestigationResult
from backend.app.agents.knowledge_agent import KnowledgeResult
from backend.app.tools.registry import ToolRegistry


class ResolutionResult:
    def __init__(self):
        self.recommended_action: str = ""
        self.requires_human_approval: bool = False
        self.approval_request_id: Optional[int] = None
        self.final_response: str = ""
        self.tools_executed: List[Dict[str, Any]] = []


class ResolutionAgent:
    """
    Resolution Agent: Policy-governed decision maker.
    Determines business remediation, manages Human-In-The-Loop approval gates,
    and synthesizes factually grounded customer communication.
    """
    def __init__(self, db: Session):
        self.db = db
        self.registry = ToolRegistry(db)
        self.llm = get_llm_client()

    def resolve(
        self,
        ctx: TriageContext,
        inv: InvestigationResult,
        know: KnowledgeResult,
        agent_run_id: Optional[int] = None
    ) -> ResolutionResult:
        res = ResolutionResult()
        intent = ctx.classification.intent if ctx.classification else "GENERAL_SUPPORT"
        order_ref = ctx.active_order_ref
        cust_id = ctx.customer_id or 1

        # 1. Evaluate Consequential Business Workflows
        if intent == "REFUND_REQUEST" and order_ref:
            # Sensitive: refund requests require staging ApprovalRequest
            refund_tool = self.registry.get_tool("initiate_refund_request")
            if refund_tool:
                r_res = refund_tool.run(
                    arguments={"order_id": order_ref, "reason": ctx.query},
                    agent_run_id=agent_run_id,
                    user_id=ctx.user_id
                )
                res.tools_executed.append({"tool": "initiate_refund_request", "result": r_res})
                if r_res.get("success"):
                    res.requires_human_approval = True
                    res.approval_request_id = r_res.get("approval_request_id")
                    res.recommended_action = "HUMAN_OPERATOR_REVIEW_PENDING: Simulated refund staged in operations approval queue."
                else:
                    res.recommended_action = f"Refund eligibility rejected: {r_res.get('message')}"

        elif intent == "RETURN_REQUEST" and order_ref:
            return_tool = self.registry.get_tool("create_return_request")
            if return_tool:
                ret_res = return_tool.run(
                    arguments={"order_id": order_ref, "reason": ctx.query},
                    agent_run_id=agent_run_id,
                    user_id=ctx.user_id
                )
                res.tools_executed.append({"tool": "create_return_request", "result": ret_res})
                if ret_res.get("success"):
                    res.recommended_action = f"Return request {ret_res.get('return_request_number')} authorized under 30-day policy. Prepaid label dispatched."
                else:
                    res.recommended_action = f"Return request denied: {ret_res.get('message')}"

        elif intent == "PAYMENT_DEDUCTED_ORDER_MISSING":
            # Consequential: orphan capture detected, escalate for human manager override
            res.requires_human_approval = True
            res.recommended_action = "REQUEST_HUMAN_APPROVAL: Escalate to operations queue to authorize immediate reversal or manual order fulfillment."
            esc_tool = self.registry.get_tool("escalate_to_human")
            if esc_tool:
                esc_res = esc_tool.run(
                    arguments={
                        "conversation_id": ctx.conversation_id,
                        "customer_id": cust_id,
                        "reason": f"Orphan payment discrepancy: customer charged without confirmed order ({ctx.query})",
                        "priority": "urgent"
                    },
                    agent_run_id=agent_run_id,
                    user_id=ctx.user_id
                )
                res.tools_executed.append({"tool": "escalate_to_human", "result": esc_res})

        elif intent in ["DELIVERY_DELAY", "ORDER_TRACKING"]:
            if inv.is_delayed:
                res.recommended_action = "Inform customer of courier weather delay, provide tracking link, and offer $10 courtesy credit."
            else:
                res.recommended_action = "Provide customer with live carrier tracking telemetry and expected delivery schedule."

        elif intent == "PAYMENT_FAILURE":
            res.recommended_action = "Advise customer that charge was declined by bank gateway and provide secure payment retry link."

        else:
            res.recommended_action = "Provide customer with evidence-grounded operational status update."

        # 2. Grounded Response Synthesis
        evidence_str = "\n".join(inv.evidence) if inv.evidence else "Standard operational records inspected."
        citations_str = "\n".join(know.applicable_clauses) if know.applicable_clauses else "OpsPilot Operational Standards"

        synth_prompt = (
            f"You are OpsPilot AI, an autonomous operations engineer.\n"
            f"Generate a professional, helpful, grounded response to the customer based strictly on the verified facts below.\n\n"
            f"Customer Request: \"{ctx.query}\"\n"
            f"Classified Intent: {intent}\n"
            f"Database Facts & Telemetry:\n{evidence_str}\n\n"
            f"Enterprise Policy Grounding:\n{citations_str}\n\n"
            f"Action Recommended:\n{res.recommended_action}\n\n"
            f"Requires Human Approval: {res.requires_human_approval}\n\n"
            "Requirements:\n"
            "- Cite real operational details (order number, tracking event, delivery date, refund status).\n"
            "- Reference company policy terms.\n"
            "- If human approval is required, explicitly inform the customer that their request has been staged for managerial review."
        )

        res.final_response = self.llm.generate(prompt=synth_prompt)
        return res

