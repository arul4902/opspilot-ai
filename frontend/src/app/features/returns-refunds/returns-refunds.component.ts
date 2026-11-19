import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OpsService } from '../../core/services/ops.service';
import { ReturnRequest, RefundRequest } from '../../core/models';

@Component({
  selector: 'app-returns-refunds',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-primary">Returns & Refunds Ledger</h1>
          <p class="text-xs text-secondary mt-0.5">Physical return authorizations and simulated financial refund disbursements</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadData()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <!-- Tab Switcher -->
      <div class="flex items-center gap-1 border-b border-[var(--border-default)] pb-2 text-xs">
        <button
          class="px-2.5 py-1 rounded-[var(--radius-sm)] transition font-medium"
          [class.bg-[var(--bg-elevated)]]="activeTab() === 'refunds'"
          [class.text-primary]="activeTab() === 'refunds'"
          [class.text-muted]="activeTab() !== 'refunds'"
          (click)="activeTab.set('refunds')"
        >
          Refund Requests ({{ refunds().length }})
        </button>
        <button
          class="px-2.5 py-1 rounded-[var(--radius-sm)] transition font-medium"
          [class.bg-[var(--bg-elevated)]]="activeTab() === 'returns'"
          [class.text-primary]="activeTab() === 'returns'"
          [class.text-muted]="activeTab() !== 'returns'"
          (click)="activeTab.set('returns')"
        >
          Physical Returns ({{ returns().length }})
        </button>
      </div>

      <!-- Refunds Table -->
      <div class="op-table-container" *ngIf="activeTab() === 'refunds'">
        <table class="op-table">
          <thead>
            <tr>
              <th>Refund Number</th>
              <th>Order Number</th>
              <th>Customer</th>
              <th>Refund Amount</th>
              <th>Justification</th>
              <th>Mode</th>
              <th>Status</th>
              <th>Approval Timestamp</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let ref of refunds()" class="hover:bg-[var(--bg-hover)] transition">
              <td class="font-mono font-semibold text-brand">{{ ref.refund_number }}</td>
              <td class="font-mono text-secondary text-xs">{{ ref.order_number }}</td>
              <td class="text-secondary">{{ ref.customer_name || 'Customer #' + ref.customer_id }}</td>
              <td class="font-mono font-medium text-primary">\${{ ref.amount | number:'1.2-2' }}</td>
              <td class="text-xs text-muted max-w-xs truncate" [title]="ref.reason">{{ ref.reason }}</td>
              <td>
                <span class="badge badge-purple text-[10px]" *ngIf="ref.is_simulated">SIMULATION</span>
              </td>
              <td>
                <span class="badge" [ngClass]="getRefundBadge(ref.status)">
                  {{ ref.status | uppercase }}
                </span>
              </td>
              <td class="font-mono text-muted text-[11px]">{{ ref.approved_at ? (ref.approved_at | date:'yyyy-MM-dd HH:mm') : 'Pending Review' }}</td>
            </tr>
            <tr *ngIf="refunds().length === 0">
              <td colspan="8" class="p-8 text-center text-muted text-xs">No refund requests recorded.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Returns Table -->
      <div class="op-table-container" *ngIf="activeTab() === 'returns'">
        <table class="op-table">
          <thead>
            <tr>
              <th>Return Number</th>
              <th>Order Number</th>
              <th>Customer</th>
              <th>Return Reason</th>
              <th>Requested At</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let ret of returns()" class="hover:bg-[var(--bg-hover)] transition">
              <td class="font-mono font-semibold text-brand">{{ ret.request_number }}</td>
              <td class="font-mono text-secondary text-xs">{{ ret.order_number }}</td>
              <td class="text-secondary">{{ ret.customer_name || 'Customer #' + ret.customer_id }}</td>
              <td class="text-xs text-secondary max-w-xs truncate" [title]="ret.reason">{{ ret.reason }}</td>
              <td class="font-mono text-muted text-[11px]">{{ ret.requested_at | date:'yyyy-MM-dd HH:mm' }}</td>
              <td>
                <span class="badge" [ngClass]="getReturnBadge(ret.status)">
                  {{ ret.status | uppercase }}
                </span>
              </td>
            </tr>
            <tr *ngIf="returns().length === 0">
              <td colspan="6" class="p-8 text-center text-muted text-xs">No return requests recorded.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class ReturnsRefundsComponent implements OnInit {
  private readonly ops = inject(OpsService);
  readonly activeTab = signal<'refunds' | 'returns'>('refunds');
  readonly refunds = signal<RefundRequest[]>([]);
  readonly returns = signal<ReturnRequest[]>([]);

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.ops.listRefunds().subscribe({
      next: (res) => this.refunds.set(res),
      error: (err) => console.error('Failed to load refunds', err)
    });

    this.ops.listReturns().subscribe({
      next: (res) => this.returns.set(res),
      error: (err) => console.error('Failed to load returns', err)
    });
  }

  getRefundBadge(status: string): string {
    switch (status.toLowerCase()) {
      case 'approved': return 'badge-success';
      case 'pending_approval': return 'badge-warning';
      case 'rejected': return 'badge-danger';
      case 'processed': return 'badge-brand';
      default: return 'badge-neutral';
    }
  }

  getReturnBadge(status: string): string {
    switch (status.toLowerCase()) {
      case 'approved': return 'badge-success';
      case 'requested': return 'badge-warning';
      case 'rejected': return 'badge-danger';
      case 'completed': return 'badge-brand';
      default: return 'badge-neutral';
    }
  }
}
