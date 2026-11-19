import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OpsService } from '../../core/services/ops.service';
import { AuditLogItem } from '../../core/models';

@Component({
  selector: 'app-audit-logs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold tracking-tight text-primary">Immutable Audit Trail</h1>
            <span class="badge badge-brand font-mono text-[10px]">APPEND ONLY</span>
          </div>
          <p class="text-xs text-secondary mt-0.5">Cryptographically traceable ledger recording all autonomous agent actions and human operator decisions</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadLogs()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh Ledger</span>
          </button>
        </div>
      </div>

      <!-- Filters & Search Bar -->
      <div class="op-card p-3 flex flex-col sm:flex-row justify-between items-center gap-3">
        <div class="flex flex-wrap items-center gap-2 w-full sm:w-auto flex-1">
          <input 
            type="text" 
            [(ngModel)]="searchTerm" 
            placeholder="Search by action, email, or entity ID..." 
            class="op-input text-xs w-full sm:w-72"
          />
          <select [(ngModel)]="selectedAction" (change)="onFilterChange()" class="op-input text-xs w-auto">
            <option value="">All Action Types</option>
            <option value="APPROVAL_REQUEST_APPROVED">APPROVAL_REQUEST_APPROVED</option>
            <option value="APPROVAL_REQUEST_REJECTED">APPROVAL_REQUEST_REJECTED</option>
            <option value="REFUND_INITIATED_PENDING_APPROVAL">REFUND_INITIATED_PENDING_APPROVAL</option>
            <option value="RETURN_REQUEST_CREATED">RETURN_REQUEST_CREATED</option>
            <option value="ESCALATION_UPDATED">ESCALATION_UPDATED</option>
            <option value="AGENT_RUN_COMPLETED">AGENT_RUN_COMPLETED</option>
          </select>
        </div>
        <div class="text-xs text-muted font-mono whitespace-nowrap">
          {{ filteredLogs.length }} Events Recorded
        </div>
      </div>

      <!-- Audit Table -->
      <div class="op-table-container">
        <table class="op-table">
          <thead>
            <tr>
              <th>Timestamp (UTC)</th>
              <th>Action Event</th>
              <th>Target Entity</th>
              <th>Actor / Origin</th>
              <th class="text-right">Payload</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngIf="loading">
              <td colspan="5" class="py-8 text-center text-muted text-xs">Loading audit ledger...</td>
            </tr>
            <tr *ngIf="!loading && filteredLogs.length === 0">
              <td colspan="5" class="py-8 text-center text-muted text-xs">No audit events match current criteria.</td>
            </tr>
            <tr *ngFor="let item of filteredLogs" class="hover:bg-[var(--bg-hover)] transition">
              <td class="font-mono text-muted text-[11px] whitespace-nowrap">
                {{ item.timestamp | date:'yyyy-MM-dd HH:mm:ss' }}
              </td>
              <td>
                <span class="badge text-[10px] font-mono" [ngClass]="getActionBadgeClass(item.action)">
                  {{ item.action }}
                </span>
              </td>
              <td>
                <span class="font-medium text-primary text-xs">{{ item.entity_type }}</span>
                <span *ngIf="item.entity_id" class="text-muted font-mono text-[11px] ml-1">#{{ item.entity_id }}</span>
              </td>
              <td>
                <div class="text-xs text-primary">{{ item.user_email || 'Autonomous Agent Pipeline' }}</div>
                <div class="text-[10px] text-muted font-mono">{{ item.ip_address || 'internal' }}</div>
              </td>
              <td class="text-right">
                <button (click)="inspectPayload(item)" class="btn btn-ghost btn-xs text-brand hover:underline font-mono">
                  Inspect JSON
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- JSON Inspection Drawer / Modal -->
      <div *ngIf="selectedItem" class="modal-overlay" (click)="selectedItem = null">
        <div class="modal-card p-5 max-w-2xl space-y-4" (click)="$event.stopPropagation()">
          <div class="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
            <div>
              <h3 class="text-sm font-semibold text-primary font-mono">Audit Event #{{ selectedItem.id }}</h3>
              <p class="text-xs text-muted font-mono mt-0.5">{{ selectedItem.action }}</p>
            </div>
            <button class="text-muted hover:text-primary" (click)="selectedItem = null">&times;</button>
          </div>

          <div class="space-y-3 font-mono text-xs">
            <div class="grid grid-cols-2 gap-2 text-muted bg-[var(--bg-canvas)] p-3 rounded border border-[var(--border-default)]">
              <div><span class="text-primary font-semibold">Entity:</span> {{ selectedItem.entity_type }} #{{ selectedItem.entity_id }}</div>
              <div><span class="text-primary font-semibold">Actor:</span> {{ selectedItem.user_email || 'Autonomous System' }}</div>
              <div><span class="text-primary font-semibold">Origin IP:</span> {{ selectedItem.ip_address || '127.0.0.1' }}</div>
              <div><span class="text-primary font-semibold">Timestamp:</span> {{ selectedItem.timestamp }}</div>
            </div>

            <div>
              <div class="tech-label mb-1">State Mutation Payload</div>
              <pre class="bg-[var(--bg-canvas)] p-3 rounded border border-[var(--border-default)] text-emerald-400 overflow-x-auto text-[11px] leading-relaxed max-h-64">{{ selectedItem.details | json }}</pre>
            </div>
          </div>

          <div class="flex justify-end pt-3 border-t border-[var(--border-subtle)]">
            <button (click)="selectedItem = null" class="btn btn-secondary btn-xs">
              Close
            </button>
          </div>
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
export class AuditLogsComponent implements OnInit {
  private readonly opsService = inject(OpsService);

  logs: AuditLogItem[] = [];
  loading = false;
  selectedAction = '';
  searchTerm = '';
  selectedItem: AuditLogItem | null = null;

  ngOnInit(): void {
    this.loadLogs();
  }

  loadLogs(): void {
    this.loading = true;
    this.opsService.listAuditLogs(0, 100, this.selectedAction || undefined).subscribe({
      next: (data) => {
        this.logs = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load audit logs', err);
        this.loading = false;
      }
    });
  }

  onFilterChange(): void {
    this.loadLogs();
  }

  get filteredLogs(): AuditLogItem[] {
    if (!this.searchTerm.trim()) return this.logs;
    const term = this.searchTerm.toLowerCase();
    return this.logs.filter(item => 
      item.action.toLowerCase().includes(term) ||
      (item.entity_type && item.entity_type.toLowerCase().includes(term)) ||
      (item.entity_id && item.entity_id.toLowerCase().includes(term)) ||
      (item.user_email && item.user_email.toLowerCase().includes(term))
    );
  }

  getActionBadgeClass(action: string): string {
    if (action.includes('APPROVED')) return 'badge-success';
    if (action.includes('REJECTED')) return 'badge-danger';
    if (action.includes('PENDING') || action.includes('INITIATED')) return 'badge-warning';
    if (action.includes('ESCALAT')) return 'badge-purple';
    return 'badge-brand';
  }

  inspectPayload(item: AuditLogItem): void {
    this.selectedItem = item;
  }
}
