import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import (
    User, UserRole, ApprovalRequest, ApprovalStatus,
    RefundRequest, RefundStatus, Order, OrderStatus, AuditLog
)
from backend.app.services.audit_service import AuditService
from backend.app.core.broadcaster import EventBroadcaster

router = APIRouter()


class ApprovalDecisionRequest(BaseModel):
    comments: Optional[str] = Field(None, description="Optional operator review comments or justification")


class ApprovalItemResponse(BaseModel):
    id: int
    agent_run_id: Optional[int] = None
    order_id: Optional[int] = None
    request_type: str
    status: str
    requested_by_agent: str
    payload: Dict[str, Any]
    reviewed_by: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    comments: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    created_at: str


@router.get("", response_model=List[ApprovalItemResponse])
def list_approval_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    List Human-In-The-Loop approval queue requests (Operations Agent & Admin).
    """
    query = db.query(ApprovalRequest)
    if status_filter:
        query = query.filter(ApprovalRequest.status == status_filter)

    items = query.order_by(ApprovalRequest.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for item in items:
        try:
            p = json.loads(item.payload_json) if item.payload_json else {}
        except Exception:
            p = {"raw": item.payload_json}
        try:
            ex = json.loads(item.execution_result_json) if item.execution_result_json else None
        except Exception:
            ex = {"raw": item.execution_result_json}

        reviewer_name = item.reviewer.full_name if item.reviewer else None

        result.append(
            ApprovalItemResponse(
                id=item.id,
                agent_run_id=item.agent_run_id,
                order_id=item.order_id,
                request_type=item.request_type,
                status=item.status,
                requested_by_agent=item.requested_by_agent,
                payload=p,
                reviewed_by=item.reviewed_by,
                reviewed_by_name=reviewer_name,
                reviewed_at=item.reviewed_at.isoformat() if item.reviewed_at else None,
                comments=item.comments,
                execution_result=ex,
                created_at=item.created_at.isoformat()
            )
        )
    return result


@router.get("/{id}", response_model=ApprovalItemResponse)
def get_approval_request(
    id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Inspect single approval request with full operational payload and evidence audit.
    """
    item = db.query(ApprovalRequest).filter(ApprovalRequest.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Approval request ID {id} not found.")

    try:
        p = json.loads(item.payload_json) if item.payload_json else {}
    except Exception:
        p = {"raw": item.payload_json}
    try:
        ex = json.loads(item.execution_result_json) if item.execution_result_json else None
    except Exception:
        ex = {"raw": item.execution_result_json}

    return ApprovalItemResponse(
        id=item.id,
        agent_run_id=item.agent_run_id,
        order_id=item.order_id,
        request_type=item.request_type,
        status=item.status,
        requested_by_agent=item.requested_by_agent,
        payload=p,
        reviewed_by=item.reviewed_by,
        reviewed_by_name=item.reviewer.full_name if item.reviewer else None,
        reviewed_at=item.reviewed_at.isoformat() if item.reviewed_at else None,
        comments=item.comments,
        execution_result=ex,
        created_at=item.created_at.isoformat()
    )


@router.post("/{id}/approve", response_model=ApprovalItemResponse)
def approve_request(
    id: int,
    decision: ApprovalDecisionRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Approve an operation in the Human-In-The-Loop queue.
    Executes the business operation (e.g. simulated refund execution or status transition),
    updates records, and writes to the immutable audit log.
    """
    item = db.query(ApprovalRequest).filter(ApprovalRequest.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Approval request ID {id} not found.")

    if item.status != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve request: current status is '{item.status}'."
        )

    now = datetime.now(timezone.utc)
    item.status = ApprovalStatus.APPROVED.value
    item.reviewed_by = current_user.id
    item.reviewed_at = now
    item.comments = decision.comments or "Approved by operations manager."

    execution_result = {}

    # Execute underlying business action
    try:
        payload = json.loads(item.payload_json) if item.payload_json else {}
    except Exception:
        payload = {}

    if item.request_type == "refund":
        refund_id = payload.get("refund_request_id")
        refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first() if refund_id else None
        if not refund and item.order_id:
            refund = db.query(RefundRequest).filter(
                RefundRequest.order_id == item.order_id,
                RefundRequest.status == RefundStatus.PENDING_APPROVAL.value
            ).first()

        if refund:
            refund.status = RefundStatus.APPROVED.value
            refund.approved_by = current_user.id
            refund.approved_at = now

            # Simulate gateway execution
            simulated_txn_code = f"SIM-REF-{now.strftime('%Y%m%d%H%M%S')}"
            execution_result = {
                "action": "SIMULATED_REFUND_EXECUTED",
                "refund_number": refund.refund_number,
                "amount": float(refund.amount),
                "gateway_reference": simulated_txn_code,
                "timestamp": now.isoformat(),
                "executed_by": current_user.email
            }
            # Transition refund to processed
            refund.status = RefundStatus.PROCESSED.value

    elif item.request_type == "order_cancellation" and item.order_id:
        order = db.query(Order).filter(Order.id == item.order_id).first()
        if order:
            order.status = OrderStatus.CANCELLED.value
            execution_result = {
                "action": "ORDER_CANCELLED",
                "order_number": order.order_number,
                "previous_status": order.status,
                "timestamp": now.isoformat()
            }

    item.execution_result_json = json.dumps(execution_result)
    db.commit()
    db.refresh(item)

    # Immutable Audit Log
    AuditService.log_action(
        db=db,
        action="APPROVAL_REQUEST_APPROVED",
        entity_type="approval_request",
        entity_id=str(item.id),
        user_id=current_user.id,
        details={
            "approval_id": item.id,
            "request_type": item.request_type,
            "decision": "APPROVED",
            "comments": item.comments,
            "execution_result": execution_result
        }
    )

    EventBroadcaster.broadcast("approval.reviewed", {
        "approval_id": item.id,
        "status": "approved",
        "request_type": item.request_type,
        "reviewed_by": current_user.full_name,
        "order_id": item.order_id
    })

    return get_approval_request(id=item.id, current_user=current_user, db=db)


@router.post("/{id}/reject", response_model=ApprovalItemResponse)
def reject_request(
    id: int,
    decision: ApprovalDecisionRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Reject an operation in the Human-In-The-Loop queue with mandatory explanation.
    """
    item = db.query(ApprovalRequest).filter(ApprovalRequest.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail=f"Approval request ID {id} not found.")

    if item.status != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request: current status is '{item.status}'."
        )

    now = datetime.now(timezone.utc)
    item.status = ApprovalStatus.REJECTED.value
    item.reviewed_by = current_user.id
    item.reviewed_at = now
    item.comments = decision.comments or "Rejected by operations manager."

    # Update refund request if applicable
    try:
        payload = json.loads(item.payload_json) if item.payload_json else {}
    except Exception:
        payload = {}

    if item.request_type == "refund":
        refund_id = payload.get("refund_request_id")
        refund = db.query(RefundRequest).filter(RefundRequest.id == refund_id).first() if refund_id else None
        if not refund and item.order_id:
            refund = db.query(RefundRequest).filter(
                RefundRequest.order_id == item.order_id,
                RefundRequest.status == RefundStatus.PENDING_APPROVAL.value
            ).first()

        if refund:
            refund.status = RefundStatus.REJECTED.value
            refund.rejection_reason = item.comments

    db.commit()
    db.refresh(item)

    # Immutable Audit Log
    AuditService.log_action(
        db=db,
        action="APPROVAL_REQUEST_REJECTED",
        entity_type="approval_request",
        entity_id=str(item.id),
        user_id=current_user.id,
        details={
            "approval_id": item.id,
            "request_type": item.request_type,
            "decision": "REJECTED",
            "comments": item.comments
        }
    )

    EventBroadcaster.broadcast("approval.reviewed", {
        "approval_id": item.id,
        "status": "rejected",
        "request_type": item.request_type,
        "reviewed_by": current_user.full_name,
        "order_id": item.order_id
    })

    return get_approval_request(id=item.id, current_user=current_user, db=db)

