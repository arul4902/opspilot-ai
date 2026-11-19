import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { OpsService } from '../../core/services/ops.service';
import { AgentOrchestrationResult, ExecutionTimelineEvent } from '../../core/models';

interface QuickScenario {
  label: string;
  tag: string;
  query: string;
  customerId: number;
}

@Component({
  selector: 'app-agent-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  template: `
    <div class="p-4 sm:p-6 flex flex-col h-full max-w-7xl mx-auto space-y-4">
      <!-- Workspace Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold tracking-tight text-primary">Agent Workspace</h1>
            <span class="badge badge-brand font-mono text-[10px]">PIPELINE ACTIVE</span>
          </div>
          <p class="text-xs text-secondary mt-0.5">Live multi-agent orchestration, telemetry inspection, and verifiable decision auditing</p>
        </div>
        <!-- Multi-Agent Stage Pipeline Indicator -->
        <div class="flex items-center gap-1.5 overflow-x-auto text-[11px] font-mono text-muted">
          <span class="px-2 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-secondary">1. Triage</span>
          <span class="text-muted">→</span>
          <span class="px-2 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-secondary">2. Investigation</span>
          <span class="text-muted">→</span>
          <span class="px-2 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-secondary">3. Knowledge RAG</span>
          <span class="text-muted">→</span>
          <span class="px-2 py-0.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)] text-secondary">4. Resolution</span>
        </div>
      </div>

      <!-- Quick Incident Scenarios Bar -->
      <div class="op-card p-3">
        <div class="flex items-center justify-between mb-2">
          <span class="tech-label">Operational Incident Templates:</span>
          <span class="text-[11px] text-muted hidden sm:inline">Select a verified test incident to run the 12-step pipeline</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          <button
            *ngFor="let s of scenarios"
            class="incident-btn"
            [class.active]="currentQuery === s.query"
            (click)="selectScenario(s)"
            [disabled]="isRunning()"
          >
            <span class="incident-tag">{{ s.tag }}</span>
            <span class="incident-title">{{ s.label }}</span>
          </button>
        </div>
      </div>

      <!-- Mobile/Tablet View Switcher Tab Bar -->
      <div class="flex lg:hidden border-b border-[var(--border-default)] gap-1 text-xs font-medium">
        <button 
          class="px-3 py-1.5 border-b-2 transition" 
          [class.border-brand]="mobileTab === 'input'"
          [class.text-primary]="mobileTab === 'input'"
          [class.border-transparent]="mobileTab !== 'input'"
          [class.text-muted]="mobileTab !== 'input'"
          (click)="mobileTab = 'input'"
        >
          1. Inquiry & Input
        </button>
        <button 
          class="px-3 py-1.5 border-b-2 transition" 
          [class.border-brand]="mobileTab === 'timeline'"
          [class.text-primary]="mobileTab === 'timeline'"
          [class.border-transparent]="mobileTab !== 'timeline'"
          [class.text-muted]="mobileTab !== 'timeline'"
          (click)="mobileTab = 'timeline'"
        >
          2. Execution Timeline
        </button>
        <button 
          class="px-3 py-1.5 border-b-2 transition" 
          [class.border-brand]="mobileTab === 'evidence'"
          [class.text-primary]="mobileTab === 'evidence'"
          [class.border-transparent]="mobileTab !== 'evidence'"
          [class.text-muted]="mobileTab !== 'evidence'"
          (click)="mobileTab = 'evidence'"
        >
          3. Evidence & RAG
        </button>
      </div>

      <!-- 3-Column Precision Console Layout -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0">
        <!-- Column 1: Customer Input & Inbound Channel (4 cols) -->
        <div 
          class="op-card lg:col-span-4 flex flex-col justify-between"
          [class.hidden]="mobileTab !== 'input' && isMobileView"
        >
          <div class="space-y-3">
            <div class="panel-header">
              <div class="panel-title">
                <svg width="16" height="16" class="w-4 h-4 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span>Customer Channel Input</span>
              </div>
              <span class="text-xs font-mono text-muted">Customer #{{ currentCustomerId() }}</span>
            </div>

            <div>
              <label class="op-label">Inbound Customer Message</label>
              <textarea
                [(ngModel)]="currentQuery"
                rows="4"
                class="op-input font-mono text-xs resize-none"
                placeholder="Enter customer message or select an incident scenario above..."
                [disabled]="isRunning()"
              ></textarea>
            </div>

            <div class="flex items-center justify-between text-xs text-muted">
              <span class="font-mono">Origin: Direct Web Chat</span>
              <button
                class="btn btn-primary btn-xs"
                (click)="runAgent()"
                [disabled]="isRunning() || !currentQuery.trim()"
              >
                <svg width="14" height="14" *ngIf="!isRunning()" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                <svg width="14" height="14" *ngIf="isRunning()" class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" stroke-opacity="0.25"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
                <span>{{ isRunning() ? 'Investigating...' : 'Execute Investigation' }}</span>
              </button>
            </div>

            <!-- Grounded Agent Response Display -->
            <div class="mt-4 pt-3 border-t border-[var(--border-subtle)]" *ngIf="latestResult() as res">
              <div class="flex items-center justify-between mb-2">
                <span class="tech-label">Synthesized Resolution:</span>
                <span class="badge badge-brand font-mono text-[10px]">{{ res.duration_ms }} ms</span>
              </div>
              <div class="p-3 rounded bg-[var(--bg-canvas)] border border-[var(--border-default)] text-xs text-primary leading-relaxed font-sans select-text">
                {{ res.final_response }}
              </div>
            </div>
          </div>

          <div class="text-[11px] text-muted pt-3 border-t border-[var(--border-subtle)] flex items-center justify-between">
            <span>Timeout limit: 30s</span>
            <span>Max steps: 8</span>
          </div>
        </div>

        <!-- Column 2: 12-Step Execution Timeline (4 cols) -->
        <div 
          class="op-card lg:col-span-4 flex flex-col"
          [class.hidden]="mobileTab !== 'timeline' && isMobileView"
        >
          <div class="panel-header">
            <div class="panel-title">
              <svg width="16" height="16" class="w-4 h-4 text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              <span>Execution Timeline</span>
            </div>
            <span class="badge" [ngClass]="isRunning() ? 'badge-warning' : (latestResult() ? 'badge-success' : 'badge-neutral')">
              {{ isRunning() ? 'PROCESSING' : (latestResult() ? 'COMPLETED' : 'IDLE') }}
            </span>
          </div>

          <div class="overflow-y-auto flex-1 pr-1 space-y-2 min-h-[300px]">
            <!-- Empty state -->
            <div *ngIf="!isRunning() && !latestResult()" class="py-16 text-center text-muted text-xs">
              <svg width="32" height="32" class="w-8 h-8 mx-auto mb-2 opacity-40 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              <span>Select an incident and click "Execute Investigation" to stream the multi-agent execution steps.</span>
            </div>

            <!-- Active spinner -->
            <div *ngIf="isRunning()" class="flex items-center gap-2 p-2 rounded bg-[var(--bg-subtle)] border border-[var(--border-default)] text-xs text-brand font-mono animate-pulse">
              <span class="w-2 h-2 rounded-full bg-brand animate-ping"></span>
              <span>Autonomous agents querying database, carrier APIs, and vector store...</span>
            </div>

            <!-- Timeline event list -->
            <div class="timeline-list" *ngIf="latestResult() as res">
              <div class="timeline-item" *ngFor="let ev of res.timeline">
                <div class="timeline-dot completed"></div>
                <div class="pl-2">
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="font-mono text-brand font-semibold">{{ ev.stage }}</span>
                    <span class="font-mono text-muted text-[10px]">{{ ev.timestamp }}</span>
                  </div>
                  <div class="text-xs text-primary mt-0.5">{{ ev.message }}</div>

                  <!-- Expandable intermediate details -->
                  <div *ngIf="ev.details" class="mt-1.5 p-2 rounded bg-[var(--bg-canvas)] border border-[var(--border-subtle)] font-mono text-[11px] text-muted overflow-x-auto">
                    <pre class="text-emerald-400 whitespace-pre-wrap">{{ ev.details | json }}</pre>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Column 3: Evidence, Citations & HITL Approval (4 cols) -->
        <div 
          class="op-card lg:col-span-4 flex flex-col"
          [class.hidden]="mobileTab !== 'evidence' && isMobileView"
        >
          <div class="panel-header">
            <div class="panel-title">
              <svg width="16" height="16" class="w-4 h-4 text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              <span>Evidence & Policy Grounding</span>
            </div>
            <span *ngIf="latestResult() as res" class="badge badge-neutral font-mono text-[10px]">
              {{ res.tools_executed.length }} Tools • {{ res.knowledge_sources.length }} Citations
            </span>
          </div>

          <div class="overflow-y-auto flex-1 pr-1 space-y-3 min-h-[300px]">
            <!-- Empty state -->
            <div *ngIf="!latestResult()" class="py-16 text-center text-muted text-xs">
              <svg width="32" height="32" class="w-8 h-8 mx-auto mb-2 opacity-40 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              <span>Retrieved database records, courier statuses, and policy citations appear here.</span>
            </div>

            <ng-container *ngIf="latestResult() as res">
              <!-- Intent Classification Node -->
              <div class="p-2.5 rounded bg-[var(--bg-elevated)] border border-[var(--border-default)]">
                <div class="tech-label mb-1">Intent Classification</div>
                <div class="flex items-center justify-between">
                  <span class="badge badge-brand font-mono">{{ res.intent }}</span>
                  <span class="font-mono text-xs text-muted">Confidence: {{ (res.confidence * 100) | number:'1.0-0' }}%</span>
                </div>
              </div>

              <!-- Human-In-The-Loop Approval Banner -->
              <div 
                class="p-3 rounded border"
                [ngClass]="res.requires_human_approval ? 'bg-amber-500/10 border-amber-500/30' : 'bg-emerald-500/10 border-emerald-500/30'"
              >
                <div class="flex items-center gap-1.5 mb-1">
                  <span class="w-2 h-2 rounded-full" [ngClass]="res.requires_human_approval ? 'bg-amber-400' : 'bg-emerald-400'"></span>
                  <span class="text-[11px] font-semibold uppercase tracking-wider" [ngClass]="res.requires_human_approval ? 'text-amber-400' : 'text-emerald-400'">
                    {{ res.requires_human_approval ? 'Human Approval Required' : 'Autonomous Action Authorized' }}
                  </span>
                </div>
                <p class="text-xs text-secondary mt-1 mb-2">{{ res.recommended_action }}</p>
                <div *ngIf="res.requires_human_approval" class="flex justify-end">
                  <a routerLink="/approvals" class="btn btn-warning btn-xs flex items-center gap-1">
                    <span>Review in Approvals Queue</span>
                    <svg width="12" height="12" class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
                  </a>
                </div>
              </div>

              <!-- Executed Backend Tools -->
              <div *ngIf="res.tools_executed.length > 0">
                <div class="tech-label mb-1.5">Executed Backend Tools:</div>
                <div class="space-y-1.5">
                  <div *ngFor="let t of res.tools_executed" class="p-2 rounded bg-[var(--bg-canvas)] border border-[var(--border-subtle)] text-xs">
                    <div class="flex items-center justify-between">
                      <span class="font-mono text-brand font-medium">{{ t.tool }}</span>
                      <span class="badge text-[10px]" [ngClass]="t.result['success'] ? 'badge-success' : 'badge-danger'">
                        {{ t.result['success'] ? 'SUCCESS' : 'DENIED' }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Grounded RAG Policy Citations -->
              <div *ngIf="res.knowledge_sources.length > 0">
                <div class="tech-label mb-1.5">Grounded Policy Citations (RAG):</div>
                <div class="space-y-2">
                  <div *ngFor="let c of res.knowledge_sources" class="p-2.5 rounded bg-[var(--bg-canvas)] border border-[var(--border-subtle)] text-xs space-y-1">
                    <div class="flex items-center justify-between text-[11px]">
                      <span class="font-mono text-secondary truncate max-w-[180px]" [title]="c.source_document">{{ c.source_document }}</span>
                      <span class="font-mono text-brand text-[10px]">{{ (c.relevance_score * 100) | number:'1.0-0' }}% match</span>
                    </div>
                    <div class="font-semibold text-primary text-[11px]">{{ c.section }}</div>
                    <p class="text-muted text-[11px] leading-relaxed italic bg-[var(--bg-elevated)] p-1.5 rounded">
                      "{{ c.snippet }}"
                    </p>
                  </div>
                </div>
              </div>
            </ng-container>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }

    .incident-btn {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      padding: 0.45rem 0.55rem;
      border-radius: var(--radius-sm);
      background: var(--bg-canvas);
      border: 1px solid var(--border-default);
      cursor: pointer;
      text-align: left;
      transition: all 0.12s ease;
      min-width: 0;
    }

    .incident-btn:hover:not(:disabled) {
      border-color: var(--border-hover);
      background: var(--bg-elevated);
    }

    .incident-btn.active {
      border-color: var(--brand-primary);
      background: var(--brand-bg);
    }

    .incident-tag {
      font-family: ui-monospace, monospace;
      font-size: 0.625rem;
      font-weight: 600;
      color: var(--brand-primary);
      line-height: 1;
    }

    .incident-title {
      font-size: 0.6875rem;
      color: var(--text-secondary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      width: 100%;
      margin-top: 0.25rem;
    }

    .incident-btn.active .incident-title {
      color: var(--text-primary);
      font-weight: 500;
    }
  `]
})
export class AgentWorkspaceComponent {
  private readonly opsService = inject(OpsService);

  readonly isRunning = signal(false);
  readonly currentCustomerId = signal<number>(2);
  readonly latestResult = signal<AgentOrchestrationResult | null>(null);

  currentQuery = 'Where is my order ORD-2024-1002? It has not arrived yet.';
  mobileTab: 'input' | 'timeline' | 'evidence' = 'input';

  get isMobileView(): boolean {
    return typeof window !== 'undefined' && window.innerWidth < 1024;
  }

  readonly scenarios: QuickScenario[] = [
    {
      label: 'Late Order',
      tag: 'INC-A',
      query: 'Where is my order ORD-2024-1002? It has not arrived yet.',
      customerId: 2
    },
    {
      label: 'Orphan Charge',
      tag: 'INC-B',
      query: 'My payment TXN-2024-998811 was deducted from my bank, but I have no order confirmation!',
      customerId: 2
    },
    {
      label: 'Payment Decline',
      tag: 'INC-C',
      query: 'Why did my payment fail for order ORD-2024-1003?',
      customerId: 3
    },
    {
      label: 'Return Policy',
      tag: 'INC-D',
      query: 'What is your return policy and how many days do I have to return an item?',
      customerId: 1
    },
    {
      label: 'Full Refund',
      tag: 'INC-E',
      query: 'I would like to request a refund for order ORD-2024-1005 because the items were defective.',
      customerId: 5
    },
    {
      label: 'Exchange Item',
      tag: 'INC-F',
      query: 'I want to return order ORD-2024-1007 because the size was too large.',
      customerId: 7
    }
  ];

  selectScenario(s: QuickScenario): void {
    this.currentQuery = s.query;
    this.currentCustomerId.set(s.customerId);
  }

  runAgent(): void {
    if (!this.currentQuery.trim() || this.isRunning()) return;

    this.isRunning.set(true);
    const q = this.currentQuery;
    const cid = this.currentCustomerId();

    // Initialize in-flight real-time timeline state
    const streamingResult: AgentOrchestrationResult = {
      run_id: 0,
      intent: 'CLASSIFYING...',
      confidence: 0,
      status: 'INVESTIGATING',
      input_query: q,
      llm_provider: 'OpsPilot Autonomous Pipeline',
      timeline: [
        {
          timestamp: new Date().toLocaleTimeString('en-GB'),
          stage: 'STREAM_CONNECTED',
          message: `Connected to SSE stream. Query: "${q}"`
        }
      ],
      tools_executed: [],
      knowledge_sources: [],
      recommended_action: 'Investigating operational records...',
      requires_human_approval: false,
      final_response: '',
      duration_ms: 0
    };
    this.latestResult.set(streamingResult);

    this.opsService.streamAgentMessage(q, cid).subscribe({
      next: (sseEvt) => {
        const data = sseEvt.data;
        const current = this.latestResult();
        if (!current) return;

        const ts = new Date().toLocaleTimeString('en-GB');

        switch (sseEvt.event) {
          case 'agent.started':
            current.run_id = data.run_id;
            current.timeline.push({
              timestamp: ts,
              stage: 'AGENT_STARTED',
              message: `Execution #${data.run_id} started for customer: ${data.customer_name || 'Guest'}`
            });
            break;

          case 'intent.detected':
            current.intent = data.intent;
            current.confidence = data.confidence;
            current.timeline.push({
              timestamp: ts,
              stage: 'INTENT_CLASSIFIED',
              message: `Intent detected: ${data.intent} (${Math.round(data.confidence * 100)}% confidence)`,
              details: data.reasoning ? { reasoning: data.reasoning } : undefined
            });
            break;

          case 'investigation.started':
            current.timeline.push({
              timestamp: ts,
              stage: 'INVESTIGATION_ROUTING',
              message: `Routing request through Multi-Agent System for workflow '${data.intent}'`
            });
            break;

          case 'tool.started':
            current.timeline.push({
              timestamp: ts,
              stage: 'TOOL_EXECUTE',
              message: `Invoking tool: ${data.tool_name}(${JSON.stringify(data.arguments || {})})`
            });
            break;

          case 'tool.completed':
            current.tools_executed.push({
              tool: data.tool_name,
              arguments: data.result?.arguments,
              result: data.result || { success: true }
            });
            current.timeline.push({
              timestamp: ts,
              stage: 'TOOL_RESULT',
              message: `Tool '${data.tool_name}' completed successfully.`
            });
            break;

          case 'tool.failed':
            current.tools_executed.push({
              tool: data.tool_name,
              arguments: {},
              result: { success: false, error: data.error }
            });
            current.timeline.push({
              timestamp: ts,
              stage: 'TOOL_FAILED',
              message: `Tool '${data.tool_name}' failed: ${data.error}`
            });
            break;

          case 'rag.retrieval.completed':
            current.knowledge_sources = data.citations || [];
            current.timeline.push({
              timestamp: ts,
              stage: 'RAG_GROUNDING',
              message: `Knowledge Agent retrieved ${data.citations_count || 0} policy citations from vector store.`
            });
            break;

          case 'approval.required':
            current.requires_human_approval = true;
            current.approval_request_id = data.approval_request_id;
            current.recommended_action = data.recommended_action;
            current.timeline.push({
              timestamp: ts,
              stage: 'APPROVAL_REQUIRED',
              message: `Action requires human authorization: ${data.recommended_action}`
            });
            break;

          case 'agent.completed':
            current.status = 'COMPLETED';
            current.recommended_action = data.recommended_action;
            current.final_response = data.final_response;
            current.duration_ms = data.duration_ms;
            current.requires_human_approval = data.requires_human_approval;
            current.approval_request_id = data.approval_request_id;
            if (data.llm_provider) current.llm_provider = data.llm_provider;
            current.timeline.push({
              timestamp: ts,
              stage: 'COMPLETED',
              message: `Autonomous investigation finished in ${data.duration_ms}ms.`
            });
            this.isRunning.set(false);
            break;

          case 'agent.failed':
            current.status = 'FAILED';
            current.timeline.push({
              timestamp: ts,
              stage: 'FAILED',
              message: `Agent execution failed: ${data.error}`
            });
            this.isRunning.set(false);
            break;
        }

        this.latestResult.set({ ...current });
      },
      error: (err) => {
        console.warn('SSE stream failed, falling back to standard HTTP POST...', err);
        this.opsService.sendAgentMessage(q, cid).subscribe({
          next: (res) => {
            this.latestResult.set(res);
            this.isRunning.set(false);
          },
          error: (syncErr) => {
            console.error('Synchronous agent invocation also failed', syncErr);
            this.isRunning.set(false);
          }
        });
      },
      complete: () => {
        this.isRunning.set(false);
      }
    });
  }
}
