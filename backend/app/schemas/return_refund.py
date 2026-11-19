from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ReturnRequestCreate(BaseModel):
    order_id: int
    reason: str


class ReturnRequestResponse(BaseModel):
    id: int
    request_number: str
    order_id: int
    customer_id: int
    reason: str
    status: str
    requested_at: datetime
    resolution_notes: Optional[str] = None
    order_number: Optional[str] = None
    customer_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RefundRequestCreate(BaseModel):
    order_id: int
    reason: str
    amount: Optional[Decimal] = None


class RefundRequestResponse(BaseModel):
    id: int
    refund_number: str
    order_id: int
    payment_id: Optional[int] = None
    customer_id: int
    amount: Decimal
    reason: str
    status: str
    is_simulated: bool
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    order_number: Optional[str] = None
    customer_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EligibilityCheckResponse(BaseModel):
    order_id: int
    order_number: str
    eligible: bool
    reason: str
    policy_reference: str
    delivery_date: Optional[datetime] = None
    days_since_delivery: Optional[int] = None
    max_refund_amount: Decimal = Decimal("0.00")
    requires_human_approval: bool = True

