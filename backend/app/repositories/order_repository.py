from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from backend.app.models.models import Order, OrderItem, Product, Customer


class OrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, order_id: int) -> Optional[Order]:
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.items).joinedload(OrderItem.product),
                joinedload(Order.payments),
                joinedload(Order.shipments),
            )
            .filter(Order.id == order_id)
            .first()
        )

    def get_by_number(self, order_number: str) -> Optional[Order]:
        return (
            self.db.query(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.items).joinedload(OrderItem.product),
                joinedload(Order.payments),
                joinedload(Order.shipments),
            )
            .filter(Order.order_number == order_number.strip().upper())
            .first()
        )

    def list_orders(
        self,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Order], int]:
        query = self.db.query(Order).options(
            joinedload(Order.customer),
            joinedload(Order.items)
        )
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        if status:
            query = query.filter(Order.status == status)
        if start_date:
            query = query.filter(Order.order_date >= start_date)
        if end_date:
            query = query.filter(Order.order_date <= end_date)

        total = query.count()
        orders = query.order_by(Order.order_date.desc()).offset(skip).limit(limit).all()
        return orders, total

    def update_status(self, order_id: int, new_status: str) -> Optional[Order]:
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = new_status
            self.db.commit()
            self.db.refresh(order)
        return order
