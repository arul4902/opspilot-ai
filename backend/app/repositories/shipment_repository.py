from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from backend.app.models.models import Shipment, Order, Customer


class ShipmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, shipment_id: int) -> Optional[Shipment]:
        return (
            self.db.query(Shipment)
            .options(
                joinedload(Shipment.order).joinedload(Order.customer)
            )
            .filter(Shipment.id == shipment_id)
            .first()
        )

    def get_by_tracking_number(self, tracking_number: str) -> Optional[Shipment]:
        return (
            self.db.query(Shipment)
            .options(
                joinedload(Shipment.order).joinedload(Order.customer)
            )
            .filter(Shipment.tracking_number == tracking_number.strip().upper())
            .first()
        )

    def get_by_order_id(self, order_id: int) -> Optional[Shipment]:
        return (
            self.db.query(Shipment)
            .options(
                joinedload(Shipment.order).joinedload(Order.customer)
            )
            .filter(Shipment.order_id == order_id)
            .first()
        )

    def list_shipments(
        self,
        status: Optional[str] = None,
        courier: Optional[str] = None,
        order_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Shipment], int]:
        query = self.db.query(Shipment).options(
            joinedload(Shipment.order).joinedload(Order.customer)
        )
        if status:
            query = query.filter(Shipment.status == status)
        if courier:
            query = query.filter(Shipment.courier_name == courier)
        if order_id:
            query = query.filter(Shipment.order_id == order_id)

        total = query.count()
        shipments = query.order_by(Shipment.created_at.desc()).offset(skip).limit(limit).all()
        return shipments, total

