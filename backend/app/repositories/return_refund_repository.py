from typing import List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from backend.app.models.models import ReturnRequest, RefundRequest, Order, Customer, Payment


class ReturnRefundRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_return_by_id(self, return_id: int) -> Optional[ReturnRequest]:
        return (
            self.db.query(ReturnRequest)
            .options(
                joinedload(ReturnRequest.order).joinedload(Order.customer),
                joinedload(ReturnRequest.customer)
            )
            .filter(ReturnRequest.id == return_id)
            .first()
        )

    def list_returns(
        self,
        customer_id: Optional[int] = None,
        order_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ReturnRequest], int]:
        query = self.db.query(ReturnRequest).options(
            joinedload(ReturnRequest.order),
            joinedload(ReturnRequest.customer)
        )
        if customer_id:
            query = query.filter(ReturnRequest.customer_id == customer_id)
        if order_id:
            query = query.filter(ReturnRequest.order_id == order_id)
        if status:
            query = query.filter(ReturnRequest.status == status)

        total = query.count()
        returns = query.order_by(ReturnRequest.created_at.desc()).offset(skip).limit(limit).all()
        return returns, total

    def create_return(
        self,
        order_id: int,
        customer_id: int,
        reason: str
    ) -> ReturnRequest:
        count = self.db.query(ReturnRequest).count() + 1
        req_number = f"RET-2024-{count:04d}"
        ret = ReturnRequest(
            request_number=req_number,
            order_id=order_id,
            customer_id=customer_id,
            reason=reason.strip(),
            status="requested",
            requested_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(ret)
        self.db.commit()
        self.db.refresh(ret)
        return ret

    def get_refund_by_id(self, refund_id: int) -> Optional[RefundRequest]:
        return (
            self.db.query(RefundRequest)
            .options(
                joinedload(RefundRequest.order),
                joinedload(RefundRequest.customer),
                joinedload(RefundRequest.payment)
            )
            .filter(RefundRequest.id == refund_id)
            .first()
        )

    def list_refunds(
        self,
        customer_id: Optional[int] = None,
        order_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[RefundRequest], int]:
        query = self.db.query(RefundRequest).options(
            joinedload(RefundRequest.order),
            joinedload(RefundRequest.customer),
            joinedload(RefundRequest.payment)
        )
        if customer_id:
            query = query.filter(RefundRequest.customer_id == customer_id)
        if order_id:
            query = query.filter(RefundRequest.order_id == order_id)
        if status:
            query = query.filter(RefundRequest.status == status)

        total = query.count()
        refunds = query.order_by(RefundRequest.created_at.desc()).offset(skip).limit(limit).all()
        return refunds, total

    def create_refund(
        self,
        order_id: int,
        customer_id: int,
        amount: Decimal,
        reason: str,
        payment_id: Optional[int] = None,
        is_simulated: bool = True
    ) -> RefundRequest:
        count = self.db.query(RefundRequest).count() + 1
        ref_number = f"REF-2024-{count:04d}"
        refund = RefundRequest(
            refund_number=ref_number,
            order_id=order_id,
            payment_id=payment_id,
            customer_id=customer_id,
            amount=amount,
            reason=reason.strip(),
            status="pending_approval",
            is_simulated=is_simulated,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(refund)
        self.db.commit()
        self.db.refresh(refund)
        return refund

