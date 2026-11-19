# Import all models so that Base.metadata has all entity tables registered
from backend.app.database.session import Base
from backend.app.models.models import (
    User,
    Customer,
    Product,
    Order,
    OrderItem,
    Payment,
    Shipment,
    ReturnRequest,
    RefundRequest,
    SupportTicket,
    Conversation,
    Message,
    Document,
    DocumentChunk,
    AgentRun,
    AgentEvent,
    ToolExecutionLog,
    ApprovalRequest,
    AuditLog,
    Escalation,
)

