from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, Escalation, EscalationStatus
from backend.app.services.audit_service import AuditService

router = APIRouter()


class EscalationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="pending, in_review, resolved")
    assigned_to: Optional[int] = Field(None, description="Assigned operator user ID")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class EscalationResponse(BaseModel):
    id: int
    conversation_id: Optional[int] = None
    customer_id: int
    customer_name: Optional[str] = None
    reason: str
    priority: str
    status: str
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[str] = None
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: str


@router.get("", response_model=List[EscalationResponse])
def list_escalations(
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    List tier-2 escalations from operations queue (Operations Agent & Admin).
    """
    query = db.query(Escalation)
    if status_filter:
        query = query.filter(Escalation.status == status_filter)
    if priority_filter:
        query = query.filter(Escalation.priority == priority_filter)

    items = query.order_by(Escalation.created_at.desc()).offset(skip).limit(limit).all()

    return [
        EscalationResponse(
            id=e.id,
            conversation_id=e.conversation_id,
            customer_id=e.customer_id,
            customer_name=e.customer.name if e.customer else None,
            reason=e.reason,
            priority=e.priority,
            status=e.status,
            assigned_to=e.assigned_to,
            assigned_to_name=e.assignee.full_name if e.assignee else None,
            assigned_at=e.assigned_at.isoformat() if e.assigned_at else None,
            resolved_at=e.resolved_at.isoformat() if e.resolved_at else None,
            resolution_notes=e.resolution_notes,
            created_at=e.created_at.isoformat()
        )
        for e in items
    ]


@router.get("/{id}", response_model=EscalationResponse)
def get_escalation(
    id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific operational escalation.
    """
    e = db.query(Escalation).filter(Escalation.id == id).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Escalation ID {id} not found.")

    return EscalationResponse(
        id=e.id,
        conversation_id=e.conversation_id,
        customer_id=e.customer_id,
        customer_name=e.customer.name if e.customer else None,
        reason=e.reason,
        priority=e.priority,
        status=e.status,
        assigned_to=e.assigned_to,
        assigned_to_name=e.assignee.full_name if e.assignee else None,
        assigned_at=e.assigned_at.isoformat() if e.assigned_at else None,
        resolved_at=e.resolved_at.isoformat() if e.resolved_at else None,
        resolution_notes=e.resolution_notes,
        created_at=e.created_at.isoformat()
    )


@router.patch("/{id}", response_model=EscalationResponse)
def update_escalation(
    id: int,
    payload: EscalationUpdate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    Update escalation assignment, status, or resolution notes.
    """
    e = db.query(Escalation).filter(Escalation.id == id).first()
    if not e:
        raise HTTPException(status_code=404, detail=f"Escalation ID {id} not found.")

    now = datetime.now(timezone.utc)
    prev_status = e.status

    if payload.status:
        e.status = payload.status
        if payload.status == EscalationStatus.RESOLVED.value:
            e.resolved_at = now

    if payload.assigned_to is not None:
        e.assigned_to = payload.assigned_to
        e.assigned_at = now

    if payload.resolution_notes is not None:
        e.resolution_notes = payload.resolution_notes

    e.updated_at = now
    db.commit()
    db.refresh(e)

    AuditService.log_action(
        db=db,
        action="ESCALATION_UPDATED",
        entity_type="escalation",
        entity_id=str(e.id),
        user_id=current_user.id,
        details={
            "escalation_id": e.id,
            "previous_status": prev_status,
            "new_status": e.status,
            "assigned_to": e.assigned_to,
            "notes": payload.resolution_notes
        }
    )

    return get_escalation(id=e.id, current_user=current_user, db=db)

