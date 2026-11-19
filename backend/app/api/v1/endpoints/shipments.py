import json
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, Customer
from backend.app.repositories.shipment_repository import ShipmentRepository
from backend.app.services.delivery_service import DeliveryService
from backend.app.schemas.shipment import ShipmentResponse, DeliveryInvestigationResponse

router = APIRouter()


def _get_customer_id_for_user(user: User, db: Session) -> Optional[int]:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer:
        return customer.id
    customer = db.query(Customer).filter(Customer.email == user.email).first()
    return customer.id if customer else None


@router.get("", response_model=List[ShipmentResponse])
def list_shipments(
    status: Optional[str] = Query(None),
    courier: Optional[str] = Query(None),
    order_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List shipments and their tracking statuses.
    """
    shipment_repo = ShipmentRepository(db)
    shipments, _ = shipment_repo.list_shipments(
        status=status,
        courier=courier,
        order_id=order_id,
        skip=skip,
        limit=limit
    )

    cust_id = _get_customer_id_for_user(current_user, db) if current_user.role == UserRole.CUSTOMER.value else None

    results = []
    for s in shipments:
        # Ownership check for customer
        if current_user.role == UserRole.CUSTOMER.value:
            if s.order and s.order.customer_id != cust_id:
                continue

        try:
            events = json.loads(s.tracking_events_json) if s.tracking_events_json else []
        except Exception:
            events = []

        results.append(
            ShipmentResponse(
                id=s.id,
                tracking_number=s.tracking_number,
                order_id=s.order_id,
                courier_name=s.courier_name,
                status=s.status,
                estimated_delivery=s.estimated_delivery,
                actual_delivery=s.actual_delivery,
                tracking_events=events,
                created_at=s.created_at,
                order_number=s.order.order_number if s.order else None,
                customer_id=s.order.customer_id if s.order else None,
                customer_name=s.order.customer.name if (s.order and s.order.customer) else None,
                is_delayed=(s.status == "delayed"),
                delay_reason="Weather delay at transit hub" if s.status == "delayed" else None
            )
        )
    return results


@router.get("/{id}", response_model=ShipmentResponse)
def get_shipment_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get detailed shipment record including chronological tracking events.
    """
    shipment_repo = ShipmentRepository(db)
    s = shipment_repo.get_by_id(id)
    if not s:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment ID {id} not found."
        )

    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        if s.order and s.order.customer_id != cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this shipment record."
            )

    try:
        events = json.loads(s.tracking_events_json) if s.tracking_events_json else []
    except Exception:
        events = []

    return ShipmentResponse(
        id=s.id,
        tracking_number=s.tracking_number,
        order_id=s.order_id,
        courier_name=s.courier_name,
        status=s.status,
        estimated_delivery=s.estimated_delivery,
        actual_delivery=s.actual_delivery,
        tracking_events=events,
        created_at=s.created_at,
        order_number=s.order.order_number if s.order else None,
        customer_id=s.order.customer_id if s.order else None,
        customer_name=s.order.customer.name if (s.order and s.order.customer) else None,
        is_delayed=(s.status == "delayed"),
        delay_reason="Weather delay at transit hub" if s.status == "delayed" else None
    )


@router.get("/investigate/order/{order_id}", response_model=DeliveryInvestigationResponse)
def investigate_order_delivery(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Investigate delivery delay and tracking status for an order.
    Returns grounded evidence, delay cause, and operational next steps.
    """
    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        # Verify customer owns the order
        from backend.app.repositories.order_repository import OrderRepository
        order = OrderRepository(db).get_by_id(order_id)
        if not order or order.customer_id != cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to investigate this order."
            )

    delivery_svc = DeliveryService(db)
    return delivery_svc.investigate_delivery(order_id)

