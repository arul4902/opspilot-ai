import json
from typing import Any, List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.api.deps import get_db, get_current_user, require_roles
from backend.app.models.models import User, UserRole, AgentRun, AgentEvent, ToolExecutionLog, Customer
from backend.app.agents.orchestrator import AgentOrchestrator, AgentOrchestrationResult

router = APIRouter()


class AgentMessageRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Customer request query string")
    customer_id: Optional[int] = Field(None, description="Optional customer ID")
    conversation_id: Optional[int] = Field(None, description="Optional active conversation ID")


class ToolLogResponse(BaseModel):
    id: int
    tool_name: str
    input_arguments: Dict[str, Any]
    output_result: Dict[str, Any]
    status: str
    error_message: Optional[str] = None
    duration_ms: int
    executed_at: str


class AgentRunDetailResponse(BaseModel):
    id: int
    intent: Optional[str] = None
    input_query: str
    status: str
    resolution_plan: Optional[str] = None
    final_response: Optional[str] = None
    duration_ms: int
    created_at: str
    completed_at: Optional[str] = None
    customer_id: Optional[int] = None
    tool_logs: List[ToolLogResponse] = []


def _get_customer_id_for_user(user: User, db: Session) -> Optional[int]:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer:
        return customer.id
    customer = db.query(Customer).filter(Customer.email == user.email).first()
    return customer.id if customer else None


@router.post("/message", response_model=AgentOrchestrationResult)
def send_agent_message(
    payload: AgentMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Submit customer query to the OpsPilot Autonomous Agent Pipeline.
    Executes intent classification, multi-step tool execution, grounded RAG verification,
    human approval checks, and returns real-time execution timeline.
    """
    effective_cust_id = payload.customer_id
    if current_user.role == UserRole.CUSTOMER.value:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        effective_cust_id = user_cust_id or payload.customer_id

    orchestrator = AgentOrchestrator(db)
    result = orchestrator.process_request(
        query=payload.query,
        customer_id=effective_cust_id,
        conversation_id=payload.conversation_id,
        user_id=current_user.id
    )
    return result


@router.post("/stream")
async def stream_agent_message(
    payload: AgentMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Real-Time Server-Sent Events (SSE) investigation stream.
    Streams actual execution events: agent.started, intent.detected, investigation.started,
    tool.started, tool.completed, rag.retrieval.completed, approval.required, agent.completed.
    """
    effective_cust_id = payload.customer_id
    if current_user.role == UserRole.CUSTOMER.value:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        effective_cust_id = user_cust_id or payload.customer_id

    orchestrator = AgentOrchestrator(db)

    return StreamingResponse(
        orchestrator.process_request_stream(
            query=payload.query,
            customer_id=effective_cust_id,
            conversation_id=payload.conversation_id,
            user_id=current_user.id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.get("/runs", response_model=List[Dict[str, Any]])
def list_agent_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
) -> Any:
    """
    List historical AI agent runs and investigation traces (Operations Agent & Admin).
    """
    query = db.query(AgentRun)
    if status:
        query = query.filter(AgentRun.status == status)

    runs = query.order_by(AgentRun.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": r.id,
            "intent": r.intent,
            "input_query": r.input_query,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "tool_call_count": len(r.tool_logs),
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "customer_id": r.customer_id
        }
        for r in runs
    ]


@router.get("/runs/{id}", response_model=AgentRunDetailResponse)
def get_agent_run_detail(
    id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
) -> Any:
    """
    Inspect single agent run with full tool execution trace and evidence audit.
    """
    run = db.query(AgentRun).filter(AgentRun.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Agent Run ID {id} not found.")

    tool_logs = []
    for log in run.tool_logs:
        try:
            inp = json.loads(log.input_arguments_json) if log.input_arguments_json else {}
        except Exception:
            inp = {"raw": log.input_arguments_json}
        try:
            out = json.loads(log.output_result_json) if log.output_result_json else {}
        except Exception:
            out = {"raw": log.output_result_json}

        tool_logs.append(
            ToolLogResponse(
                id=log.id,
                tool_name=log.tool_name,
                input_arguments=inp,
                output_result=out,
                status=log.status,
                error_message=log.error_message,
                duration_ms=log.duration_ms,
                executed_at=log.executed_at.isoformat()
            )
        )

    return AgentRunDetailResponse(
        id=run.id,
        intent=run.intent,
        input_query=run.input_query,
        status=run.status,
        resolution_plan=run.resolution_plan,
        final_response=run.final_response,
        duration_ms=run.duration_ms,
        created_at=run.created_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        customer_id=run.customer_id,
        tool_logs=tool_logs
    )


@router.get("/runs/{id}/events")
def get_agent_run_events(
    id: int,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value, UserRole.OPERATIONS_AGENT.value])),
    db: Session = Depends(get_db)
) -> Any:
    """
    Retrieve chronological list of immutable execution events persisted for an agent run.
    Powering the Live Execution Inspector for deep retrospective replay.
    """
    run = db.query(AgentRun).filter(AgentRun.id == id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Agent Run ID {id} not found.")

    events = db.query(AgentEvent).filter(AgentEvent.agent_run_id == id).order_by(AgentEvent.id.asc()).all()
    results = []
    for evt in events:
        try:
            p = json.loads(evt.payload_json) if evt.payload_json else {}
        except Exception:
            p = {"raw": evt.payload_json}
        results.append({
            "id": evt.id,
            "event_id": evt.event_id,
            "event_type": evt.event_type,
            "payload": p,
            "created_at": evt.created_at.isoformat()
        })
    return results


