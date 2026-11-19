from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    transaction_reference: str
    order_id: Optional[int] = None
    customer_id: int
    payment_method: str
    amount: Decimal
    currency: str = "USD"
    status: str
    gateway_response: Optional[str] = None
    transaction_date: datetime


class PaymentResponse(PaymentBase):
    id: int
    created_at: datetime
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    order_number: Optional[str] = None
    is_orphan: bool = False

    model_config = ConfigDict(from_attributes=True)


class PaymentInvestigationResponse(BaseModel):
    customer_id: int
    has_issues: bool
    issue_type: Optional[str] = None  # FAILED_PAYMENT, ORPHAN_PAYMENT, DUPLICATE_PAYMENT, NONE
    message: str
    transactions: list[PaymentResponse] = []
    recommended_action: str

