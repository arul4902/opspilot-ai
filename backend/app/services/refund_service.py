import json
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import (
    Order, RefundRequest, ApprovalRequest, AuditLog,
    OrderStatus, RefundStatus, PaymentStatus, UserRole
)
from backend.app.repositories.order_repository import OrderRepository
from backend.app.repositories.return_refund_repository import ReturnRefundRepository
from backend.app.schemas.return_refund import EligibilityCheckResponse, RefundRequestResponse
from backend.app.services.audit_service import AuditService


class RefundService:
    POLICY_RETURN_WINDOW_DAYS = 30

    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.refund_repo = ReturnRefundRepository(db)

    def check_eligibility(self, order_id: int) -> EligibilityCheckResponse:
        """
        Evaluate refund eligibility against enterprise operational policy:
        1. Order must exist and be settled.
        2. Delivery date must be within 30 days.
        3. Order must not already have an approved or processed refund.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            return EligibilityCheckResponse(
                order_id=order_id,
                order_number=f"ORD-{order_id}",
                eligible=False,
                reason="Order not found in database.",
                policy_reference="Standard Policy: Order Existence",
                requires_human_approval=True
            )

        # Check existing refunds
        existing_refunds = self.db.query(RefundRequest).filter(
            RefundRequest.order_id == order.id,
            RefundRequest.status.in_([RefundStatus.APPROVED.value, RefundStatus.PROCESSED.value, RefundStatus.PENDING_APPROVAL.value])
        ).first()

        if existing_refunds:
            return EligibilityCheckResponse(
                order_id=order.id,
                order_number=order.order_number,
                eligible=False,
                reason=f"An active or approved refund request already exists ({existing_refunds.refund_number}, status: {existing_refunds.status}).",
                policy_reference="Anti-Fraud Policy: Duplicate Refund Restriction",
                max_refund_amount=Decimal("0.00"),
                requires_human_approval=True
            )

        now = datetime.now(timezone.utc)
        delivery_date = order.estimated_delivery

        # Find actual delivery from shipment if available
        if order.shipments:
            for s in order.shipments:
                if s.actual_delivery:
                    delivery_date = s.actual_delivery
                    break

        if not delivery_date:
            delivery_date = order.order_date

        if delivery_date.tzinfo is None:
            delivery_date = delivery_date.replace(tzinfo=timezone.utc)

        days_since_delivery = (now - delivery_date).days

        if days_since_delivery > self.POLICY_RETURN_WINDOW_DAYS:
            return EligibilityCheckResponse(
                order_id=order.id,
                order_number=order.order_number,
                eligible=False,
                reason=(
                    f"Return policy exceeded: purchases must be requested within {self.POLICY_RETURN_WINDOW_DAYS} days "
                    f"of delivery. Delivery was {days_since_delivery} days ago."
                ),
                policy_reference="General Return Policy: Section 2.1 (30-Day Window)",
                delivery_date=delivery_date,
                days_since_delivery=days_since_delivery,
                max_refund_amount=Decimal("0.00"),
                requires_human_approval=True
            )

        # Eligible
        return EligibilityCheckResponse(
            order_id=order.id,
            order_number=order.order_number,
            eligible=True,
            reason=f"Order is eligible for refund (delivered {days_since_delivery} days ago, within 30-day window).",
            policy_reference="General Return Policy: Section 2.1 (30-Day Window)",
            delivery_date=delivery_date,
            days_since_delivery=days_since_delivery,
            max_refund_amount=order.total_amount,
            requires_human_approval=True
        )

    def initiate_refund(
        self,
        order_id: int,
        reason: str,
        amount: Optional[Decimal] = None,
        requested_by_user_id: Optional[int] = None,
        agent_run_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> RefundRequest:
        """
        Creates a simulated refund request in the database and registers a pending ApprovalRequest.
        All refunds are marked as simulated and require human operator review.
        """
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order ID {order_id} not found."
            )

        eligibility = self.check_eligibility(order_id)
        if not eligibility.eligible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ineligible for refund: {eligibility.reason}"
            )

        refund_amt = amount if amount and amount <= order.total_amount else order.total_amount

        # Find payment record if any
        payment_id = order.payments[0].id if order.payments else None

        # 1. Create Refund Request (status: pending_approval)
        refund = self.refund_repo.create_refund(
            order_id=order.id,
            customer_id=order.customer_id,
            amount=refund_amt,
            reason=reason,
            payment_id=payment_id,
            is_simulated=True
        )

        # 2. Create Human-In-The-Loop Approval Request
        payload = {
            "refund_request_id": refund.id,
            "refund_number": refund.refund_number,
            "order_number": order.order_number,
            "customer_id": order.customer_id,
            "customer_name": order.customer.name if order.customer else "N/A",
            "amount": float(refund_amt),
            "reason": reason,
            "is_simulated": True,
            "policy_check": eligibility.model_dump(mode="json")
        }
        approval = ApprovalRequest(
            agent_run_id=agent_run_id,
            order_id=order.id,
            request_type="refund",
            payload_json=json.dumps(payload),
            status="pending",
            requested_by_agent="OpsPilot Operations Engine",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(approval)
        self.db.commit()

        # 3. Audit Log
        AuditService.log_action(
            db=self.db,
            action="REFUND_INITIATED_PENDING_APPROVAL",
            entity_type="refund_request",
            entity_id=str(refund.id),
            user_id=requested_by_user_id,
            details=payload,
            ip_address=ip_address
        )

        return refund

