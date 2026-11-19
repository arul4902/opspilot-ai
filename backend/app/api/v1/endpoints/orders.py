import random
from typing import Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user
from backend.app.models.models import User, UserRole, Customer, Order, OrderItem, OrderStatus
from backend.app.repositories.order_repository import OrderRepository
from backend.app.schemas.order import (
    OrderSummaryResponse,
    OrderDetailResponse,
    OrderItemResponse,
    OrderCreateRequest,
    OrderStatusUpdateRequest
)
from backend.app.core.broadcaster import EventBroadcaster

router = APIRouter()


def _get_customer_id_for_user(user: User, db: Session) -> Optional[int]:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer:
        return customer.id
    customer = db.query(Customer).filter(Customer.email == user.email).first()
    return customer.id if customer else None


@router.get("", response_model=List[OrderSummaryResponse])
def list_orders(
    status: Optional[str] = Query(None, description="Filter by status (pending, confirmed, processing, shipped, delivered, cancelled)"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID (Admins/Agents only)"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List orders with filtering and pagination.
    Customers are strictly restricted to their own orders.
    """
    order_repo = OrderRepository(db)

    # Customer authorization restriction
    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        if not cust_id:
            return []
        effective_customer_id = cust_id
    else:
        effective_customer_id = customer_id

    orders, _ = order_repo.list_orders(
        customer_id=effective_customer_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )

    results = []
    for o in orders:
        results.append(
            OrderSummaryResponse(
                id=o.id,
                order_number=o.order_number,
                customer_id=o.customer_id,
                order_date=o.order_date,
                status=o.status,
                total_amount=o.total_amount,
                currency=o.currency,
                shipping_address=o.shipping_address,
                estimated_delivery=o.estimated_delivery,
                created_at=o.created_at,
                customer_name=o.customer.name if o.customer else None,
                customer_email=o.customer.email if o.customer else None,
                item_count=len(o.items) if o.items else 0
            )
        )
    return results


@router.get("/{id}", response_model=OrderDetailResponse)
def get_order_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get full order details including line items, payment status, and shipment tracking.
    """
    order_repo = OrderRepository(db)
    order = order_repo.get_by_id(id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order ID {id} not found."
        )

    # Ownership check for customer role
    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        if order.customer_id != cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this order record."
            )

    items = [
        OrderItemResponse(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            product_name=item.product.name if item.product else None,
            product_sku=item.product.sku if item.product else None
        )
        for item in order.items
    ]

    payment = order.payments[0] if order.payments else None
    shipment = order.shipments[0] if order.shipments else None

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        customer_id=order.customer_id,
        order_date=order.order_date,
        status=order.status,
        total_amount=order.total_amount,
        currency=order.currency,
        shipping_address=order.shipping_address,
        estimated_delivery=order.estimated_delivery,
        created_at=order.created_at,
        customer_name=order.customer.name if order.customer else None,
        customer_email=order.customer.email if order.customer else None,
        item_count=len(order.items),
        items=items,
        has_active_shipment=shipment is not None,
        has_delayed_shipment=(shipment.status == "delayed") if shipment else False,
        payment_status=payment.status if payment else "unpaid",
        shipment_status=shipment.status if shipment else "unfulfilled",
        tracking_number=shipment.tracking_number if shipment else None
    )


@router.post("", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new real order in the operational database.
    Broadcasts real-time 'order.created' event via SSE to all active operator dashboards.
    """
    customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer ID {payload.customer_id} not found.")

    now = datetime.now(timezone.utc)
    order_num = f"ORD-2026-{random.randint(10000, 99999)}"

    total_amt = sum(item.unit_price * item.quantity for item in payload.items)

    new_order = Order(
        order_number=order_num,
        customer_id=payload.customer_id,
        order_date=now,
        status=OrderStatus.CONFIRMED.value,
        total_amount=total_amt,
        currency=payload.currency,
        shipping_address=payload.shipping_address,
        created_at=now
    )
    db.add(new_order)
    db.flush()

    for it in payload.items:
        line_item = OrderItem(
            order_id=new_order.id,
            product_id=it.product_id,
            quantity=it.quantity,
            unit_price=it.unit_price,
            total_price=it.unit_price * it.quantity
        )
        db.add(line_item)

    db.commit()
    db.refresh(new_order)

    # Broadcast real-time operational event to all connected consoles
    EventBroadcaster.broadcast("order.created", {
        "order_id": new_order.id,
        "order_number": new_order.order_number,
        "customer_id": new_order.customer_id,
        "customer_name": customer.name,
        "total_amount": float(new_order.total_amount),
        "status": new_order.status
    })

    return get_order_by_id(id=new_order.id, current_user=current_user, db=db)


@router.patch("/{id}/status", response_model=OrderDetailResponse)
def update_order_status(
    id: int,
    payload: OrderStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update order status in real time and broadcast 'order.updated' SSE event.
    """
    order = db.query(Order).filter(Order.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Order ID {id} not found.")

    old_status = order.status
    order.status = payload.status
    order.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(order)

    EventBroadcaster.broadcast("order.updated", {
        "order_id": order.id,
        "order_number": order.order_number,
        "old_status": old_status,
        "new_status": order.status,
        "updated_by": current_user.full_name
    })

    return get_order_by_id(id=order.id, current_user=current_user, db=db)


