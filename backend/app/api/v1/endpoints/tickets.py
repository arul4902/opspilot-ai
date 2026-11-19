from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, Customer
from backend.app.repositories.ticket_repository import TicketRepository
from backend.app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse

router = APIRouter()


def _get_customer_id_for_user(user: User, db: Session) -> Optional[int]:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer:
        return customer.id
    customer = db.query(Customer).filter(Customer.email == user.email).first()
    return customer.id if customer else None


@router.get("", response_model=List[TicketResponse])
def list_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    order_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    List support tickets. Customers are strictly restricted to tickets they submitted.
    """
    ticket_repo = TicketRepository(db)
    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        effective_customer_id = cust_id
    else:
        effective_customer_id = customer_id

    tickets, _ = ticket_repo.list_tickets(
        customer_id=effective_customer_id,
        status=status,
        priority=priority,
        order_id=order_id,
        skip=skip,
        limit=limit
    )

    return [
        TicketResponse(
            id=t.id,
            ticket_number=t.ticket_number,
            customer_id=t.customer_id,
            order_id=t.order_id,
            subject=t.subject,
            description=t.description,
            priority=t.priority,
            status=t.status,
            created_at=t.created_at,
            updated_at=t.updated_at,
            customer_name=t.customer.name if t.customer else None,
            customer_email=t.customer.email if t.customer else None,
            order_number=t.order.order_number if t.order else None
        )
        for t in tickets
    ]


@router.get("/{id}", response_model=TicketResponse)
def get_ticket_by_id(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    ticket_repo = TicketRepository(db)
    t = ticket_repo.get_by_id(id)
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    if current_user.role == UserRole.CUSTOMER.value:
        cust_id = _get_customer_id_for_user(current_user, db)
        if t.customer_id != cust_id:
            raise HTTPException(status_code=403, detail="Access denied to this ticket.")

    return TicketResponse(
        id=t.id,
        ticket_number=t.ticket_number,
        customer_id=t.customer_id,
        order_id=t.order_id,
        subject=t.subject,
        description=t.description,
        priority=t.priority,
        status=t.status,
        created_at=t.created_at,
        updated_at=t.updated_at,
        customer_name=t.customer.name if t.customer else None,
        customer_email=t.customer.email if t.customer else None,
        order_number=t.order.order_number if t.order else None
    )


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_in: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new support ticket.
    """
    cust_id = _get_customer_id_for_user(current_user, db) if current_user.role == UserRole.CUSTOMER.value else ticket_in.customer_id
    if not cust_id:
        cust_id = 1  # Fallback customer id for operations team created tickets

    ticket_repo = TicketRepository(db)
    ticket = ticket_repo.create(
        customer_id=cust_id,
        subject=ticket_in.subject,
        description=ticket_in.description,
        priority=ticket_in.priority,
        order_id=ticket_in.order_id
    )
    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        customer_id=ticket.customer_id,
        order_id=ticket.order_id,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        customer_name=ticket.customer.name if ticket.customer else None,
        customer_email=ticket.customer.email if ticket.customer else None,
        order_number=ticket.order.order_number if ticket.order else None
    )


@router.patch("/{id}", response_model=TicketResponse)
def update_ticket(
    id: int,
    ticket_in: TicketUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update ticket status and priority (Operations agents and Admin only).
    """
    ticket_repo = TicketRepository(db)
    ticket = ticket_repo.update(
        ticket_id=id,
        status=ticket_in.status,
        priority=ticket_in.priority,
        description=ticket_in.description
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        customer_id=ticket.customer_id,
        order_id=ticket.order_id,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        customer_name=ticket.customer.name if ticket.customer else None,
        customer_email=ticket.customer.email if ticket.customer else None,
        order_number=ticket.order.order_number if ticket.order else None
    )

