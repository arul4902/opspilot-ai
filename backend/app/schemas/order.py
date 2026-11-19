from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    order_number: str
    customer_id: int
    status: str
    total_amount: Decimal
    currency: str = "USD"
    shipping_address: Optional[str] = None
    estimated_delivery: Optional[datetime] = None


class OrderSummaryResponse(OrderBase):
    id: int
    order_date: datetime
    created_at: datetime
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class OrderDetailResponse(OrderSummaryResponse):
    items: List[OrderItemResponse] = []
    has_active_shipment: bool = False
    has_delayed_shipment: bool = False
    payment_status: Optional[str] = None
    shipment_status: Optional[str] = None
    tracking_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderFilterParams(BaseModel):
    status: Optional[str] = None
    customer_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    skip: int = 0
    limit: int = 20


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: Decimal


class OrderCreateRequest(BaseModel):
    customer_id: int
    shipping_address: str
    items: List[OrderItemCreate]
    currency: str = "USD"


class OrderStatusUpdateRequest(BaseModel):
    status: str

