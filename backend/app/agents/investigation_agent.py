import json
from typing import List, Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from backend.app.agents.triage_agent import TriageContext
from backend.app.tools.registry import ToolRegistry
from backend.app.core.logging import logger


class InvestigationResult:
    def __init__(self):
        self.tools_executed: List[Dict[str, Any]] = []
        self.evidence: List[str] = []
        self.is_delayed: bool = False
        self.delay_evidence: Optional[str] = None
        self.is_orphan_payment: bool = False
        self.orphan_payment_amount: Optional[float] = None
        self.is_payment_failed: bool = False
        self.payment_failure_reason: Optional[str] = None
        self.order_details: Optional[Dict[str, Any]] = None
        self.tracking_details: Optional[Dict[str, Any]] = None
        self.customer_history: Optional[Dict[str, Any]] = None


class InvestigationAgent:
    """
    Investigation Agent: Deep multi-system inspector.
    Queries database records, courier APIs, and transaction logs using validated backend tools.
    """
    def __init__(self, db: Session):
        self.db = db
        self.registry = ToolRegistry(db)

    def investigate(
        self,
        ctx: TriageContext,
        agent_run_id: Optional[int] = None,
        on_tool_start: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        on_tool_complete: Optional[Callable[[str, Dict[str, Any], bool, Optional[str]], None]] = None
    ) -> InvestigationResult:
        result = InvestigationResult()
        intent = ctx.classification.intent if ctx.classification else "GENERAL_SUPPORT"
        order_ref = ctx.active_order_ref
        txn_ref = ctx.active_txn_ref
        cust_id = ctx.customer_id or 1

        # Determine tool sequence based on intent
        tools_to_run: List[tuple[str, Dict[str, Any]]] = []

        if intent in ["DELIVERY_DELAY", "ORDER_TRACKING"]:
            if order_ref:
                tools_to_run.append(("get_order_details", {"order_id": order_ref}))
                tools_to_run.append(("check_delivery_status", {"order_id": order_ref}))
            else:
                tools_to_run.append(("search_customer_history", {"customer_id": cust_id}))

        elif intent == "PAYMENT_DEDUCTED_ORDER_MISSING":
            if txn_ref:
                tools_to_run.append(("get_payment_details", {"order_id": txn_ref}))
            elif order_ref:
                tools_to_run.append(("get_payment_details", {"order_id": order_ref}))
            else:
                tools_to_run.append(("search_customer_history", {"customer_id": cust_id}))

        elif intent == "PAYMENT_FAILURE":
            if order_ref:
                tools_to_run.append(("get_payment_details", {"order_id": order_ref}))
                tools_to_run.append(("get_order_details", {"order_id": order_ref}))
            else:
                tools_to_run.append(("search_customer_history", {"customer_id": cust_id}))

        elif intent in ["REFUND_REQUEST", "RETURN_REQUEST"]:
            if order_ref:
                tools_to_run.append(("get_order_details", {"order_id": order_ref}))
            else:
                tools_to_run.append(("search_customer_history", {"customer_id": cust_id}))

        else:
            tools_to_run.append(("search_customer_history", {"customer_id": cust_id}))

        # Execute planned tools
        for tool_name, args in tools_to_run:
            tool = self.registry.get_tool(tool_name)
            if not tool:
                continue

            if on_tool_start:
                try:
                    on_tool_start(tool_name, args)
                except Exception as e:
                    logger.error(f"Error in on_tool_start callback: {e}")

            tool_res = tool.run(arguments=args, agent_run_id=agent_run_id, user_id=ctx.user_id)
            result.tools_executed.append({
                "tool": tool_name,
                "arguments": args,
                "result": tool_res
            })

            if on_tool_complete:
                try:
                    is_ok = tool_res.get("success", False)
                    err = tool_res.get("error") if not is_ok else None
                    on_tool_complete(tool_name, tool_res, is_ok, err)
                except Exception as e:
                    logger.error(f"Error in on_tool_complete callback: {e}")

            # Process evidence and state mutations
            if tool_name == "get_order_details" and tool_res.get("success"):
                result.order_details = tool_res
                result.evidence.append(
                    f"Order {tool_res.get('order_number')}: Status '{tool_res.get('status')}', "
                    f"Total ${tool_res.get('total_amount', 0.0):.2f}, Items: {len(tool_res.get('products', []))} items."
                )

            elif tool_name == "check_delivery_status" and tool_res.get("success"):
                result.tracking_details = tool_res
                result.is_delayed = tool_res.get("is_delayed", False)
                if result.is_delayed:
                    result.delay_evidence = tool_res.get("evidence")
                    result.evidence.append(tool_res.get("evidence", "Shipment delay detected."))
                else:
                    result.evidence.append(
                        f"Shipment {tool_res.get('tracking_number')} via {tool_res.get('courier_reference')}: "
                        f"Status '{tool_res.get('shipment_status')}'. Expected: {tool_res.get('expected_delivery_date')}."
                    )

            elif tool_name == "get_payment_details" and tool_res.get("success"):
                if tool_res.get("is_orphan"):
                    result.is_orphan_payment = True
                    result.orphan_payment_amount = tool_res.get("transaction_amount")
                    result.evidence.append(
                        f"Payment {tool_res.get('transaction_id')} for ${tool_res.get('transaction_amount', 0.0):.2f} "
                        f"was CAPTURED successfully, but no order confirmation exists (checkout session drop)."
                    )
                elif tool_res.get("payment_status") == "failed":
                    result.is_payment_failed = True
                    result.payment_failure_reason = tool_res.get("gateway_message")
                    result.evidence.append(
                        f"Payment {tool_res.get('transaction_id')} FAILED. Reason: {tool_res.get('gateway_message')}."
                    )
                else:
                    result.evidence.append(
                        f"Payment {tool_res.get('transaction_id')}: Status '{tool_res.get('payment_status')}', "
                        f"Amount ${tool_res.get('transaction_amount', 0.0):.2f} via {tool_res.get('payment_method')}."
                    )

            elif tool_name == "search_customer_history" and tool_res.get("success"):
                result.customer_history = tool_res.get("history")
                hist = tool_res.get("history", {})
                result.evidence.append(
                    f"Customer #{hist.get('customer_id')}: {hist.get('total_orders', 0)} total orders "
                    f"(${hist.get('total_spent', 0.0):.2f} lifetime value), {len(hist.get('support_tickets', []))} support tickets."
                )

        return result

