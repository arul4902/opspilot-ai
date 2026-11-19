from typing import List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from backend.app.models.models import SupportTicket, Customer, Order


class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, ticket_id: int) -> Optional[SupportTicket]:
        return (
            self.db.query(SupportTicket)
            .options(
                joinedload(SupportTicket.customer),
                joinedload(SupportTicket.order)
            )
            .filter(SupportTicket.id == ticket_id)
            .first()
        )

    def get_by_ticket_number(self, ticket_number: str) -> Optional[SupportTicket]:
        return (
            self.db.query(SupportTicket)
            .options(
                joinedload(SupportTicket.customer),
                joinedload(SupportTicket.order)
            )
            .filter(SupportTicket.ticket_number == ticket_number.strip().upper())
            .first()
        )

    def list_tickets(
        self,
        customer_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        order_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[SupportTicket], int]:
        query = self.db.query(SupportTicket).options(
            joinedload(SupportTicket.customer),
            joinedload(SupportTicket.order)
        )
        if customer_id:
            query = query.filter(SupportTicket.customer_id == customer_id)
        if status:
            query = query.filter(SupportTicket.status == status)
        if priority:
            query = query.filter(SupportTicket.priority == priority)
        if order_id:
            query = query.filter(SupportTicket.order_id == order_id)

        total = query.count()
        tickets = query.order_by(SupportTicket.created_at.desc()).offset(skip).limit(limit).all()
        return tickets, total

    def create(
        self,
        customer_id: int,
        subject: str,
        description: str,
        priority: str = "medium",
        order_id: Optional[int] = None,
    ) -> SupportTicket:
        count = self.db.query(SupportTicket).count() + 1
        ticket_number = f"TCK-2024-{count:04d}"
        ticket = SupportTicket(
            ticket_number=ticket_number,
            customer_id=customer_id,
            order_id=order_id,
            subject=subject.strip(),
            description=description.strip(),
            priority=priority.lower(),
            status="open",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def update(
        self,
        ticket_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[SupportTicket]:
        ticket = self.db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if ticket:
            if status:
                ticket.status = status
            if priority:
                ticket.priority = priority
            if description:
                ticket.description = description
            ticket.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(ticket)
        return ticket

