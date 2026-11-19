import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, AuditLog

router = APIRouter()


class AuditLogResponse(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    timestamp: str


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action code"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
):
    """
    List immutable operational audit logs with filtering and pagination (Operations Agent & Admin).
    """
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)

    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for log in logs:
        try:
            det = json.loads(log.details_json) if log.details_json else {}
        except Exception:
            det = {"raw": log.details_json}

        result.append(
            AuditLogResponse(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
                user_name=log.user.full_name if log.user else None,
                details=det,
                ip_address=log.ip_address,
                timestamp=log.timestamp.isoformat()
            )
        )

    return result
