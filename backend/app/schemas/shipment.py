from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class TrackingEvent(BaseModel):
    timestamp: str
    location: str
    status: str


class ShipmentBase(BaseModel):
    tracking_number: str
    order_id: int
    courier_name: str
    status: str
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None


class ShipmentResponse(ShipmentBase):
    id: int
    tracking_events: List[Dict[str, Any]] = []
    created_at: datetime
    order_number: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    is_delayed: bool = False
    delay_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DeliveryInvestigationResponse(BaseModel):
    order_id: int
    order_number: str
    shipment_id: Optional[int] = None
    tracking_number: Optional[str] = None
    courier: Optional[str] = None
    current_status: str
    is_delayed: bool
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    delay_days: int = 0
    delay_cause: Optional[str] = None
    latest_event: Optional[Dict[str, Any]] = None
    evidence: str
    recommended_action: str

