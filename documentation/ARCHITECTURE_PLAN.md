# OpsPilot AI – Architecture & Technical Implementation Plan

**OpsPilot AI** is an enterprise-grade autonomous e-commerce operations platform designed to automate investigation, policy retrieval (RAG), tool calling, and human-in-the-loop approvals for complex customer operational issues.

---

## 1. High-Level Architecture

```mermaid
flowchart TD
    subgraph Frontend["Angular SaaS Client"]
        UI[Workspace & Dashboard UI]
        AuthGuard[JWT Auth Guard & RBAC]
        State[RxJS State & Services]
    end

    subgraph Backend["FastAPI Orchestration Core"]
        API[REST Endpoints /api/v1]
        Security[JWT & Password Security]
        Orchestrator[Agent Orchestrator Engine]
        
        subgraph Agents["Logical Agent Network"]
            TriageAgent[Triage Agent]
            InvestigateAgent[Investigation Agent]
            KnowledgeAgent[Knowledge RAG Agent]
            ResolutionAgent[Resolution Agent]
        end
        
        subgraph Tools["Deterministic Backend Tools"]
            T1[get_order_details]
            T2[get_payment_details]
            T3[check_delivery_status]
            T4[search_return_policy]
            T5[create_return_request]
            T6[initiate_refund_request]
            T7[create_support_ticket]
            T8[escalate_to_human]
            T9[search_customer_history]
        end

        HITL[Human Approval Engine]
        Audit[Audit & Execution Logger]
    end

    subgraph DataStorage["Persistence & Vector Layer"]
        DB[(SQLite / PostgreSQL Relational DB)]
        Chroma[(ChromaDB Vector Store)]
    end

    UI --> API
    API --> Security
    API --> Orchestrator
    Orchestrator --> Agents
    Agents --> Tools
    Tools --> DB
    KnowledgeAgent --> Chroma
    Orchestrator --> HITL
    HITL --> DB
    Orchestrator --> Audit
    Audit --> DB
```

---

## 2. Multi-Phase Roadmap

| Phase | Title | Scope | Status |
|---|---|---|---|
| **Phase 1** | **Foundation & Data Engine** | Project scaffolding, FastAPI setup, Angular setup, SQLAlchemy models (18 tables), JWT authentication & RBAC, realistic seed data (20 customers, 30 orders, 20 products, 31 payments, 20 shipments, 10 tickets, all 7 business scenarios), automated pytest suite. | **COMPLETED** |
| **Phase 2** | **Core Business Domain APIs** | CRUD & domain endpoints for Orders, Payments, Shipments, Returns, Refunds, and Support Tickets. Operational business rules: delivery delay detector, payment discrepancy investigator, 30-day refund eligibility validator, simulated refund requester with approval hook. 28 automated tests passing. | **COMPLETED** |
| **Phase 3** | **AI Agent & Tool Execution** | Deterministic orchestrator, 9 business tools with input/output schemas, execution timeouts, loop prevention, structured execution logging. | Planned |
| **Phase 4** | **Enterprise Knowledge RAG** | Document ingestion (PDF & TXT), chunking, embeddings, ChromaDB vector retrieval, source citations, prompt defense against prompt injections. | Planned |
| **Phase 5** | **Multi-Agent Orchestration & HITL** | Triage, Investigation, Knowledge, Resolution agents with shared validated state, Human-in-the-loop approval workflow, operations queue escalations, audit trail. | Planned |
| **Phase 6** | **Angular Operations Workspace** | Dark SaaS dashboard theme (`#0A0E27`, `#00D4FF`), Agent Workspace with interactive timeline, approval queue, analytics charts, knowledge manager. | Planned |
| **Phase 7** | **E2E Testing & Documentation** | Automated integration tests for all 6 end-to-end scenarios (A to F), Swagger documentation, comprehensive README.md, and `PROJECT_WALKTHROUGH.md` for technical interviews. | Planned |

