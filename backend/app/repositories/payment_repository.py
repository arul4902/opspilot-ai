from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from backend.app.models.models import Payment, Order, Customer


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, payment_id: int) -> Optional[Payment]:
        return (
            self.db.query(Payment)
            .options(
                joinedload(Payment.customer),
                joinedload(Payment.order)
            )
            .filter(Payment.id == payment_id)
            .first()
        )

    def get_by_reference(self, reference: str) -> Optional[Payment]:
        return (
            self.db.query(Payment)
            .options(
                joinedload(Payment.customer),
                joinedload(Payment.order)
            )
            .filter(Payment.transaction_reference == reference.strip().upper())
            .first()
        )

    def get_by_order_id(self, order_id: int) -> List[Payment]:
        return (
            self.db.query(Payment)
            .options(joinedload(Payment.customer))
            .filter(Payment.order_id == order_id)
            .all()
        )

    def get_by_customer_id(self, customer_id: int) -> List[Payment]:
        return (
            self.db.query(Payment)
            .options(joinedload(Payment.order))
            .filter(Payment.customer_id == customer_id)
            .order_by(Payment.transaction_date.desc())
            .all()
        )

    def list_payments(
        self,
        customer_id: Optional[int] = None,
        order_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Payment], int]:
        query = self.db.query(Payment).options(
            joinedload(Payment.customer),
            joinedload(Payment.order)
        )
        if customer_id:
            query = query.filter(Payment.customer_id == customer_id)
        if order_id:
            query = query.filter(Payment.order_id == order_id)
        if status:
            query = query.filter(Payment.status == status)

        total = query.count()
        payments = query.order_by(Payment.transaction_date.desc()).offset(skip).limit(limit).all()
        return payments, total

