import pytest
from sqlalchemy.orm import Session
from backend.app.database.session import SessionLocal
from backend.app.models.models import (
    Customer, Product, Order, Payment, Shipment,
    RefundRequest, ReturnRequest, SupportTicket,
    OrderStatus, PaymentStatus, ShipmentStatus, RefundStatus
)


@pytest.fixture(scope="module")
def prod_db():
    session = SessionLocal()
    yield session
    session.close()


def test_seed_counts(prod_db: Session):
    customer_count = prod_db.query(Customer).count()
    product_count = prod_db.query(Product).count()
    order_count = prod_db.query(Order).count()
    payment_count = prod_db.query(Payment).count()
    shipment_count = prod_db.query(Shipment).count()
    ticket_count = prod_db.query(SupportTicket).count()

    assert customer_count == 20, f"Expected 20 customers, got {customer_count}"
    assert product_count == 20, f"Expected 20 products, got {product_count}"
    assert order_count == 30, f"Expected 30 orders, got {order_count}"
    assert payment_count == 31, f"Expected 31 payments, got {payment_count}"
    assert shipment_count == 20, f"Expected 20 shipments, got {shipment_count}"
    assert ticket_count == 10, f"Expected 10 tickets, got {ticket_count}"


def test_scenario_successful_order(prod_db: Session):
    order = prod_db.query(Order).filter(Order.order_number == "ORD-2024-1001").first()
    assert order is not None
    assert order.status == OrderStatus.DELIVERED.value
    # Has payment
    payment = prod_db.query(Payment).filter(Payment.order_id == order.id).first()
    assert payment is not None
    assert payment.status == PaymentStatus.SUCCESSFUL.value
    # Has shipment
    shipment = prod_db.query(Shipment).filter(Shipment.order_id == order.id).first()
    assert shipment is not None
    assert shipment.status == ShipmentStatus.DELIVERED.value


def test_scenario_delayed_delivery(prod_db: Session):
    order = prod_db.query(Order).filter(Order.order_number == "ORD-2024-1002").first()
    assert order is not None
    shipment = prod_db.query(Shipment).filter(Shipment.order_id == order.id).first()
    assert shipment is not None
    assert shipment.status == ShipmentStatus.DELAYED.value
    assert "blizzard" in shipment.tracking_events_json.lower() or "weather" in shipment.tracking_events_json.lower()


def test_scenario_failed_payment(prod_db: Session):
    order = prod_db.query(Order).filter(Order.order_number == "ORD-2024-1003").first()
    assert order is not None
    assert order.status == OrderStatus.PENDING.value
    payment = prod_db.query(Payment).filter(Payment.order_id == order.id).first()
    assert payment is not None
    assert payment.status == PaymentStatus.FAILED.value
    assert "INSUFFICIENT_FUNDS" in payment.gateway_response


def test_scenario_payment_deducted_order_missing(prod_db: Session):
    # Customer Diana Prince (CUST-1004) has orphan payment TXN-2024-998811
    payment = prod_db.query(Payment).filter(Payment.transaction_reference == "TXN-2024-998811").first()
    assert payment is not None
    assert payment.order_id is None
    assert payment.status == PaymentStatus.SUCCESSFUL.value
    assert payment.customer is not None
    assert payment.customer.customer_code == "CUST-1004"


def test_scenario_eligible_refund(prod_db: Session):
    refund = prod_db.query(RefundRequest).filter(RefundRequest.refund_number == "REF-2024-8001").first()
    assert refund is not None
    assert refund.status == RefundStatus.PENDING_APPROVAL.value
    assert refund.is_simulated is True
    assert refund.order is not None


def test_scenario_ineligible_refund(prod_db: Session):
    refund = prod_db.query(RefundRequest).filter(RefundRequest.refund_number == "REF-2024-8002").first()
    assert refund is not None
    assert refund.status == RefundStatus.REJECTED.value
    assert "exceeded" in refund.rejection_reason.lower()


def test_scenario_return_request(prod_db: Session):
    ret = prod_db.query(ReturnRequest).filter(ReturnRequest.request_number == "RET-2024-9001").first()
    assert ret is not None
    assert ret.status == "requested"
    assert "size" in ret.reason.lower()

