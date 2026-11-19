from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"  # low, medium, high, urgent
    order_id: Optional[int] = None
    customer_id: Optional[int] = None


class TicketUpdate(BaseModel):
    status: Optional[str] = None  # open, in_progress, waiting_customer, resolved, closed
    priority: Optional[str] = None
    description: Optional[str] = None


class TicketResponse(BaseModel):
    id: int
    ticket_number: str
    customer_id: int
    order_id: Optional[int] = None
    subject: str
    description: str
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    order_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

