from typing import List, Optional, Any, Dict
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


# Tool 1: get_order_details
class GetOrderDetailsInput(BaseModel):
    order_id: str = Field(description="Order number (e.g. ORD-2024-1001) or database order ID")


class OrderItemSummary(BaseModel):
    product_name: str
    product_sku: str
    quantity: int
    unit_price: float
    total_price: float


class GetOrderDetailsOutput(BaseModel):
    success: bool
    order_id: int
    order_number: str
    customer_id: int
    customer_name: Optional[str] = None
    order_date: Optional[str] = None
    status: str
    total_amount: float
    currency: str = "USD"
    estimated_delivery: Optional[str] = None
    products: List[OrderItemSummary] = []
    message: Optional[str] = None


# Tool 2: get_payment_details
class GetPaymentDetailsInput(BaseModel):
    order_id: str = Field(description="Order number or ID, or transaction reference")


class GetPaymentDetailsOutput(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    order_id: Optional[int] = None
    order_number: Optional[str] = None
    payment_method: Optional[str] = None
    transaction_amount: Optional[float] = None
    currency: str = "USD"
    payment_status: Optional[str] = None
    transaction_date: Optional[str] = None
    gateway_message: Optional[str] = None
    is_orphan: bool = False
    message: Optional[str] = None


# Tool 3: check_delivery_status
class CheckDeliveryStatusInput(BaseModel):
    order_id: str = Field(description="Order number or ID to inspect shipment status")


class CheckDeliveryStatusOutput(BaseModel):
    success: bool
    order_id: int
    order_number: str
    tracking_number: Optional[str] = None
    courier_reference: Optional[str] = None
    shipment_status: str
    expected_delivery_date: Optional[str] = None
    actual_delivery_date: Optional[str] = None
    is_delayed: bool = False
    latest_tracking_event: Optional[Dict[str, Any]] = None
    delay_cause: Optional[str] = None
    evidence: str


# Tool 4: search_return_policy
class SearchReturnPolicyInput(BaseModel):
    query: str = Field(description="Policy query keywords (e.g. 'return window', 'damaged item', 'refund eligibility')")


class PolicyCitation(BaseModel):
    section: str
    source_document: str
    snippet: str
    relevance_score: float


class SearchReturnPolicyOutput(BaseModel):
    success: bool
    query: str
    citations: List[PolicyCitation] = []
    policy_summary: str


# Tool 5: create_return_request
class CreateReturnRequestInput(BaseModel):
    order_id: str = Field(description="Order number or ID to create a return for")
    reason: str = Field(description="Reason for return request")


class CreateReturnRequestOutput(BaseModel):
    success: bool
    return_request_number: Optional[str] = None
    order_id: int
    status: str
    eligible: bool
    eligibility_reason: str
    message: str


# Tool 6: initiate_refund_request
class InitiateRefundRequestInput(BaseModel):
    order_id: str = Field(description="Order number or ID to initiate refund for")
    reason: str = Field(description="Reason for refund request")
    amount: Optional[float] = Field(None, description="Optional partial or full amount")


class InitiateRefundRequestOutput(BaseModel):
    success: bool
    refund_number: Optional[str] = None
    order_id: int
    amount: float
    status: str
    is_simulated: bool = True
    requires_approval: bool = True
    approval_request_id: Optional[int] = None
    message: str


# Tool 7: create_support_ticket
class CreateSupportTicketInput(BaseModel):
    customer_id: int = Field(description="Customer database ID")
    subject: str = Field(description="Ticket title or subject")
    description: str = Field(description="Detailed issue description")
    priority: str = Field("medium", description="Priority level: low, medium, high, urgent")
    order_id: Optional[str] = Field(None, description="Optional associated order ID or number")


class CreateSupportTicketOutput(BaseModel):
    success: bool
    ticket_id: int
    ticket_number: str
    customer_id: int
    subject: str
    priority: str
    status: str
    created_at: str
    message: str


# Tool 8: escalate_to_human
class EscalateToHumanInput(BaseModel):
    conversation_id: Optional[int] = Field(None, description="Active conversation or ticket ID")
    customer_id: int = Field(description="Customer database ID")
    reason: str = Field(description="Reason for escalation")
    priority: str = Field("high", description="Escalation priority")


class EscalateToHumanOutput(BaseModel):
    success: bool
    escalation_id: int
    queue_name: str = "Operations Investigation Queue"
    priority: str
    status: str = "pending"
    message: str


# Tool 9: search_customer_history
class SearchCustomerHistoryInput(BaseModel):
    customer_id: int = Field(description="Customer database ID")


class CustomerHistorySummary(BaseModel):
    customer_id: int
    customer_code: str
    name: str
    email: str
    tier: str
    total_orders: int
    open_tickets: int
    recent_orders: List[Dict[str, Any]] = []
    recent_payments: List[Dict[str, Any]] = []


class SearchCustomerHistoryOutput(BaseModel):
    success: bool
    customer_id: int
    history: Optional[CustomerHistorySummary] = None
    message: str

