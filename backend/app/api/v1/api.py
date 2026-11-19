from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    auth,
    orders,
    payments,
    shipments,
    returns_refunds,
    tickets,
    agent,
    knowledge,
    approvals,
    escalations,
    audit_logs,
    analytics,
    events,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["Shipments"])
api_router.include_router(returns_refunds.router, tags=["Returns & Refunds"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["Support Tickets"])
api_router.include_router(agent.router, prefix="/agent", tags=["AI Agent"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Base & RAG"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["Human Approval Queue"])
api_router.include_router(escalations.router, prefix="/escalations", tags=["Escalations Queue"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Reporting"])
api_router.include_router(events.router, prefix="/events", tags=["Real-Time Operational Events"])

