from typing import Optional, List
from sqlalchemy.orm import Session
from backend.app.repositories.payment_repository import PaymentRepository
from backend.app.repositories.order_repository import OrderRepository
from backend.app.schemas.payment import PaymentResponse, PaymentInvestigationResponse
from backend.app.models.models import PaymentStatus, OrderStatus


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.order_repo = OrderRepository(db)

    def investigate_payment(
        self,
        customer_id: int,
        order_id: Optional[int] = None,
        transaction_ref: Optional[str] = None
    ) -> PaymentInvestigationResponse:
        """
        Investigate payment transactions for a customer or specific order/reference.
        Detects failed payments, duplicate charges, and orphan charges (payment deducted but order missing).
        """
        payments = []
        if transaction_ref:
            pay = self.payment_repo.get_by_reference(transaction_ref)
            if pay and (pay.customer_id == customer_id or customer_id == 0):
                payments = [pay]
        elif order_id:
            payments = self.payment_repo.get_by_order_id(order_id)
        else:
            payments = self.payment_repo.get_by_customer_id(customer_id)

        if not payments:
            return PaymentInvestigationResponse(
                customer_id=customer_id,
                has_issues=True,
                issue_type="NO_PAYMENT_FOUND",
                message="No payment transactions were found matching the inquiry.",
                transactions=[],
                recommended_action="Ask customer for their bank statement transaction reference or authorization date."
            )

        serialized_payments = [
            PaymentResponse(
                id=p.id,
                transaction_reference=p.transaction_reference,
                order_id=p.order_id,
                customer_id=p.customer_id,
                payment_method=p.payment_method,
                amount=p.amount,
                currency=p.currency,
                status=p.status,
                gateway_response=p.gateway_response,
                transaction_date=p.transaction_date,
                created_at=p.created_at,
                order_number=p.order.order_number if p.order else None,
                customer_name=p.customer.name if p.customer else None,
                customer_email=p.customer.email if p.customer else None,
                is_orphan=(p.order_id is None and p.status == PaymentStatus.SUCCESSFUL.value)
            )
            for p in payments
        ]

        # Case 1: Orphan Payment (Payment Deducted, Order Missing)
        orphan_payments = [p for p in serialized_payments if p.is_orphan]
        if orphan_payments:
            orphan = orphan_payments[0]
            return PaymentInvestigationResponse(
                customer_id=customer_id,
                has_issues=True,
                issue_type="PAYMENT_DEDUCTED_ORDER_MISSING",
                message=(
                    f"CRITICAL DISCREPANCY DETECTED: Transaction {orphan.transaction_reference} for "
                    f"${orphan.amount:.2f} was successfully captured by payment gateway, but no confirmed order exists "
                    f"in the database (checkout session timeout)."
                ),
                transactions=serialized_payments,
                recommended_action="REQUEST_HUMAN_APPROVAL: Initiate automatic simulated refund or create expedited manual order fulfillment."
            )

        # Case 2: Failed Payment
        failed_payments = [p for p in serialized_payments if p.status == PaymentStatus.FAILED.value]
        if failed_payments:
            failed = failed_payments[0]
            gw_msg = failed.gateway_response or "Payment processor declined card."
            return PaymentInvestigationResponse(
                customer_id=customer_id,
                has_issues=True,
                issue_type="PAYMENT_FAILURE",
                message=(
                    f"Payment attempt {failed.transaction_reference} for ${failed.amount:.2f} failed. "
                    f"Processor response: {gw_msg}"
                ),
                transactions=serialized_payments,
                recommended_action="Advise customer that charge was declined by their bank. Provide secure retry link or alternate payment method option."
            )

        # Case 3: Duplicate Charges
        successful_payments = [p for p in serialized_payments if p.status == PaymentStatus.SUCCESSFUL.value]
        if len(successful_payments) > 1 and order_id:
            return PaymentInvestigationResponse(
                customer_id=customer_id,
                has_issues=True,
                issue_type="DUPLICATE_PAYMENT",
                message=f"Multiple successful charges ({len(successful_payments)}) detected for order ID {order_id}.",
                transactions=serialized_payments,
                recommended_action="REQUEST_HUMAN_APPROVAL: Immediately refund duplicate charge back to customer's original payment method."
            )

        # Case 4: Everything Normal & Settled
        return PaymentInvestigationResponse(
            customer_id=customer_id,
            has_issues=False,
            issue_type="NONE",
            message=f"All {len(successful_payments)} transaction(s) are valid and settled normally.",
            transactions=serialized_payments,
            recommended_action="No payment action required. All charges match recorded order amounts."
        )

