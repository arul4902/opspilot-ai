import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.repositories.order_repository import OrderRepository
from backend.app.repositories.shipment_repository import ShipmentRepository
from backend.app.schemas.shipment import DeliveryInvestigationResponse
from backend.app.models.models import ShipmentStatus, OrderStatus


class DeliveryService:
    def __init__(self, db: Session):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.shipment_repo = ShipmentRepository(db)

    def investigate_delivery(self, order_identifier: str | int) -> DeliveryInvestigationResponse:
        """
        Investigate shipment delivery status using actual order and courier records.
        Identifies delays, weather/customs exceptions, and provides an evidence-based recommendation.
        """
        if isinstance(order_identifier, int) or (isinstance(order_identifier, str) and order_identifier.isdigit()):
            order = self.order_repo.get_by_id(int(order_identifier))
        else:
            order = self.order_repo.get_by_number(str(order_identifier))

        if not order:
            return DeliveryInvestigationResponse(
                order_id=0,
                order_number=str(order_identifier),
                current_status="ORDER_NOT_FOUND",
                is_delayed=False,
                evidence=f"Order '{order_identifier}' was not found in the database.",
                recommended_action="Verify the order number with the customer."
            )

        shipment = self.shipment_repo.get_by_order_id(order.id)
        if not shipment:
            is_delayed = False
            evidence = f"Order {order.order_number} currently has status '{order.status}' and no shipment package has been dispatched yet."
            action = "Check fulfillment center warehouse picking queue." if order.status in [OrderStatus.CONFIRMED.value, OrderStatus.PROCESSING.value] else "Verify payment before preparing shipment."
            return DeliveryInvestigationResponse(
                order_id=order.id,
                order_number=order.order_number,
                current_status=order.status,
                is_delayed=is_delayed,
                evidence=evidence,
                recommended_action=action
            )

        # Parse tracking events
        try:
            events: List[Dict[str, Any]] = json.loads(shipment.tracking_events_json) if shipment.tracking_events_json else []
        except Exception:
            events = []

        latest_event = events[-1] if events else None

        # Check delay conditions
        now = datetime.now(timezone.utc)
        is_delayed = False
        delay_days = 0
        delay_cause = None

        if shipment.status == ShipmentStatus.DELAYED.value:
            is_delayed = True

        if shipment.estimated_delivery:
            est_deliv = shipment.estimated_delivery
            if est_deliv.tzinfo is None:
                est_deliv = est_deliv.replace(tzinfo=timezone.utc)

            if shipment.status not in [ShipmentStatus.DELIVERED.value] and now > est_deliv:
                is_delayed = True
                delay_days = (now - est_deliv).days

        # Scan tracking events for exception keywords
        delay_keywords = ["weather", "blizzard", "storm", "customs", "delay", "road closure", "sorting issue", "mechanical", "exception"]
        for ev in reversed(events):
            ev_status = ev.get("status", "").lower()
            for kw in delay_keywords:
                if kw in ev_status:
                    is_delayed = True
                    delay_cause = ev.get("status")
                    break
            if delay_cause:
                break

        # Generate Evidence & Recommendation
        if shipment.status == ShipmentStatus.DELIVERED.value:
            evidence = f"Shipment {shipment.tracking_number} was successfully delivered on {shipment.actual_delivery.strftime('%Y-%m-%d %H:%M:%S UTC') if shipment.actual_delivery else 'record date'}."
            action = "Confirm delivery with customer and offer return/exchange if customer is unsatisfied with products."
        elif is_delayed:
            evidence = (
                f"Shipment {shipment.tracking_number} via {shipment.courier_name} is DELAYED. "
                f"Estimated delivery was {shipment.estimated_delivery.strftime('%Y-%m-%d') if shipment.estimated_delivery else 'N/A'}"
                f"{f' ({delay_days} days overdue)' if delay_days > 0 else ''}. "
                f"Latest status: '{latest_event.get('status') if latest_event else shipment.status}' at '{latest_event.get('location') if latest_event else 'Transit Hub'}'. "
                f"{f'Cause: {delay_cause}.' if delay_cause else ''}"
            )
            action = "Provide customer with tracking details, explain transit delay, and offer a $10 courtesy credit or free expedited reshipment if delayed past SLA."
        else:
            evidence = (
                f"Shipment {shipment.tracking_number} via {shipment.courier_name} is actively in transit. "
                f"Expected arrival: {shipment.estimated_delivery.strftime('%Y-%m-%d') if shipment.estimated_delivery else 'on schedule'}. "
                f"Latest tracking event: '{latest_event.get('status') if latest_event else 'In transit'}'."
            )
            action = "Advise customer that delivery is currently proceeding on schedule according to courier tracking."

        return DeliveryInvestigationResponse(
            order_id=order.id,
            order_number=order.order_number,
            shipment_id=shipment.id,
            tracking_number=shipment.tracking_number,
            courier=shipment.courier_name,
            current_status=shipment.status,
            is_delayed=is_delayed,
            estimated_delivery=shipment.estimated_delivery,
            actual_delivery=shipment.actual_delivery,
            delay_days=delay_days,
            delay_cause=delay_cause,
            latest_event=latest_event,
            evidence=evidence,
            recommended_action=action
        )
