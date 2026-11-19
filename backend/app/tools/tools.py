from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from backend.app.tools.base import BaseTool
from backend.app.tools.schemas import (
    GetOrderDetailsInput, GetOrderDetailsOutput, OrderItemSummary,
    GetPaymentDetailsInput, GetPaymentDetailsOutput,
    CheckDeliveryStatusInput, CheckDeliveryStatusOutput,
    SearchReturnPolicyInput, SearchReturnPolicyOutput, PolicyCitation,
    CreateReturnRequestInput, CreateReturnRequestOutput,
    InitiateRefundRequestInput, InitiateRefundRequestOutput,
    CreateSupportTicketInput, CreateSupportTicketOutput,
    EscalateToHumanInput, EscalateToHumanOutput,
    SearchCustomerHistoryInput, SearchCustomerHistoryOutput, CustomerHistorySummary
)
from backend.app.repositories.order_repository import OrderRepository
from backend.app.repositories.payment_repository import PaymentRepository
from backend.app.repositories.ticket_repository import TicketRepository
from backend.app.repositories.return_refund_repository import ReturnRefundRepository
from backend.app.services.delivery_service import DeliveryService
from backend.app.services.refund_service import RefundService
from backend.app.rag.service import RAGService
from backend.app.models.models import Customer, Escalation, Order, Payment, SupportTicket, ApprovalRequest


# TOOL 1: get_order_details
class GetOrderDetailsTool(BaseTool):
    name = "get_order_details"
    description = "Retrieve full order details, customer ID, items, status, amount, and estimated delivery date."
    input_schema = GetOrderDetailsInput
    output_schema = GetOrderDetailsOutput

    def _execute(self, input_data: GetOrderDetailsInput, agent_run_id=None, user_id=None) -> GetOrderDetailsOutput:
        order_repo = OrderRepository(self.db)
        val = input_data.order_id.strip()
        order = order_repo.get_by_id(int(val)) if val.isdigit() else order_repo.get_by_number(val)

        if not order:
            return GetOrderDetailsOutput(
                success=False,
                order_id=0,
                order_number=val,
                customer_id=0,
                status="NOT_FOUND",
                total_amount=0.0,
                message=f"Order '{val}' not found in database."
            )

        products = [
            OrderItemSummary(
                product_name=item.product.name if item.product else "Unknown Product",
                product_sku=item.product.sku if item.product else "N/A",
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                total_price=float(item.total_price)
            )
            for item in order.items
        ]

        return GetOrderDetailsOutput(
            success=True,
            order_id=order.id,
            order_number=order.order_number,
            customer_id=order.customer_id,
            customer_name=order.customer.name if order.customer else None,
            order_date=order.order_date.isoformat(),
            status=order.status,
            total_amount=float(order.total_amount),
            currency=order.currency,
            estimated_delivery=order.estimated_delivery.isoformat() if order.estimated_delivery else None,
            products=products,
            message="Order details retrieved successfully."
        )


# TOOL 2: get_payment_details
class GetPaymentDetailsTool(BaseTool):
    name = "get_payment_details"
    description = "Retrieve transaction ID, payment method, amount, status, date, and gateway response for an order or transaction reference."
    input_schema = GetPaymentDetailsInput
    output_schema = GetPaymentDetailsOutput

    def _execute(self, input_data: GetPaymentDetailsInput, agent_run_id=None, user_id=None) -> GetPaymentDetailsOutput:
        payment_repo = PaymentRepository(self.db)
        val = input_data.order_id.strip()

        # Check if transaction reference
        if val.upper().startswith("TXN-"):
            pay = payment_repo.get_by_reference(val)
        elif val.isdigit():
            pays = payment_repo.get_by_order_id(int(val))
            pay = pays[0] if pays else None
        else:
            order_repo = OrderRepository(self.db)
            order = order_repo.get_by_number(val)
            pay = order.payments[0] if (order and order.payments) else None

        if not pay:
            return GetPaymentDetailsOutput(
                success=False,
                message=f"No payment record found for '{val}'."
            )

        return GetPaymentDetailsOutput(
            success=True,
            transaction_id=pay.transaction_reference,
            order_id=pay.order_id,
            order_number=pay.order.order_number if pay.order else None,
            payment_method=pay.payment_method,
            transaction_amount=float(pay.amount),
            currency=pay.currency,
            payment_status=pay.status,
            transaction_date=pay.transaction_date.isoformat(),
            gateway_message=pay.gateway_response,
            is_orphan=(pay.order_id is None and pay.status == "successful"),
            message="Payment details retrieved successfully."
        )


# TOOL 3: check_delivery_status
class CheckDeliveryStatusTool(BaseTool):
    name = "check_delivery_status"
    description = "Inspect shipment tracking status, courier name, tracking number, expected delivery date, and latest tracking event for an order."
    input_schema = CheckDeliveryStatusInput
    output_schema = CheckDeliveryStatusOutput

    def _execute(self, input_data: CheckDeliveryStatusInput, agent_run_id=None, user_id=None) -> CheckDeliveryStatusOutput:
        svc = DeliveryService(self.db)
        investigation = svc.investigate_delivery(input_data.order_id)

        return CheckDeliveryStatusOutput(
            success=investigation.current_status != "ORDER_NOT_FOUND",
            order_id=investigation.order_id,
            order_number=investigation.order_number,
            tracking_number=investigation.tracking_number,
            courier_reference=investigation.courier,
            shipment_status=investigation.current_status,
            expected_delivery_date=investigation.estimated_delivery.isoformat() if investigation.estimated_delivery else None,
            actual_delivery_date=investigation.actual_delivery.isoformat() if investigation.actual_delivery else None,
            is_delayed=investigation.is_delayed,
            latest_tracking_event=investigation.latest_event,
            delay_cause=investigation.delay_cause,
            evidence=investigation.evidence
        )


# TOOL 4: search_return_policy
class SearchReturnPolicyTool(BaseTool):
    name = "search_return_policy"
    description = "Search enterprise knowledge base for return, refund, replacement, and warranty policies."
    input_schema = SearchReturnPolicyInput
    output_schema = SearchReturnPolicyOutput

    # Curated enterprise policies for source grounding
    CURATED_POLICIES = [
        {
            "section": "Section 2.1: General Return Window",
            "source": "E-Commerce Return & Refund Policy (POL-RET-2026.pdf)",
            "content": "Customers are eligible to return physical items within 30 calendar days from the verified delivery date. Items must be in original condition with packaging.",
            "keywords": ["return", "refund", "window", "30 days", "time limit", "eligible", "eligibility"]
        },
        {
            "section": "Section 3.4: Damaged or Defective Items",
            "source": "Quality Assurance & Replacement Policy (POL-QA-2026.pdf)",
            "content": "If a product arrives damaged, defective, or with a broken seal, the customer is entitled to an immediate replacement or full refund upon submitting photo evidence within 14 days of receipt.",
            "keywords": ["damaged", "broken", "defective", "cracked", "faulty", "replacement"]
        },
        {
            "section": "Section 4.2: Delivery Delays & SLA Breaches",
            "source": "Logistics & Shipping Guarantee Policy (POL-LOG-2026.pdf)",
            "content": "Deliveries delayed by more than 3 business days past the estimated delivery date due to courier exceptions or severe weather qualify for a $10 courtesy credit or free expedited reshipment.",
            "keywords": ["delay", "delayed", "weather", "blizzard", "late", "sla", "courtesy credit", "reshipment"]
        },
        {
            "section": "Section 5.1: Payment Discrepancies & Orphan Charges",
            "source": "Payment Operations & Fraud Policy (POL-PAY-2026.pdf)",
            "content": "If funds are deducted from a customer's account without an order confirmation being generated (checkout session drop), operations must verify the bank gateway authorization code and initiate an automated refund or manual order creation within 24 hours.",
            "keywords": ["deducted", "orphan", "missing order", "payment", "charged", "authorization", "session"]
        },
        {
            "section": "Section 6.3: Non-Returnable & Final Sale Items",
            "source": "E-Commerce Return & Refund Policy (POL-RET-2026.pdf)",
            "content": "Digital downloads, gift cards, and clearance items marked 'Final Sale' are strictly non-refundable once transaction is completed.",
            "keywords": ["final sale", "digital", "gift card", "clearance", "non-refundable"]
        }
    ]

    def _execute(self, input_data: SearchReturnPolicyInput, agent_run_id=None, user_id=None) -> SearchReturnPolicyOutput:
        q_lower = input_data.query.lower()
        matched_citations: List[PolicyCitation] = []

        # 1. Curated exact policy rule grounding
        for p in self.CURATED_POLICIES:
            matches = sum(1 for kw in p["keywords"] if kw in q_lower)
            if matches > 0 or any(word in p["content"].lower() for word in q_lower.split() if len(word) > 3):
                relevance = min(0.98, 0.70 + (matches * 0.10))
                matched_citations.append(
                    PolicyCitation(
                        section=p["section"],
                        source_document=p["source"],
                        snippet=p["content"],
                        relevance_score=relevance
                    )
                )

        # 2. ChromaDB vector retrieval for deep semantic knowledge search
        try:
            rag_svc = RAGService(self.db)
            vector_results = rag_svc.search(query=input_data.query, top_k=3, min_score=0.25)
            for vr in vector_results:
                if not any(vr["snippet"][:40] in c.snippet for c in matched_citations):
                    matched_citations.append(
                        PolicyCitation(
                            section=vr["section"],
                            source_document=vr["source_document"],
                            snippet=vr["snippet"],
                            relevance_score=vr["relevance_score"]
                        )
                    )
        except Exception:
            pass

        if not matched_citations:
            default_p = self.CURATED_POLICIES[0]
            matched_citations.append(
                PolicyCitation(
                    section=default_p["section"],
                    source_document=default_p["source"],
                    snippet=default_p["content"],
                    relevance_score=0.75
                )
            )

        matched_citations.sort(key=lambda x: x.relevance_score, reverse=True)
        summary = " ".join([c.snippet for c in matched_citations[:2]])

        return SearchReturnPolicyOutput(
            success=True,
            query=input_data.query,
            citations=matched_citations[:3],
            policy_summary=summary
        )


# TOOL 5: create_return_request
class CreateReturnRequestTool(BaseTool):
    name = "create_return_request"
    description = "Validate return eligibility and create an official return request in the database."
    input_schema = CreateReturnRequestInput
    output_schema = CreateReturnRequestOutput

    def _execute(self, input_data: CreateReturnRequestInput, agent_run_id=None, user_id=None) -> CreateReturnRequestOutput:
        val = input_data.order_id.strip()
        order_repo = OrderRepository(self.db)
        order = order_repo.get_by_id(int(val)) if val.isdigit() else order_repo.get_by_number(val)

        if not order:
            return CreateReturnRequestOutput(
                success=False,
                order_id=0,
                status="FAILED",
                eligible=False,
                eligibility_reason="Order not found.",
                message="Cannot create return request for nonexistent order."
            )

        # Validate eligibility
        refund_svc = RefundService(self.db)
        eligibility = refund_svc.check_eligibility(order.id)
        if not eligibility.eligible:
            return CreateReturnRequestOutput(
                success=False,
                order_id=order.id,
                status="INELIGIBLE",
                eligible=False,
                eligibility_reason=eligibility.reason,
                message=f"Return request rejected: {eligibility.reason}"
            )

        ret_repo = ReturnRefundRepository(self.db)
        ret = ret_repo.create_return(
            order_id=order.id,
            customer_id=order.customer_id,
            reason=input_data.reason
        )

        return CreateReturnRequestOutput(
            success=True,
            return_request_number=ret.request_number,
            order_id=order.id,
            status=ret.status,
            eligible=True,
            eligibility_reason=eligibility.reason,
            message=f"Return request {ret.request_number} created successfully. Return shipping label will be generated."
        )


# TOOL 6: initiate_refund_request
class InitiateRefundRequestTool(BaseTool):
    name = "initiate_refund_request"
    description = "Validate refund policy, create a simulated refund request record, and submit an approval request to the operations queue."
    input_schema = InitiateRefundRequestInput
    output_schema = InitiateRefundRequestOutput

    def _execute(self, input_data: InitiateRefundRequestInput, agent_run_id=None, user_id=None) -> InitiateRefundRequestOutput:
        val = input_data.order_id.strip()
        order_repo = OrderRepository(self.db)
        order = order_repo.get_by_id(int(val)) if val.isdigit() else order_repo.get_by_number(val)

        if not order:
            return InitiateRefundRequestOutput(
                success=False,
                order_id=0,
                amount=0.0,
                status="FAILED",
                is_simulated=True,
                requires_approval=True,
                message=f"Order '{val}' not found in database."
            )

        amt_decimal = Decimal(str(input_data.amount)) if input_data.amount else order.total_amount
        refund_svc = RefundService(self.db)

        try:
            refund = refund_svc.initiate_refund(
                order_id=order.id,
                reason=input_data.reason,
                amount=amt_decimal,
                requested_by_user_id=user_id,
                agent_run_id=agent_run_id
            )

            approval = self.db.query(ApprovalRequest).filter(
                ApprovalRequest.order_id == order.id,
                ApprovalRequest.status == "pending"
            ).order_by(ApprovalRequest.created_at.desc()).first()

            return InitiateRefundRequestOutput(
                success=True,
                refund_number=refund.refund_number,
                order_id=order.id,
                amount=float(refund.amount),
                status=refund.status,
                is_simulated=True,
                requires_approval=True,
                approval_request_id=approval.id if approval else None,
                message=(
                    f"SIMULATION: Refund request {refund.refund_number} for ${float(refund.amount):.2f} "
                    f"has been initiated and is PENDING APPROVAL by a human operations manager."
                )
            )
        except Exception as e:
            # Check if an existing approval request is already pending for this order
            existing_approval = self.db.query(ApprovalRequest).filter(
                ApprovalRequest.order_id == order.id,
                ApprovalRequest.status == "pending"
            ).order_by(ApprovalRequest.created_at.desc()).first()

            if existing_approval:
                return InitiateRefundRequestOutput(
                    success=True,
                    refund_number=f"REF-{order.order_number}",
                    order_id=order.id,
                    amount=float(amt_decimal),
                    status="pending_approval",
                    is_simulated=True,
                    requires_approval=True,
                    approval_request_id=existing_approval.id,
                    message=(
                        f"SIMULATION: An existing refund request for order {order.order_number} (${float(amt_decimal):.2f}) "
                        f"is already PENDING APPROVAL (Approval ID #{existing_approval.id})."
                    )
                )

            return InitiateRefundRequestOutput(
                success=False,
                order_id=order.id,
                amount=float(amt_decimal),
                status="FAILED",
                is_simulated=True,
                requires_approval=True,
                message=f"Failed to initiate refund: {str(e)}"
            )


# TOOL 7: create_support_ticket
class CreateSupportTicketTool(BaseTool):
    name = "create_support_ticket"
    description = "Create an official support ticket record in the database for tracking unresolved customer inquiries."
    input_schema = CreateSupportTicketInput
    output_schema = CreateSupportTicketOutput

    def _execute(self, input_data: CreateSupportTicketInput, agent_run_id=None, user_id=None) -> CreateSupportTicketOutput:
        ticket_repo = TicketRepository(self.db)
        order_id_int = None
        if input_data.order_id:
            val = input_data.order_id.strip()
            if val.isdigit():
                order_id_int = int(val)
            else:
                ord_rec = OrderRepository(self.db).get_by_number(val)
                if ord_rec:
                    order_id_int = ord_rec.id

        ticket = ticket_repo.create(
            customer_id=input_data.customer_id,
            subject=input_data.subject,
            description=input_data.description,
            priority=input_data.priority,
            order_id=order_id_int
        )

        return CreateSupportTicketOutput(
            success=True,
            ticket_id=ticket.id,
            ticket_number=ticket.ticket_number,
            customer_id=ticket.customer_id,
            subject=ticket.subject,
            priority=ticket.priority,
            status=ticket.status,
            created_at=ticket.created_at.isoformat(),
            message=f"Support ticket {ticket.ticket_number} created with priority '{ticket.priority}'."
        )


# TOOL 8: escalate_to_human
class EscalateToHumanTool(BaseTool):
    name = "escalate_to_human"
    description = "Escalate a complex, disputed, or high-urgency issue to the human operations queue."
    input_schema = EscalateToHumanInput
    output_schema = EscalateToHumanOutput

    def _execute(self, input_data: EscalateToHumanInput, agent_run_id=None, user_id=None) -> EscalateToHumanOutput:
        escalation = Escalation(
            conversation_id=input_data.conversation_id,
            customer_id=input_data.customer_id,
            reason=input_data.reason,
            priority=input_data.priority,
            status="pending",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        self.db.add(escalation)
        self.db.commit()
        self.db.refresh(escalation)

        return EscalateToHumanOutput(
            success=True,
            escalation_id=escalation.id,
            queue_name="Operations Specialist Intervention Queue",
            priority=escalation.priority,
            status=escalation.status,
            message=f"Issue successfully escalated to human operations team (Escalation ID #{escalation.id}). An agent will review shortly."
        )


# TOOL 9: search_customer_history
class SearchCustomerHistoryTool(BaseTool):
    name = "search_customer_history"
    description = "Retrieve customer profile, order history, transaction records, and prior support interactions."
    input_schema = SearchCustomerHistoryInput
    output_schema = SearchCustomerHistoryOutput

    def _execute(self, input_data: SearchCustomerHistoryInput, agent_run_id=None, user_id=None) -> SearchCustomerHistoryOutput:
        customer = self.db.query(Customer).filter(Customer.id == input_data.customer_id).first()
        if not customer:
            return SearchCustomerHistoryOutput(
                success=False,
                customer_id=input_data.customer_id,
                message=f"Customer ID {input_data.customer_id} not found."
            )

        orders = self.db.query(Order).filter(Order.customer_id == customer.id).order_by(Order.order_date.desc()).limit(5).all()
        payments = self.db.query(Payment).filter(Payment.customer_id == customer.id).order_by(Payment.transaction_date.desc()).limit(5).all()
        open_tickets = self.db.query(SupportTicket).filter(
            SupportTicket.customer_id == customer.id,
            SupportTicket.status.in_(["open", "in_progress", "waiting_customer"])
        ).count()

        summary = CustomerHistorySummary(
            customer_id=customer.id,
            customer_code=customer.customer_code,
            name=customer.name,
            email=customer.email,
            tier=customer.tier,
            total_orders=len(customer.orders),
            open_tickets=open_tickets,
            recent_orders=[
                {"id": o.id, "order_number": o.order_number, "status": o.status, "total_amount": float(o.total_amount), "order_date": o.order_date.isoformat()}
                for o in orders
            ],
            recent_payments=[
                {"id": p.id, "reference": p.transaction_reference, "status": p.status, "amount": float(p.amount), "method": p.payment_method, "date": p.transaction_date.isoformat()}
                for p in payments
            ]
        )

        return SearchCustomerHistoryOutput(
            success=True,
            customer_id=customer.id,
            history=summary,
            message="Customer historical profile retrieved successfully."
        )

