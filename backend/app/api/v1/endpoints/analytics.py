from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import (
    User, UserRole, Order, OrderStatus, Payment, PaymentStatus,
    Shipment, ShipmentStatus, RefundRequest, RefundStatus,
    SupportTicket, TicketStatus, Escalation, EscalationStatus,
    ApprovalRequest, ApprovalStatus, AgentRun, AgentRunStatus
)

router = APIRouter()


class AnalyticsOverviewResponse(BaseModel):
    total_orders: int
    total_revenue: float
    orders_by_status: Dict[str, int]
    delayed_shipments_count: int
    failed_payments_count: int
    orphan_payments_count: int
    pending_refunds_count: int
    total_refunded_amount: float
    pending_approvals_count: int
    open_tickets_count: int
    pending_escalations_count: int
    agent_runs_total: int
    agent_avg_duration_ms: int
    agent_success_rate_percent: float


class DailyTrendPoint(BaseModel):
    date: str
    orders_count: int
    tickets_count: int


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Real-time operational dashboard analytics derived from live SQL records.
    Never fabricated or hard-coded.
    """
    now = datetime.now(timezone.utc)

    # 1. Orders
    total_orders = db.query(func.count(Order.id)).scalar() or 0
    total_revenue = db.query(func.sum(Order.total_amount)).scalar() or 0.0

    order_status_rows = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    orders_by_status = {st: cnt for st, cnt in order_status_rows}

    # 2. Delayed Shipments
    delayed_shipments = db.query(func.count(Shipment.id)).filter(
        Shipment.status.in_([ShipmentStatus.IN_TRANSIT.value, ShipmentStatus.DELAYED.value, ShipmentStatus.PENDING.value]),
        Shipment.estimated_delivery < now
    ).scalar() or 0

    # 3. Payments
    failed_payments = db.query(func.count(Payment.id)).filter(Payment.status == PaymentStatus.FAILED.value).scalar() or 0
    orphan_payments = db.query(func.count(Payment.id)).filter(
        Payment.order_id == None,
        Payment.status == PaymentStatus.SUCCESSFUL.value
    ).scalar() or 0

    # 4. Refunds & Approvals
    pending_refunds = db.query(func.count(RefundRequest.id)).filter(
        RefundRequest.status == RefundStatus.PENDING_APPROVAL.value
    ).scalar() or 0

    total_refunded = db.query(func.sum(RefundRequest.amount)).filter(
        RefundRequest.status.in_([RefundStatus.APPROVED.value, RefundStatus.PROCESSED.value])
    ).scalar() or 0.0

    pending_approvals = db.query(func.count(ApprovalRequest.id)).filter(
        ApprovalRequest.status == ApprovalStatus.PENDING.value
    ).scalar() or 0

    # 5. Tickets & Escalations
    open_tickets = db.query(func.count(SupportTicket.id)).filter(
        SupportTicket.status.in_([TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value])
    ).scalar() or 0

    pending_escalations = db.query(func.count(Escalation.id)).filter(
        Escalation.status == EscalationStatus.PENDING.value
    ).scalar() or 0

    # 6. Agent Metrics
    agent_runs = db.query(func.count(AgentRun.id)).scalar() or 0
    completed_runs = db.query(func.count(AgentRun.id)).filter(
        AgentRun.status == AgentRunStatus.COMPLETED.value
    ).scalar() or 0
    avg_duration = db.query(func.avg(AgentRun.duration_ms)).filter(
        AgentRun.status == AgentRunStatus.COMPLETED.value
    ).scalar() or 0

    success_rate = (completed_runs / agent_runs * 100.0) if agent_runs > 0 else 100.0

    return AnalyticsOverviewResponse(
        total_orders=total_orders,
        total_revenue=float(total_revenue),
        orders_by_status=orders_by_status,
        delayed_shipments_count=delayed_shipments,
        failed_payments_count=failed_payments,
        orphan_payments_count=orphan_payments,
        pending_refunds_count=pending_refunds,
        total_refunded_amount=float(total_refunded),
        pending_approvals_count=pending_approvals,
        open_tickets_count=open_tickets,
        pending_escalations_count=pending_escalations,
        agent_runs_total=agent_runs,
        agent_avg_duration_ms=int(avg_duration),
        agent_success_rate_percent=round(success_rate, 1)
    )


@router.get("/trends", response_model=List[DailyTrendPoint])
def get_analytics_trends(
    days: int = 14,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Get 14-day rolling activity trends for operations charting.
    """
    now = datetime.now(timezone.utc)
    trends = []

    for i in range(days - 1, -1, -1):
        target_date = (now - timedelta(days=i)).date()
        date_str = target_date.strftime("%Y-%m-%d")

        # Count orders on this date
        ord_cnt = db.query(func.count(Order.id)).filter(
            func.date(Order.order_date) == date_str
        ).scalar() or 0

        # Count tickets created on this date
        tck_cnt = db.query(func.count(SupportTicket.id)).filter(
            func.date(SupportTicket.created_at) == date_str
        ).scalar() or 0

        trends.append(
            DailyTrendPoint(
                date=date_str,
                orders_count=ord_cnt,
                tickets_count=tck_cnt
            )
        )

    return trends

