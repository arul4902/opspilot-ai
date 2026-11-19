import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OpsService } from '../../core/services/ops.service';
import { AgentRunSummary } from '../../core/models';

interface AgentEventItem {
  id: number;
  event_id: string;
  event_type: string;
  payload: Record<string, any>;
  created_at: string;
}

@Component({
  selector: 'app-execution-inspector',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-4 sm:p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold tracking-tight text-primary">Live Execution Inspector</h1>
            <span class="badge badge-brand font-mono text-[10px]">SSE TELEMETRY</span>
          </div>
          <p class="text-xs text-secondary mt-0.5">Immutable audit trail of agent runs, real-time event sequences, and tool execution traces</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadRuns()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/>
            </svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <!-- Main Layout: Run List Table and Detail Drawer -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- Runs List -->
        <div class="lg:col-span-7 space-y-3">
          <div class="flex items-center justify-between text-xs">
            <span class="text-muted font-mono">{{ runs().length }} Executions Recorded</span>
            <div class="flex items-center gap-1.5">
              <span class="text-muted">Filter:</span>
              <button 
                *ngFor="let f of ['all', 'completed', 'started', 'failed']"
                class="px-2 py-0.5 rounded text-[11px] font-medium uppercase tracking-wider"
                [ngClass]="activeFilter() === f ? 'bg-[var(--brand-primary)] text-white' : 'bg-[var(--bg-elevated)] text-muted hover:text-secondary'"
                (click)="activeFilter.set(f)"
              >
                {{ f }}
              </button>
            </div>
          </div>

          <div class="op-table-container">
            <table class="op-table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Intent</th>
                  <th>Input Query</th>
                  <th>Duration</th>
                  <th>Tools</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  *ngFor="let r of filteredRuns()" 
                  (click)="selectRun(r.id)"
                  class="cursor-pointer"
                  [class.bg-[var(--bg-hover)]]="selectedRunId() === r.id"
                >
                  <td class="font-mono text-brand font-semibold">#{{ r.id }}</td>
                  <td>
                    <span class="badge badge-neutral text-[10px] font-mono">{{ r.intent || 'TRIAGE' }}</span>
                  </td>
                  <td class="max-w-[180px] truncate text-secondary" [title]="r.input_query">
                    {{ r.input_query }}
                  </td>
                  <td class="font-mono text-primary text-xs">{{ r.duration_ms }}ms</td>
                  <td class="font-mono text-muted text-xs">{{ r.tool_call_count }} calls</td>
                  <td>
                    <span class="badge" [ngClass]="getStatusBadge(r.status)">
                      {{ r.status | uppercase }}
                    </span>
                  </td>
                  <td>
                    <button class="btn btn-secondary btn-xs py-0.5 px-2 text-[11px]" (click)="selectRun(r.id); $event.stopPropagation()">
                      Inspect
                    </button>
                  </td>
                </tr>
                <tr *ngIf="filteredRuns().length === 0">
                  <td colspan="7" class="text-center py-8 text-muted">
                    No agent runs match the selected criteria.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Detail Inspection Panel -->
        <div class="lg:col-span-5 space-y-3">
          <div class="op-card" *ngIf="selectedRun(); else noRunSelected">
            <div class="panel-header pb-2 border-b border-[var(--border-subtle)]">
              <div class="panel-title">
                <span class="font-mono text-brand font-semibold">Execution #{{ selectedRun()!.id }}</span>
                <span class="badge" [ngClass]="getStatusBadge(selectedRun()!.status)">{{ selectedRun()!.status | uppercase }}</span>
              </div>
              <span class="font-mono text-xs text-muted">{{ selectedRun()!.duration_ms }}ms</span>
            </div>

            <!-- Query & Plan -->
            <div class="mt-3 space-y-2 text-xs">
              <div>
                <span class="text-muted block text-[10px] uppercase font-semibold">Inquiry:</span>
                <div class="p-2 rounded bg-[var(--bg-subtle)] text-primary mt-1 border border-[var(--border-subtle)]">
                  "{{ selectedRun()!.input_query }}"
                </div>
              </div>

              <div *ngIf="selectedRun()!.resolution_plan">
                <span class="text-muted block text-[10px] uppercase font-semibold">Recommended Action:</span>
                <div class="font-mono text-brand text-xs mt-0.5">{{ selectedRun()!.resolution_plan }}</div>
              </div>
            </div>

            <!-- Tab Switcher: Events vs Tools -->
            <div class="mt-4 border-b border-[var(--border-subtle)] flex gap-2">
              <button 
                class="px-3 py-1.5 text-xs font-semibold border-b-2 -mb-px transition-all"
                [ngClass]="activeTab() === 'events' ? 'border-[var(--brand-primary)] text-brand' : 'border-transparent text-muted hover:text-secondary'"
                (click)="activeTab.set('events')"
              >
                Immutable Event Stream ({{ events().length }})
              </button>
              <button 
                class="px-3 py-1.5 text-xs font-semibold border-b-2 -mb-px transition-all"
                [ngClass]="activeTab() === 'tools' ? 'border-[var(--brand-primary)] text-brand' : 'border-transparent text-muted hover:text-secondary'"
                (click)="activeTab.set('tools')"
              >
                Tool Traces ({{ selectedRun()!.tool_logs?.length || 0 }})
              </button>
            </div>

            <!-- Events Tab -->
            <div *ngIf="activeTab() === 'events'" class="mt-3 space-y-2 max-h-[460px] overflow-y-auto pr-1">
              <div 
                *ngFor="let evt of events()" 
                class="p-2.5 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-xs space-y-1"
              >
                <div class="flex items-center justify-between">
                  <span class="font-mono font-semibold text-[11px]" [ngClass]="getEventColor(evt.event_type)">
                    {{ evt.event_type }}
                  </span>
                  <span class="font-mono text-[10px] text-muted">{{ evt.created_at | date:'HH:mm:ss' }}</span>
                </div>
                <div class="font-mono text-[10px] text-muted truncate">ID: {{ evt.event_id }}</div>
                <pre class="mt-1 p-1.5 rounded bg-[var(--bg-canvas)] text-[10px] font-mono text-secondary overflow-x-auto max-h-28 border border-[var(--border-subtle)]">{{ evt.payload | json }}</pre>
              </div>
              <div *ngIf="events().length === 0" class="text-center py-6 text-muted text-xs">
                No events recorded for this execution.
              </div>
            </div>

            <!-- Tools Tab -->
            <div *ngIf="activeTab() === 'tools'" class="mt-3 space-y-2 max-h-[460px] overflow-y-auto pr-1">
              <div 
                *ngFor="let tool of selectedRun()!.tool_logs"
                class="p-2.5 rounded bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-xs space-y-1.5"
              >
                <div class="flex items-center justify-between">
                  <span class="font-mono font-semibold text-primary text-[11px]">{{ tool.tool_name }}</span>
                  <span class="badge" [ngClass]="tool.status === 'success' ? 'badge-success' : 'badge-danger'">
                    {{ tool.status | uppercase }}
                  </span>
                </div>
                <div class="text-[10px] text-muted font-mono">Duration: {{ tool.duration_ms }}ms</div>
                <div>
                  <span class="text-[10px] text-muted uppercase">Arguments:</span>
                  <pre class="p-1 rounded bg-[var(--bg-canvas)] font-mono text-[10px] text-secondary mt-0.5 border border-[var(--border-subtle)]">{{ tool.input_arguments | json }}</pre>
                </div>
                <div>
                  <span class="text-[10px] text-muted uppercase">Output Result:</span>
                  <pre class="p-1 rounded bg-[var(--bg-canvas)] font-mono text-[10px] text-secondary mt-0.5 max-h-24 overflow-y-auto border border-[var(--border-subtle)]">{{ tool.output_result | json }}</pre>
                </div>
              </div>
              <div *ngIf="!selectedRun()!.tool_logs || selectedRun()!.tool_logs.length === 0" class="text-center py-6 text-muted text-xs">
                No tool calls recorded for this run.
              </div>
            </div>

            <!-- Final Response Preview -->
            <div class="mt-4 pt-3 border-t border-[var(--border-subtle)]" *ngIf="selectedRun()!.final_response">
              <span class="text-muted block text-[10px] uppercase font-semibold mb-1">Grounded Final Response:</span>
              <div class="p-2.5 rounded bg-[var(--bg-subtle)] text-secondary text-xs border border-[var(--border-subtle)] leading-relaxed">
                {{ selectedRun()!.final_response }}
              </div>
            </div>
          </div>

          <ng-template #noRunSelected>
            <div class="op-card text-center py-12 text-muted">
              <svg width="32" height="32" class="w-8 h-8 mx-auto mb-2 opacity-30 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 12 2 2 4-4"/>
              </svg>
              <div class="text-sm font-semibold text-secondary">Select an Agent Execution</div>
              <p class="text-xs text-muted mt-1">Click on any run on the left to replay its raw SSE event sequence and backend tool traces.</p>
            </div>
          </ng-template>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class ExecutionInspectorComponent implements OnInit {
  private readonly ops = inject(OpsService);

  readonly runs = signal<AgentRunSummary[]>([]);
  readonly activeFilter = signal<string>('all');
  readonly selectedRunId = signal<number | null>(null);
  readonly selectedRun = signal<any | null>(null);
  readonly events = signal<AgentEventItem[]>([]);
  readonly activeTab = signal<'events' | 'tools'>('events');

  ngOnInit(): void {
    this.loadRuns();
  }

  loadRuns(): void {
    this.ops.listAgentRuns(0, 50).subscribe({
      next: (res) => {
        this.runs.set(res);
        if (res.length > 0 && !this.selectedRunId()) {
          this.selectRun(res[0].id);
        }
      },
      error: (err) => console.error('Failed to load agent runs', err)
    });
  }

  filteredRuns(): AgentRunSummary[] {
    const f = this.activeFilter();
    if (f === 'all') return this.runs();
    return this.runs().filter(r => r.status.toLowerCase() === f);
  }

  selectRun(id: number): void {
    this.selectedRunId.set(id);
    this.ops.getAgentRunDetail(id).subscribe({
      next: (detail) => this.selectedRun.set(detail),
      error: (err) => console.error('Failed to get run detail', err)
    });

    this.ops.getAgentRunEvents(id).subscribe({
      next: (evts) => this.events.set(evts),
      error: (err) => {
        console.error('Failed to load execution events', err);
        this.events.set([]);
      }
    });
  }

  getStatusBadge(status: string): string {
    switch (status?.toLowerCase()) {
      case 'completed': return 'badge-success';
      case 'started':
      case 'investigating': return 'badge-brand';
      case 'failed': return 'badge-danger';
      case 'escalated': return 'badge-warning';
      default: return 'badge-neutral';
    }
  }

  getEventColor(eventType: string): string {
    if (eventType.startsWith('tool.failed') || eventType.startsWith('agent.failed')) return 'text-rose-400';
    if (eventType.startsWith('tool.completed') || eventType.startsWith('agent.completed')) return 'text-emerald-400';
    if (eventType.startsWith('approval')) return 'text-amber-400';
    if (eventType.startsWith('rag')) return 'text-purple-400';
    return 'text-[var(--brand-primary)]';
  }
}

