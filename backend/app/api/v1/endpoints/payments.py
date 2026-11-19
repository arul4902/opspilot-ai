from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, Customer
from backend.app.repositories.payment_repository import PaymentRepository
from backend.app.services.payment_service import PaymentService
from backend.app.schemas.payment import PaymentResponse, PaymentInvestigationResponse

router = APIRouter()


def _get_customer_id_for_user(user: User, db: Session) -> Optional[int]:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer:
        return customer.id
    customer = db.query(Customer).filter(Customer.email == user.email).first()
    return customer.id if customer else None


@router.get("", response_model=List[PaymentResponse])
def list_payments(
    status: Optional[str] = Query(None),
    order_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List payments with filtering.
    Customers can only view their own payments.
    """
    payment_repo = PaymentRepository(db)

    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        if not cust_id:
            return []
        effective_customer_id = cust_id
    else:
        effective_customer_id = customer_id

    payments, _ = payment_repo.list_payments(
        customer_id=effective_customer_id,
        order_id=order_id,
        status=status,
        skip=skip,
        limit=limit
    )

    return [
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
            is_orphan=(p.order_id is None and p.status == "successful")
        )
        for p in payments
    ]


@router.get("/{id}", response_model=PaymentResponse)
def get_payment_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Retrieve payment details by ID.
    """
    payment_repo = PaymentRepository(db)
    p = payment_repo.get_by_id(id)
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment ID {id} not found."
        )

    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        if p.customer_id != cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this payment record."
            )

    return PaymentResponse(
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
        is_orphan=(p.order_id is None and p.status == "successful")
    )


@router.get("/investigate/customer/{customer_id}", response_model=PaymentInvestigationResponse)
def investigate_customer_payments(
    customer_id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
) -> Any:
    """
    Operations Agent & Admin endpoint: Runs automated investigation across customer payment history
    to detect orphan charges, declines, and duplicate deductions.
    """
    svc = PaymentService(db)
    return svc.investigate_payment(customer_id=customer_id)

