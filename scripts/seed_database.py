import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sys
import os

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import SessionLocal, engine, Base
import backend.app.database.base
from backend.app.models.models import (
    User, Customer, Product, Order, OrderItem, Payment, Shipment,
    ReturnRequest, RefundRequest, SupportTicket, Conversation, Message,
    AuditLog, UserRole, OrderStatus, PaymentStatus, ShipmentStatus,
    ReturnStatus, RefundStatus, TicketPriority, TicketStatus, ApprovalStatus,
    ApprovalRequest, Escalation, EscalationStatus
)
from backend.app.security.passwords import get_password_hash


def seed_database(target_engine=None, custom_session=None):
    active_engine = target_engine or engine
    print("=" * 60)
    print(f"Seeding OpsPilot AI Database on {active_engine.url}...")
    print("=" * 60)

    # Recreate all tables cleanly
    Base.metadata.drop_all(bind=active_engine)
    Base.metadata.create_all(bind=active_engine)

    if custom_session:
        db = custom_session
    elif target_engine:
        from sqlalchemy.orm import sessionmaker
        TestSession = sessionmaker(autocommit=False, autoflush=False, bind=target_engine)
        db = TestSession()
    else:
        db = SessionLocal()
    now = datetime.now(timezone.utc)

    try:
        # 1. Create Default Users
        print("[1/9] Creating System Users...")
        admin_user = User(
            email="admin@opspilot.ai",
            hashed_password=get_password_hash("Admin@OpsPilot2026!"),
            full_name="Sarah Jenkins (Lead Ops Admin)",
            role=UserRole.ADMIN.value,
            is_active=True,
            created_at=now - timedelta(days=90),
        )
        ops_agent = User(
            email="agent@opspilot.ai",
            hashed_password=get_password_hash("Agent@OpsPilot2026!"),
            full_name="Marcus Vance (Operations Specialist)",
            role=UserRole.OPERATIONS_AGENT.value,
            is_active=True,
            created_at=now - timedelta(days=60),
        )
        demo_customer_user = User(
            email="customer@opspilot.ai",
            hashed_password=get_password_hash("Customer@OpsPilot2026!"),
            full_name="Alex Johnson",
            role=UserRole.CUSTOMER.value,
            is_active=True,
            created_at=now - timedelta(days=45),
        )
        db.add_all([admin_user, ops_agent, demo_customer_user])
        db.commit()

        # 2. Create 20 Customers
        print("[2/9] Creating 20 Realistic Customers...")
        customers_data = [
            ("CUST-1001", "Alex Johnson", "customer@opspilot.ai", "+1-555-0101", "742 Evergreen Terrace, Springfield, OR", "vip", demo_customer_user.id),
            ("CUST-1002", "Brenda Miller", "brenda.miller@example.com", "+1-555-0102", "1204 Elm Street, Dallas, TX", "gold", None),
            ("CUST-1003", "Carlos Gomez", "carlos.g@example.com", "+1-555-0103", "450 Ocean Drive, Miami, FL", "standard", None),
            ("CUST-1004", "Diana Prince", "diana.prince@example.com", "+1-555-0104", "88 Gateway Blvd, Seattle, WA", "vip", None),
            ("CUST-1005", "Evan Wright", "evan.wright@example.com", "+1-555-0105", "302 Pine Ridge Rd, Denver, CO", "gold", None),
            ("CUST-1006", "Fiona Gallagher", "fiona.g@example.com", "+1-555-0106", "211 North Ave, Chicago, IL", "standard", None),
            ("CUST-1007", "George Clark", "george.clark@example.com", "+1-555-0107", "95 Maple Court, Boston, MA", "standard", None),
            ("CUST-1008", "Hannah Abbott", "hannah.a@example.com", "+1-555-0108", "501 Willow Way, Austin, TX", "gold", None),
            ("CUST-1009", "Ian Malcolm", "ian.malcolm@example.com", "+1-555-0109", "12 Jurassic Lane, San Jose, CA", "vip", None),
            ("CUST-1010", "Julia Roberts", "julia.r@example.com", "+1-555-0110", "77 Sunset Strip, Los Angeles, CA", "standard", None),
            ("CUST-1011", "Kevin Bacon", "kevin.b@example.com", "+1-555-0111", "6 Degrees Road, Philadelphia, PA", "standard", None),
            ("CUST-1012", "Laura Croft", "laura.croft@example.com", "+1-555-0112", "14 Manor House Way, London, CT", "vip", None),
            ("CUST-1013", "Michael Scott", "michael.scott@example.com", "+1-555-0113", "1725 Slough Ave, Scranton, PA", "gold", None),
            ("CUST-1014", "Nina Patel", "nina.patel@example.com", "+1-555-0114", "33 Peachtree St, Atlanta, GA", "standard", None),
            ("CUST-1015", "Oliver Queen", "oliver.queen@example.com", "+1-555-0115", "10 Starling City Rd, Portland, OR", "vip", None),
            ("CUST-1016", "Pamela Beesly", "pam.beesly@example.com", "+1-555-0116", "83 Industrial Pkwy, Scranton, PA", "standard", None),
            ("CUST-1017", "Quentin Tarantino", "quentin.t@example.com", "+1-555-0117", "9 Pulp Fiction Way, Knoxville, TN", "gold", None),
            ("CUST-1018", "Rachel Green", "rachel.green@example.com", "+1-555-0118", "495 Grove St, New York, NY", "vip", None),
            ("CUST-1019", "Steve Rogers", "steve.rogers@example.com", "+1-555-0119", "569 Leaman Place, Brooklyn, NY", "gold", None),
            ("CUST-1020", "Tina Turner", "tina.turner@example.com", "+1-555-0120", "198 River Deep St, Nutbush, TN", "standard", None),
        ]

        customers = []
        for code, name, email, phone, addr, tier, uid in customers_data:
            cust = Customer(
                customer_code=code,
                name=name,
                email=email,
                phone=phone,
                address=addr,
                tier=tier,
                user_id=uid,
                created_at=now - timedelta(days=120),
            )
            customers.append(cust)
            db.add(cust)
        # 10. Create Initial Sample Conversations & Messages
        print("[10/10] Creating Initial Conversation & Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])

        db.commit()

        # 3. Create 20 Products
        print("[3/9] Creating 20 Products...")
        products_data = [
            ("SKU-AUDIO-001", "AuraPulse Wireless Noise-Canceling Headphones", "Flagship active noise canceling over-ear headphones with 40hr battery life.", "Audio", Decimal("199.99"), 150),
            ("SKU-AUDIO-002", "SonicBlast Portable Bluetooth Speaker", "IP67 waterproof outdoor speaker with deep bass.", "Audio", Decimal("79.50"), 85),
            ("SKU-AUDIO-003", "TrueBeats Studio Wireless Earbuds", "Compact ergonomic earbuds with low latency gaming mode.", "Audio", Decimal("89.00"), 200),
            ("SKU-PERIPH-001", "ApexPro RGB Mechanical Keyboard", "Hot-swappable tactile switches with aluminum frame.", "Computer Accessories", Decimal("129.99"), 110),
            ("SKU-PERIPH-002", "Vortex Ultra-Light Gaming Mouse", "65g ultra-lightweight optical gaming mouse with 26K DPI.", "Computer Accessories", Decimal("59.99"), 140),
            ("SKU-PERIPH-003", "ErgoLift Adjustable Laptop Stand", "Anodized aluminum foldable desk riser.", "Computer Accessories", Decimal("39.99"), 300),
            ("SKU-PERIPH-004", "UltraVision 4K UHD Webcam", "4K 60fps streaming webcam with dual microphones.", "Computer Accessories", Decimal("119.00"), 75),
            ("SKU-HOME-001", "Lumina Smart LED Desk Lamp", "Touch-controlled stepless dimming with wireless phone charging pad.", "Smart Home", Decimal("49.99"), 180),
            ("SKU-HOME-002", "PureBreeze HEPA Air Purifier", "Smart room air purifier with real-time AQI monitor.", "Smart Home", Decimal("149.50"), 45),
            ("SKU-HOME-003", "ThermoSense Smart Coffee Warmer", "Precision temperature controlled mug and heating plate.", "Smart Home", Decimal("34.99"), 220),
            ("SKU-WEAR-001", "Chronos Active Smartwatch", "AMOLED heart-rate and SpO2 fitness watch with GPS.", "Wearables", Decimal("179.00"), 95),
            ("SKU-WEAR-002", "PulseFit Endurance Fitness Band", "Lightweight swim-proof fitness tracker with 14-day battery.", "Wearables", Decimal("45.00"), 160),
            ("SKU-PWR-001", "PowerVolt 65W GaN Fast Charger", "Triple-port ultra-compact wall charger for laptops and phones.", "Power & Cables", Decimal("35.99"), 400),
            ("SKU-PWR-002", "MegaCharge 25000mAh Power Bank", "High-capacity airline approved power bank with 100W PD output.", "Power & Cables", Decimal("89.99"), 130),
            ("SKU-PWR-003", "Braided USB-C to USB-C Cable (2m)", "Durable 240W 48V/5A reinforced nylon charging cable.", "Power & Cables", Decimal("14.99"), 600),
            ("SKU-STORAGE-001", "VelocityPro 1TB Portable SSD", "USB 3.2 Gen 2x2 rugged external solid-state drive (2000 MB/s).", "Storage", Decimal("109.99"), 90),
            ("SKU-STORAGE-002", "MicroDrive 512GB High-Speed MicroSDXC", "UHS-I U3 A2 V30 memory card for 4K video recording.", "Storage", Decimal("42.50"), 250),
            ("SKU-BAGS-001", "Voyager Weatherproof Commuter Backpack", "25L water-repellent tech backpack with dedicated 16-inch laptop pocket.", "Bags & Cases", Decimal("95.00"), 70),
            ("SKU-BAGS-002", "ArmorShield Shockproof Laptop Sleeve", "Memory foam 14-inch protective case with accessory pouch.", "Bags & Cases", Decimal("24.99"), 310),
            ("SKU-OFFICE-001", "ErgoRest Memory Foam Seat Cushion", "Orthopedic cooling gel seat cushion for office chairs.", "Office & Comfort", Decimal("38.50"), 190),
        ]

        products = []
        for sku, name, desc, cat, price, stock in products_data:
            prod = Product(
                sku=sku,
                name=name,
                description=desc,
                category=cat,
                price=price,
                stock_quantity=stock,
                is_active=True,
                created_at=now - timedelta(days=150),
            )
            products.append(prod)
            db.add(prod)
        # 10. Create Initial Sample Conversations & Messages
        print("[10/10] Creating Initial Conversation & Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])

        db.commit()

        # 4. Create 30 Orders & Order Items
        print("[4/9] Creating 30 Realistic Orders...")
        orders = []
        # Pre-assign specific scenarios for testing:
        # Scenario 1: ORD-2024-1001 (Customer CUST-1001 Alex Johnson) - Delivered successfully
        # Scenario 2: ORD-2024-1002 (Customer CUST-1002 Brenda Miller) - Delayed delivery
        # Scenario 3: ORD-2024-1003 (Customer CUST-1003 Carlos Gomez) - Payment failed
        # Scenario 4: (Customer CUST-1004 Diana Prince) - Payment deducted, order missing (no order or pending creation)
        # Scenario 5: ORD-2024-1005 (Customer CUST-1005 Evan Wright) - Eligible refund request (damaged item, 7 days ago)
        # Scenario 6: ORD-2024-1006 (Customer CUST-1006 Fiona Gallagher) - Ineligible refund request (delivered 48 days ago)
        # Scenario 7: ORD-2024-1007 (Customer CUST-1007 George Clark) - Return request (wrong size)

        order_configs = [
            # 1: Delivered
            (1001, 0, OrderStatus.DELIVERED.value, Decimal("199.99"), 14, 10, "Delivered on schedule"),
            # 2: Delayed Delivery
            (1002, 1, OrderStatus.SHIPPED.value, Decimal("129.99"), 10, -3, "Past estimated delivery date"),
            # 3: Failed Payment Order
            (1003, 2, OrderStatus.PENDING.value, Decimal("269.98"), 2, 5, "Awaiting valid payment"),
            # 5: Eligible Refund
            (1005, 4, OrderStatus.DELIVERED.value, Decimal("89.00"), 10, 3, "Ordered 10 days ago, delivered 7 days ago, eligible for return/refund"),
            # 6: Ineligible Refund
            (1006, 5, OrderStatus.DELIVERED.value, Decimal("179.00"), 52, 4, "Ordered 52 days ago, delivered 48 days ago, policy window 30 days passed"),
            # 7: Return Request
            (1007, 6, OrderStatus.DELIVERED.value, Decimal("95.00"), 12, 8, "Customer requested return due to size"),
            # 8: Confirmed processing
            (1008, 7, OrderStatus.PROCESSING.value, Decimal("149.50"), 1, 4, "In warehouse fulfillment"),
            # 9: Shipped on track
            (1009, 8, OrderStatus.SHIPPED.value, Decimal("109.99"), 3, 2, "In transit via FedEx"),
            # 10: Delivered
            (1010, 9, OrderStatus.DELIVERED.value, Decimal("79.50"), 20, 16, "Delivered safely"),
            # 11: Delivered
            (1011, 10, OrderStatus.DELIVERED.value, Decimal("49.99"), 25, 21, "Delivered safely"),
            # 12: Cancelled
            (1012, 11, OrderStatus.CANCELLED.value, Decimal("59.99"), 15, None, "Cancelled by user before shipment"),
            # 13: Processing
            (1013, 12, OrderStatus.PROCESSING.value, Decimal("119.00"), 1, 3, "Picking in progress"),
            # 14: Delivered
            (1014, 13, OrderStatus.DELIVERED.value, Decimal("35.99"), 30, 26, "Delivered"),
            # 15: Shipped
            (1015, 14, OrderStatus.SHIPPED.value, Decimal("89.99"), 2, 3, "In transit via UPS"),
            # 16: Delivered
            (1016, 15, OrderStatus.DELIVERED.value, Decimal("42.50"), 40, 36, "Delivered"),
            # 17: Delivered
            (1017, 16, OrderStatus.DELIVERED.value, Decimal("24.99"), 18, 14, "Delivered"),
            # 18: Processing
            (1018, 17, OrderStatus.PROCESSING.value, Decimal("199.99"), 2, 4, "Payment cleared, preparing box"),
            # 19: Delivered
            (1019, 18, OrderStatus.DELIVERED.value, Decimal("38.50"), 50, 46, "Delivered"),
            # 20: Delivered
            (1020, 19, OrderStatus.DELIVERED.value, Decimal("14.99"), 5, 2, "Delivered"),
            # 21-30: Additional Realistic Orders
            (1021, 0, OrderStatus.DELIVERED.value, Decimal("129.99"), 60, 56, "Delivered"),
            (1022, 1, OrderStatus.DELIVERED.value, Decimal("89.00"), 22, 18, "Delivered"),
            (1023, 2, OrderStatus.SHIPPED.value, Decimal("179.00"), 4, 1, "In transit"),
            (1024, 3, OrderStatus.DELIVERED.value, Decimal("149.50"), 15, 11, "Delivered"),
            (1025, 4, OrderStatus.PROCESSING.value, Decimal("109.99"), 1, 5, "Processing"),
            (1026, 5, OrderStatus.DELIVERED.value, Decimal("39.99"), 33, 29, "Delivered"),
            (1027, 6, OrderStatus.DELIVERED.value, Decimal("79.50"), 19, 15, "Delivered"),
            (1028, 7, OrderStatus.CANCELLED.value, Decimal("45.00"), 8, None, "Cancelled upon customer request"),
            (1029, 8, OrderStatus.DELIVERED.value, Decimal("95.00"), 28, 24, "Delivered"),
            (1030, 9, OrderStatus.CONFIRMED.value, Decimal("119.00"), 1, 6, "Payment verified, awaiting warehouse pick"),
            (1031, 10, OrderStatus.PROCESSING.value, Decimal("89.99"), 2, 4, "Preparing dispatch"),
        ]

        created_orders = {}
        for num, cust_idx, st, amt, days_ago, est_deliv_days, notes in order_configs:
            ord_date = now - timedelta(days=days_ago)
            est_deliv = (now - timedelta(days=days_ago) + timedelta(days=est_deliv_days)) if est_deliv_days is not None else None
            cust = customers[cust_idx]
            order = Order(
                order_number=f"ORD-2024-{num}",
                customer_id=cust.id,
                order_date=ord_date,
                status=st,
                total_amount=amt,
                currency="USD",
                shipping_address=cust.address,
                estimated_delivery=est_deliv,
                created_at=ord_date,
            )
            db.add(order)
            created_orders[num] = order
        # 10. Create Initial Sample Conversations & Messages
        print("[10/10] Creating Initial Conversation & Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])

        db.commit()

        # Add Order Items
        print("   Adding Items to Orders...")
        for num, order in created_orders.items():
            # Pick a corresponding product
            prod_idx = (num - 1001) % len(products)
            prod = products[prod_idx]
            item = OrderItem(
                order_id=order.id,
                product_id=prod.id,
                quantity=1,
                unit_price=prod.price,
                total_price=prod.price,
            )
            db.add(item)
        # 10. Create Initial Sample Conversations & Messages
        print("[10/10] Creating Initial Conversation & Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])

        db.commit()

        # 5. Create 30 Payment Records
        print("[5/9] Creating 30 Payment Records...")
        payments = []
        payment_methods = ["credit_card", "paypal", "apple_pay", "credit_card", "bank_transfer"]

        for i, (num, order) in enumerate(created_orders.items()):
            # Scenario 3: Order 1003 has failed payment
            if num == 1003:
                p_status = PaymentStatus.FAILED.value
                gw_response = json.dumps({"error_code": "DECLINED_INSUFFICIENT_FUNDS", "message": "Card issuer declined transaction due to insufficient funds."})
            elif order.status == OrderStatus.CANCELLED.value and num == 1012:
                p_status = PaymentStatus.REFUNDED.value
                gw_response = json.dumps({"status": "REFUNDED", "message": "Transaction fully refunded back to original payment method."})
            else:
                p_status = PaymentStatus.SUCCESSFUL.value
                gw_response = json.dumps({"authorization_code": f"AUTH_{980000 + i}", "status": "CAPTURED", "network": "Visa/Mastercard"})

            pay = Payment(
                transaction_reference=f"TXN-2024-{7000 + num}",
                order_id=order.id,
                customer_id=order.customer_id,
                payment_method=payment_methods[i % len(payment_methods)],
                amount=order.total_amount,
                currency="USD",
                status=p_status,
                gateway_response=gw_response,
                transaction_date=order.order_date,
                created_at=order.order_date,
            )
            payments.append(pay)
            db.add(pay)

        # Scenario 4: CRITICAL TEST CASE - Payment deducted, order missing!
        # Customer CUST-1004 (Diana Prince) has a successful charge of $149.50, but order_id is NULL!
        missing_order_customer = customers[3]  # Diana Prince
        orphan_payment = Payment(
            transaction_reference="TXN-2024-998811",
            order_id=None,  # No order was created!
            customer_id=missing_order_customer.id,
            payment_method="credit_card",
            amount=Decimal("149.50"),
            currency="USD",
            status=PaymentStatus.SUCCESSFUL.value,
            gateway_response=json.dumps({
                "authorization_code": "AUTH_998811_ORPHAN",
                "status": "CAPTURED",
                "note": "Payment captured successfully, but checkout session timed out before order confirmation."
            }),
            transaction_date=now - timedelta(hours=6),
            created_at=now - timedelta(hours=6),
        )
        db.add(orphan_payment)
        # 10. Create Initial Sample Conversations & Messages
        print("[10/10] Creating Initial Conversation & Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])

        db.commit()

        # 6. Create 20 Shipment Records
        print("[6/9] Creating 20 Shipment Records with Tracking Timelines...")
        couriers = ["FedEx", "DHL Express", "UPS", "USPS Priority"]
        shipment_orders = [ord for ord in created_orders.values() if ord.status in [OrderStatus.SHIPPED.value, OrderStatus.DELIVERED.value]]

        for i, order in enumerate(shipment_orders[:20]):
            courier = couriers[i % len(couriers)]
            trk_no = f"TRK-{courier[:3].upper()}-{880000 + order.id}"

            # Scenario 2: Order 1002 Delayed Delivery
            if order.order_number == "ORD-2024-1002":
                ship_status = ShipmentStatus.DELAYED.value
                est_del = now - timedelta(days=3)  # was supposed to arrive 3 days ago!
                events = [
                    {"timestamp": (now - timedelta(days=10)).isoformat(), "location": "Warehouse, Ontario, CA", "status": "Package picked up by courier"},
                    {"timestamp": (now - timedelta(days=8)).isoformat(), "location": "Sorting Center, Reno, NV", "status": "Departed sorting facility"},
                    {"timestamp": (now - timedelta(days=4)).isoformat(), "location": "Hub, Salt Lake City, UT", "status": "Severe weather event: blizzard conditions delaying transport truck"},
                    {"timestamp": (now - timedelta(days=1)).isoformat(), "location": "Hub, Salt Lake City, UT", "status": "Delayed in transit due to road closures"},
                ]
                act_del = None
            elif order.status == OrderStatus.DELIVERED.value:
                ship_status = ShipmentStatus.DELIVERED.value
                est_del = order.estimated_delivery
                act_del = order.estimated_delivery
                events = [
                    {"timestamp": (order.order_date + timedelta(days=1)).isoformat(), "location": "Distribution Hub", "status": "Shipment picked up"},
                    {"timestamp": (order.order_date + timedelta(days=2)).isoformat(), "location": "Regional Hub", "status": "Departed facility"},
                    {"timestamp": (order.order_date + timedelta(days=3)).isoformat(), "location": "Destination Facility", "status": "Out for delivery"},
                    {"timestamp": act_del.isoformat() if act_del else now.isoformat(), "location": "Customer Address", "status": "Delivered to front door"},
                ]
            else:
                ship_status = ShipmentStatus.IN_TRANSIT.value
                est_del = now + timedelta(days=2)
                act_del = None
                events = [
                    {"timestamp": (order.order_date + timedelta(days=1)).isoformat(), "location": "Main Logistics Center", "status": "Label created & picked up"},
                    {"timestamp": (now - timedelta(hours=12)).isoformat(), "location": "In Transit Facility", "status": "Departed sorting center"},
                ]

            shipment = Shipment(
                tracking_number=trk_no,
                order_id=order.id,
                courier_name=courier,
                status=ship_status,
                estimated_delivery=est_del,
                actual_delivery=act_del,
                tracking_events_json=json.dumps(events),
                created_at=order.order_date + timedelta(days=1),
            )
            db.add(shipment)

        db.commit()

        # 7. Create Return & Refund Scenarios
        print("[7/9] Creating Realistic Return & Refund Scenarios...")
        # Scenario 5: Eligible Refund pending approval (Order 1005 Evan Wright)
        order_1005 = created_orders[1005]
        ref_5 = RefundRequest(
            refund_number="REF-2024-8001",
            order_id=order_1005.id,
            payment_id=None,
            customer_id=order_1005.customer_id,
            amount=Decimal("89.00"),
            reason="Item arrived with cracked display casing. Eligible under 30-day hardware return policy.",
            status=RefundStatus.PENDING_APPROVAL.value,
            is_simulated=True,
            created_at=now - timedelta(hours=5),
        )
        db.add(ref_5)

        # Scenario 6: Ineligible Refund (Order 1006 Fiona Gallagher) - rejected because 48 days > 30 days
        order_1006 = created_orders[1006]
        ref_6 = RefundRequest(
            refund_number="REF-2024-8002",
            order_id=order_1006.id,
            payment_id=None,
            customer_id=order_1006.customer_id,
            amount=Decimal("179.00"),
            reason="Customer changed mind after 48 days.",
            status=RefundStatus.REJECTED.value,
            is_simulated=True,
            approved_by=ops_agent.id,
            approved_at=now - timedelta(days=1),
            rejection_reason="Return policy exceeded: purchases must be returned within 30 days of delivery. Delivered 48 days ago.",
            created_at=now - timedelta(days=2),
        )
        db.add(ref_6)

        # Scenario 7: Return Request in review (Order 1007 George Clark)
        order_1007 = created_orders[1007]
        ret_7 = ReturnRequest(
            request_number="RET-2024-9001",
            order_id=order_1007.id,
            customer_id=order_1007.customer_id,
            reason="Purchased wrong size. Requesting return and exchange instructions.",
            status=ReturnStatus.REQUESTED.value,
            requested_at=now - timedelta(days=2),
            resolution_notes="Awaiting return label generation.",
            created_at=now - timedelta(days=2),
        )
        db.add(ret_7)

        # Seed initial pending approval request for ref_5
        appr_payload = {
            "refund_request_id": ref_5.id,
            "refund_number": ref_5.refund_number,
            "order_number": order_1005.order_number,
            "customer_id": order_1005.customer_id,
            "customer_name": "Evan Wright",
            "amount": float(ref_5.amount),
            "reason": ref_5.reason,
            "is_simulated": True
        }
        appr_5 = ApprovalRequest(
            order_id=order_1005.id,
            request_type="refund",
            payload_json=json.dumps(appr_payload),
            status=ApprovalStatus.PENDING.value,
            requested_by_agent="OpsPilot Operations Engine",
            created_at=now - timedelta(hours=5),
        )
        db.add(appr_5)

        # Seed initial pending escalation for orphan transaction
        esc_1 = Escalation(
            customer_id=customers[3].id,
            reason="Orphan payment discrepancy: customer charged without confirmed order (TXN-2024-998811)",
            priority=TicketPriority.URGENT.value,
            status=EscalationStatus.PENDING.value,
            created_at=now - timedelta(hours=3),
        )
        db.add(esc_1)

        # 10. Create Initial Sample Conversations & Messages
        print("[10/10] Creating Initial Conversation & Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])

        db.commit()

        # 8. Create 10 Support Tickets
        print("[8/9] Creating 10 Support Tickets...")
        tickets_data = [
            ("TCK-2024-001", customers[0].id, created_orders[1001].id, "Headphones sound balance inquiry", "Inquiring about firmware update instructions for AuraPulse headphones.", TicketPriority.LOW.value, TicketStatus.RESOLVED.value, 8),
            ("TCK-2024-002", customers[1].id, created_orders[1002].id, "Where is my package? Delayed past estimated date", "My order ORD-2024-1002 has not arrived yet. Tracking says weather delay in Salt Lake City.", TicketPriority.HIGH.value, TicketStatus.OPEN.value, 1),
            ("TCK-2024-003", customers[2].id, created_orders[1003].id, "Payment was declined but my card has funds", "Tried checking out order ORD-2024-1003 and got decline code.", TicketPriority.MEDIUM.value, TicketStatus.IN_PROGRESS.value, 2),
            ("TCK-2024-004", customers[3].id, None, "Charged $149.50 but no order number received", "I see a charge on my bank statement TXN-2024-998811 but never received an email confirmation.", TicketPriority.URGENT.value, TicketStatus.OPEN.value, 0),
            ("TCK-2024-005", customers[4].id, created_orders[1005].id, "Received damaged package - refund requested", "Box was crushed and earbuds casing is cracked. Requesting full refund.", TicketPriority.HIGH.value, TicketStatus.WAITING_CUSTOMER.value, 1),
            ("TCK-2024-006", customers[5].id, created_orders[1006].id, "Return request rejected explanation needed", "Why was my return rejected for order ORD-2024-1006?", TicketPriority.LOW.value, TicketStatus.CLOSED.value, 1),
            ("TCK-2024-007", customers[6].id, created_orders[1007].id, "Exchange request for backpack size", "Need to exchange 25L for 30L if available.", TicketPriority.MEDIUM.value, TicketStatus.IN_PROGRESS.value, 3),
            ("TCK-2024-008", customers[7].id, created_orders[1008].id, "Can I update shipping address before dispatch?", "Need to modify apartment number to #4B before package leaves warehouse.", TicketPriority.HIGH.value, TicketStatus.RESOLVED.value, 1),
            ("TCK-2024-009", customers[8].id, created_orders[1009].id, "Invoice copy requested for corporate expense", "Please send official tax invoice with VAT number.", TicketPriority.LOW.value, TicketStatus.RESOLVED.value, 2),
            ("TCK-2024-010", customers[9].id, created_orders[1010].id, "Question about desk lamp warranty", "Does the 2-year manufacturer warranty cover the LED bulb?", TicketPriority.LOW.value, TicketStatus.CLOSED.value, 15),
        ]

        for tck_num, c_id, o_id, subj, desc, prio, st, days_ago in tickets_data:
            ticket = SupportTicket(
                ticket_number=tck_num,
                customer_id=c_id,
                order_id=o_id,
                subject=subj,
                description=desc,
                priority=prio,
                status=st,
                created_at=now - timedelta(days=days_ago),
            )
            db.add(ticket)

        db.commit()

        # 9. Initial Audit Trail
        print("[9/9] Creating Initial Audit Log Entries...")
        init_audit = AuditLog(
            user_id=admin_user.id,
            action="SYSTEM_INITIALIZATION",
            entity_type="system",
            entity_id="ENV_DEV",
            details_json=json.dumps({"description": "OpsPilot AI database initialized with verified production seed data.", "records": {"users": 3, "customers": 20, "products": 20, "orders": 30, "payments": 31, "shipments": 20, "tickets": 10}}),
            ip_address="127.0.0.1",
            created_at=now,
        )
        db.add(init_audit)
        # 10. Create Initial Sample Conversations & Messages
        print("[10/10] Creating Initial Conversation & Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])

        db.commit()

        # 10. Create Initial Sample Conversations and Messages
        print("[10/10] Creating Initial Conversation and Message Records...")
        conv1 = Conversation(
            customer_id=customers[0].id,
            channel="web_chat",
            status="resolved",
            created_at=now - timedelta(days=2)
        )
        db.add(conv1)
        db.flush()
        m1 = Message(
            conversation_id=conv1.id,
            sender_type="customer",
            content="Can you verify the status of order ORD-2024-1001?",
            created_at=now - timedelta(days=2)
        )
        m2 = Message(
            conversation_id=conv1.id,
            sender_type="agent",
            content="Order ORD-2024-1001 was delivered on schedule via FedEx tracking FDX-100100.",
            created_at=now - timedelta(days=2, minutes=-1)
        )
        db.add_all([m1, m2])
        db.commit()

        print("=" * 60)
        print("SEEDING COMPLETE SUCCESSFULLY!")
        print(f"Users: 3 (Admin: admin@opspilot.ai, Agent: agent@opspilot.ai, Customer: customer@opspilot.ai)")
        print(f"Customers: {len(customers)} records")
        print(f"Products: {len(products)} records")
        print(f"Orders: {len(created_orders)} records")
        print(f"Payments: {len(payments) + 1} records (including orphan payment TXN-2024-998811)")
        print(f"Shipments: 20 records (including delayed delivery ORD-2024-1002)")
        print(f"Support Tickets: 10 records")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"ERROR during database seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
