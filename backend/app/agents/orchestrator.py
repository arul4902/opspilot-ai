import time
import json
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.llm import get_llm_client
from backend.app.core.broadcaster import EventBroadcaster
from backend.app.models.models import (
    AgentRun, AgentEvent, ToolExecutionLog, Conversation, Message, Customer,
    AgentRunStatus, ToolExecutionStatus
)
from backend.app.agents.intent_classifier import IntentClassifier, IntentClassificationResult
from backend.app.agents.triage_agent import TriageAgent, TriageContext
from backend.app.agents.investigation_agent import InvestigationAgent, InvestigationResult
from backend.app.agents.knowledge_agent import KnowledgeAgent, KnowledgeResult
from backend.app.agents.resolution_agent import ResolutionAgent, ResolutionResult
from backend.app.tools.registry import ToolRegistry


class ExecutionTimelineEvent(BaseModel):
    timestamp: str
    stage: str
    message: str
    details: Optional[Dict[str, Any]] = None


class AgentOrchestrationResult(BaseModel):
    run_id: int
    intent: str
    confidence: float
    status: str
    input_query: str
    llm_provider: str = "Deterministic Demo Engine"
    is_live_llm: bool = False
    timeline: List[ExecutionTimelineEvent] = []
    tools_executed: List[Dict[str, Any]] = []
    knowledge_sources: List[Dict[str, Any]] = []
    recommended_action: str
    requires_human_approval: bool = False
    approval_request_id: Optional[int] = None
    final_response: str
    duration_ms: int


class AgentOrchestrator:
    """
    Coordinator of the Multi-Agent System:
    Coordinates TriageAgent, InvestigationAgent, KnowledgeAgent, and ResolutionAgent
    through an explicit, audited 12-step operational pipeline with persistent event logging
    and real-time Server-Sent Events (SSE) streaming.
    """
    def __init__(self, db: Session):
        self.db = db
        self.triage_agent = TriageAgent(db)
        self.investigation_agent = InvestigationAgent(db)
        self.knowledge_agent = KnowledgeAgent(db)
        self.resolution_agent = ResolutionAgent(db)
        self.classifier = self.triage_agent.classifier
        self.registry = ToolRegistry(db)
        self.llm = get_llm_client()

    def record_event(self, agent_run_id: int, event_type: str, payload: Dict[str, Any]) -> AgentEvent:
        """
        Persist an execution event in the database for auditability and SSE replay.
        """
        event_id = f"evt_{agent_run_id}_{uuid.uuid4().hex[:8]}"
        evt = AgentEvent(
            agent_run_id=agent_run_id,
            event_id=event_id,
            event_type=event_type,
            payload_json=json.dumps(payload),
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(evt)
        self.db.commit()
        self.db.refresh(evt)
        return evt

    def process_request(
        self,
        query: str,
        customer_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> AgentOrchestrationResult:
        start_time = time.time()
        timeline: List[ExecutionTimelineEvent] = []
        all_tools_executed: List[Dict[str, Any]] = []

        def add_event(stage: str, msg: str, details: Optional[Dict[str, Any]] = None):
            ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
            timeline.append(ExecutionTimelineEvent(timestamp=ts, stage=stage, message=msg, details=details))
            logger.info(f"[{stage}] {msg}")

        # STEP 1: Receive customer request
        add_event("STEP_1_RECEIVED", f"Customer request received: \"{query}\"")

        # STEP 2 & 3: Triage Agent (Identity & Intent Classification)
        triage_ctx: TriageContext = self.triage_agent.triage(
            query=query,
            customer_id=customer_id,
            conversation_id=conversation_id,
            user_id=user_id
        )

        cust_label = triage_ctx.customer_name or f"Customer #{triage_ctx.customer_id}" if triage_ctx.customer_id else "General Guest"
        add_event("STEP_2_VALIDATED", f"Authenticated customer: {cust_label}")

        # Create AgentRun record in database
        agent_run = AgentRun(
            conversation_id=conversation_id,
            customer_id=triage_ctx.customer_id,
            input_query=query,
            status=AgentRunStatus.STARTED.value,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(agent_run)
        self.db.commit()
        self.db.refresh(agent_run)

        # Record agent.started
        self.record_event(agent_run.id, "agent.started", {
            "run_id": agent_run.id,
            "input_query": query,
            "customer_id": triage_ctx.customer_id,
            "customer_name": cust_label,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        classification = triage_ctx.classification
        agent_run.intent = classification.intent
        self.db.commit()

        # Record intent.detected
        self.record_event(agent_run.id, "intent.detected", {
            "run_id": agent_run.id,
            "intent": classification.intent,
            "confidence": classification.confidence,
            "entities": classification.entities.model_dump(),
            "reasoning": classification.reasoning
        })

        add_event(
            "STEP_3_INTENT_CLASSIFIED",
            f"Intent classified: {classification.intent} (confidence: {classification.confidence:.2f})",
            details={
                "intent": classification.intent,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
                "entities": classification.entities.model_dump()
            }
        )

        # STEP 4: Conversation Context
        if conversation_id:
            conv = self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
            msg_count = len(conv.messages) if conv else 0
            add_event("STEP_4_CONTEXT", f"Retrieved conversation history ({msg_count} prior messages)")
        else:
            add_event("STEP_4_CONTEXT", "Starting fresh investigation context")

        # STEP 5: Routing to Multi-Agent Pipeline
        add_event("STEP_5_ROUTING", f"Selecting investigation tools for workflow '{classification.intent}'")

        # Record investigation.started
        self.record_event(agent_run.id, "investigation.started", {
            "run_id": agent_run.id,
            "intent": classification.intent,
            "customer_id": triage_ctx.customer_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # STEP 6, 7, 8: Investigation Agent with Tool Callbacks
        step_idx = [6]
        def on_tool_start(tool_name: str, args: Dict[str, Any]):
            add_event(f"STEP_{step_idx[0]}_TOOL_START", f"Starting tool: {tool_name}({json.dumps(args)})")
            self.record_event(agent_run.id, "tool.started", {
                "run_id": agent_run.id,
                "tool_name": tool_name,
                "arguments": args
            })

        def on_tool_complete(tool_name: str, res: Dict[str, Any], is_ok: bool, err: Optional[str]):
            evt_type = "tool.completed" if is_ok else "tool.failed"
            add_event(f"STEP_{step_idx[0]}_RESULT", f"Tool '{tool_name}' finished (success={is_ok})")
            self.record_event(agent_run.id, evt_type, {
                "run_id": agent_run.id,
                "tool_name": tool_name,
                "success": is_ok,
                "result": res,
                "error": err
            })
            step_idx[0] += 1

        inv_result: InvestigationResult = self.investigation_agent.investigate(
            ctx=triage_ctx,
            agent_run_id=agent_run.id,
            on_tool_start=on_tool_start,
            on_tool_complete=on_tool_complete
        )

        for t in inv_result.tools_executed:
            all_tools_executed.append(t)

        # STEP 9: Knowledge Agent (RAG Policy Retrieval)
        know_result: KnowledgeResult = self.knowledge_agent.retrieve_grounding(
            ctx=triage_ctx,
            inv=inv_result,
            agent_run_id=agent_run.id
        )

        # Record rag.retrieval.completed
        self.record_event(agent_run.id, "rag.retrieval.completed", {
            "run_id": agent_run.id,
            "citations_count": len(know_result.citations),
            "citations": know_result.citations
        })

        add_event(
            f"STEP_{step_idx[0]}_KNOWLEDGE_RETRIEVED",
            f"Knowledge Agent retrieved {len(know_result.citations)} grounded policy citations from RAG.",
            details={"citations_count": len(know_result.citations)}
        )

        # STEP 10: Resolution Agent (HITL Approvals & Synthesis)
        add_event("STEP_10_SYNTHESIS", "Synthesizing evidence-grounded final response")
        res_result: ResolutionResult = self.resolution_agent.resolve(
            ctx=triage_ctx,
            inv=inv_result,
            know=know_result,
            agent_run_id=agent_run.id
        )
        for t in res_result.tools_executed:
            all_tools_executed.append(t)

        # If requires human approval, record approval.required
        if res_result.requires_human_approval:
            self.record_event(agent_run.id, "approval.required", {
                "run_id": agent_run.id,
                "approval_request_id": res_result.approval_request_id,
                "recommended_action": res_result.recommended_action,
                "reason": "Consequential financial/fulfillment action requires operator sign-off."
            })
            EventBroadcaster.broadcast("approval.created", {
                "approval_id": res_result.approval_request_id,
                "agent_run_id": agent_run.id,
                "action": res_result.recommended_action
            })

        # STEP 11: Save messages and execution details
        duration_ms = int((time.time() - start_time) * 1000)
        agent_run.status = AgentRunStatus.COMPLETED.value
        agent_run.resolution_plan = res_result.recommended_action
        agent_run.final_response = res_result.final_response
        agent_run.duration_ms = duration_ms
        agent_run.completed_at = datetime.now(timezone.utc)
        self.db.commit()

        if conversation_id:
            cust_msg = Message(
                conversation_id=conversation_id,
                sender_type="customer",
                content=query,
                metadata_json=json.dumps({"intent": classification.intent}),
                created_at=datetime.now(timezone.utc)
            )
            agent_msg = Message(
                conversation_id=conversation_id,
                sender_type="agent",
                content=res_result.final_response,
                metadata_json=json.dumps({"run_id": agent_run.id, "tools_called": [t["tool"] for t in all_tools_executed]}),
                created_at=datetime.now(timezone.utc)
            )
            self.db.add_all([cust_msg, agent_msg])
            self.db.commit()

        # Record agent.completed
        self.record_event(agent_run.id, "agent.completed", {
            "run_id": agent_run.id,
            "status": "completed",
            "recommended_action": res_result.recommended_action,
            "final_response": res_result.final_response,
            "requires_human_approval": res_result.requires_human_approval,
            "approval_request_id": res_result.approval_request_id,
            "duration_ms": duration_ms,
            "llm_provider": self.llm.provider_name,
            "is_live_llm": self.llm.is_live
        })

        # Broadcast live telemetry to dashboard
        EventBroadcaster.broadcast("agent.run_completed", {
            "run_id": agent_run.id,
            "intent": classification.intent,
            "duration_ms": duration_ms,
            "status": "completed"
        })

        # STEP 12: Complete
        add_event("STEP_12_COMPLETED", f"Investigation completed in {duration_ms}ms with {len(all_tools_executed)} tools executed.")

        return AgentOrchestrationResult(
            run_id=agent_run.id,
            intent=classification.intent,
            confidence=classification.confidence,
            status=agent_run.status,
            input_query=query,
            llm_provider=self.llm.provider_name,
            is_live_llm=self.llm.is_live,
            timeline=timeline,
            tools_executed=all_tools_executed,
            knowledge_sources=know_result.citations,
            recommended_action=res_result.recommended_action,
            requires_human_approval=res_result.requires_human_approval,
            approval_request_id=res_result.approval_request_id,
            final_response=res_result.final_response,
            duration_ms=duration_ms
        )

    async def process_request_stream(
        self,
        query: str,
        customer_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream the full investigation workflow via Server-Sent Events (SSE).
        Yields actual, unsimulated events as each step and backend tool executes.
        """
        start_time = time.time()
        agent_run_id = 0

        try:
            # 1. Triage & Authenticate
            triage_ctx: TriageContext = self.triage_agent.triage(
                query=query,
                customer_id=customer_id,
                conversation_id=conversation_id,
                user_id=user_id
            )
            cust_label = triage_ctx.customer_name or (f"Customer #{triage_ctx.customer_id}" if triage_ctx.customer_id else "General Guest")

            # Create AgentRun record
            agent_run = AgentRun(
                conversation_id=conversation_id,
                customer_id=triage_ctx.customer_id,
                input_query=query,
                status=AgentRunStatus.STARTED.value,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(agent_run)
            self.db.commit()
            self.db.refresh(agent_run)
            agent_run_id = agent_run.id

            # Emit: agent.started
            evt = self.record_event(agent_run_id, "agent.started", {
                "run_id": agent_run_id,
                "input_query": query,
                "customer_id": triage_ctx.customer_id,
                "customer_name": cust_label,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            yield f"id: {evt.event_id}\nevent: agent.started\ndata: {evt.payload_json}\n\n"
            await asyncio.sleep(0.04)

            # Emit: intent.detected
            classification = triage_ctx.classification
            agent_run.intent = classification.intent
            self.db.commit()

            evt = self.record_event(agent_run_id, "intent.detected", {
                "run_id": agent_run_id,
                "intent": classification.intent,
                "confidence": classification.confidence,
                "entities": classification.entities.model_dump(),
                "reasoning": classification.reasoning
            })
            yield f"id: {evt.event_id}\nevent: intent.detected\ndata: {evt.payload_json}\n\n"
            await asyncio.sleep(0.04)

            # Emit: investigation.started
            evt = self.record_event(agent_run_id, "investigation.started", {
                "run_id": agent_run_id,
                "intent": classification.intent,
                "customer_id": triage_ctx.customer_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            yield f"id: {evt.event_id}\nevent: investigation.started\ndata: {evt.payload_json}\n\n"
            await asyncio.sleep(0.04)

            # Tool execution queue with SSE yielding
            queue: asyncio.Queue = asyncio.Queue()

            def on_tool_start(tool_name: str, args: Dict[str, Any]):
                e = self.record_event(agent_run_id, "tool.started", {
                    "run_id": agent_run_id,
                    "tool_name": tool_name,
                    "arguments": args
                })
                queue.put_nowait((e.event_id, "tool.started", e.payload_json))

            def on_tool_complete(tool_name: str, res: Dict[str, Any], is_ok: bool, err: Optional[str]):
                evt_type = "tool.completed" if is_ok else "tool.failed"
                e = self.record_event(agent_run_id, evt_type, {
                    "run_id": agent_run_id,
                    "tool_name": tool_name,
                    "success": is_ok,
                    "result": res,
                    "error": err
                })
                queue.put_nowait((e.event_id, evt_type, e.payload_json))

            # Run investigation in thread to prevent blocking the async generator
            inv_result: InvestigationResult = await asyncio.to_thread(
                self.investigation_agent.investigate,
                triage_ctx,
                agent_run_id,
                on_tool_start,
                on_tool_complete
            )

            # Drain queued tool events over SSE
            while not queue.empty():
                e_id, e_name, e_data = queue.get_nowait()
                yield f"id: {e_id}\nevent: {e_name}\ndata: {e_data}\n\n"
                await asyncio.sleep(0.04)

            # Knowledge Agent RAG
            know_result: KnowledgeResult = await asyncio.to_thread(
                self.knowledge_agent.retrieve_grounding,
                triage_ctx,
                inv_result,
                agent_run_id
            )

            evt = self.record_event(agent_run_id, "rag.retrieval.completed", {
                "run_id": agent_run_id,
                "citations_count": len(know_result.citations),
                "citations": know_result.citations
            })
            yield f"id: {evt.event_id}\nevent: rag.retrieval.completed\ndata: {evt.payload_json}\n\n"
            await asyncio.sleep(0.04)

            # Resolution Agent
            res_result: ResolutionResult = await asyncio.to_thread(
                self.resolution_agent.resolve,
                triage_ctx,
                inv_result,
                know_result,
                agent_run_id
            )

            # Emit: approval.required if needed
            if res_result.requires_human_approval:
                evt = self.record_event(agent_run_id, "approval.required", {
                    "run_id": agent_run_id,
                    "approval_request_id": res_result.approval_request_id,
                    "recommended_action": res_result.recommended_action,
                    "reason": "Consequential financial/fulfillment action requires operator sign-off."
                })
                yield f"id: {evt.event_id}\nevent: approval.required\ndata: {evt.payload_json}\n\n"
                EventBroadcaster.broadcast("approval.created", {
                    "approval_id": res_result.approval_request_id,
                    "agent_run_id": agent_run_id,
                    "action": res_result.recommended_action
                })
                await asyncio.sleep(0.04)

            # Finalize AgentRun
            duration_ms = int((time.time() - start_time) * 1000)
            agent_run.status = AgentRunStatus.COMPLETED.value
            agent_run.resolution_plan = res_result.recommended_action
            agent_run.final_response = res_result.final_response
            agent_run.duration_ms = duration_ms
            agent_run.completed_at = datetime.now(timezone.utc)
            self.db.commit()

            # Emit: agent.completed
            evt = self.record_event(agent_run_id, "agent.completed", {
                "run_id": agent_run_id,
                "status": "completed",
                "recommended_action": res_result.recommended_action,
                "final_response": res_result.final_response,
                "requires_human_approval": res_result.requires_human_approval,
                "approval_request_id": res_result.approval_request_id,
                "duration_ms": duration_ms,
                "llm_provider": self.llm.provider_name,
                "is_live_llm": self.llm.is_live
            })
            yield f"id: {evt.event_id}\nevent: agent.completed\ndata: {evt.payload_json}\n\n"

            # Broadcast live telemetry to dashboard
            EventBroadcaster.broadcast("agent.run_completed", {
                "run_id": agent_run_id,
                "intent": classification.intent,
                "duration_ms": duration_ms,
                "status": "completed"
            })

        except Exception as e:
            logger.error(f"[Agent Stream Error] Run {agent_run_id}: {e}", exc_info=True)
            err_msg = str(e)
            if agent_run_id:
                try:
                    evt = self.record_event(agent_run_id, "agent.failed", {
                        "run_id": agent_run_id,
                        "error": err_msg,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    yield f"id: {evt.event_id}\nevent: agent.failed\ndata: {evt.payload_json}\n\n"
                except Exception:
                    yield f"event: agent.failed\ndata: {json.dumps({'error': err_msg})}\n\n"
