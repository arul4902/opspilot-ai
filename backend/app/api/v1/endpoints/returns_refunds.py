from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, Customer
from backend.app.repositories.return_refund_repository import ReturnRefundRepository
from backend.app.repositories.order_repository import OrderRepository
from backend.app.services.refund_service import RefundService
from backend.app.schemas.return_refund import (
    ReturnRequestCreate,
    ReturnRequestResponse,
    RefundRequestCreate,
    RefundRequestResponse,
    EligibilityCheckResponse,
)

router = APIRouter()


def _get_customer_id_for_user(user: User, db: Session) -> Optional[int]:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer:
        return customer.id
    customer = db.query(Customer).filter(Customer.email == user.email).first()
    return customer.id if customer else None


@router.get("/returns", response_model=List[ReturnRequestResponse])
def list_returns(
    status: Optional[str] = Query(None),
    order_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    repo = ReturnRefundRepository(db)
    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        effective_customer_id = cust_id
    else:
        effective_customer_id = customer_id

    returns, _ = repo.list_returns(
        customer_id=effective_customer_id,
        order_id=order_id,
        status=status,
        skip=skip,
        limit=limit
    )

    return [
        ReturnRequestResponse(
            id=r.id,
            request_number=r.request_number,
            order_id=r.order_id,
            customer_id=r.customer_id,
            reason=r.reason,
            status=r.status,
            requested_at=r.requested_at,
            resolution_notes=r.resolution_notes,
            order_number=r.order.order_number if r.order else None,
            customer_name=r.customer.name if r.customer else None
        )
        for r in returns
    ]


@router.post("/returns", response_model=ReturnRequestResponse, status_code=status.HTTP_201_CREATED)
def create_return_request(
    return_in: ReturnRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    order_repo = OrderRepository(db)
    order = order_repo.get_by_id(return_in.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    cust_id = _get_customer_id_for_user(current_user, db) if current_user.role == UserRole.CUSTOMER.value else order.customer_id
    if current_user.role == UserRole.CUSTOMER.value and order.customer_id != cust_id:
        raise HTTPException(status_code=403, detail="Cannot request return for another customer's order.")

    repo = ReturnRefundRepository(db)
    ret = repo.create_return(
        order_id=order.id,
        customer_id=order.customer_id,
        reason=return_in.reason
    )
    return ReturnRequestResponse(
        id=ret.id,
        request_number=ret.request_number,
        order_id=ret.order_id,
        customer_id=ret.customer_id,
        reason=ret.reason,
        status=ret.status,
        requested_at=ret.requested_at,
        resolution_notes=ret.resolution_notes,
        order_number=order.order_number,
        customer_name=order.customer.name if order.customer else None
    )


@router.get("/refunds", response_model=List[RefundRequestResponse])
def list_refunds(
    status: Optional[str] = Query(None),
    order_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    repo = ReturnRefundRepository(db)
    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        effective_customer_id = cust_id
    else:
        effective_customer_id = customer_id

    refunds, _ = repo.list_refunds(
        customer_id=effective_customer_id,
        order_id=order_id,
        status=status,
        skip=skip,
        limit=limit
    )

    return [
        RefundRequestResponse(
            id=r.id,
            refund_number=r.refund_number,
            order_id=r.order_id,
            payment_id=r.payment_id,
            customer_id=r.customer_id,
            amount=r.amount,
            reason=r.reason,
            status=r.status,
            is_simulated=r.is_simulated,
            approved_by=r.approved_by,
            approved_at=r.approved_at,
            rejection_reason=r.rejection_reason,
            order_number=r.order.order_number if r.order else None,
            customer_name=r.customer.name if r.customer else None,
            created_at=r.created_at
        )
        for r in refunds
    ]


@router.get("/refunds/eligibility/{order_id}", response_model=EligibilityCheckResponse)
def check_refund_eligibility(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    refund_svc = RefundService(db)
    return refund_svc.check_eligibility(order_id)


@router.post("/refunds", response_model=RefundRequestResponse, status_code=status.HTTP_201_CREATED)
def initiate_refund_request(
    refund_in: RefundRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Initiate a simulated refund request.
    Verifies policy eligibility, records the request as 'pending_approval',
    and generates an approval request for the human operations queue.
    """
    client_ip = request.client.host if request.client else None
    refund_svc = RefundService(db)
    refund = refund_svc.initiate_refund(
        order_id=refund_in.order_id,
        reason=refund_in.reason,
        amount=refund_in.amount,
        requested_by_user_id=current_user.id,
        ip_address=client_ip
    )
    return RefundRequestResponse(
        id=refund.id,
        refund_number=refund.refund_number,
        order_id=refund.order_id,
        payment_id=refund.payment_id,
        customer_id=refund.customer_id,
        amount=refund.amount,
        reason=refund.reason,
        status=refund.status,
        is_simulated=refund.is_simulated,
        approved_by=refund.approved_by,
        approved_at=refund.approved_at,
        rejection_reason=refund.rejection_reason,
        order_number=refund.order.order_number if refund.order else None,
        customer_name=refund.customer.name if refund.customer else None,
        created_at=refund.created_at
    )

