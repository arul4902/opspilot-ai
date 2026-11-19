import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OpsService } from '../../core/services/ops.service';
import { Payment } from '../../core/models';

@Component({
  selector: 'app-payments',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-primary">Payment Transactions</h1>
          <p class="text-xs text-secondary mt-0.5">Payment gateway captures, bank authorizations, and orphan charge monitoring</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadPayments()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <!-- Orphan Alert Banner if orphan exists -->
      <div class="p-3 rounded bg-rose-500/10 border border-rose-500/30 flex items-start gap-3" *ngIf="hasOrphan()">
        <svg width="20" height="20" class="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        <div>
          <div class="font-semibold text-rose-300 text-xs">Orphan Payment Discrepancy Detected (Checkout Session Drop-off)</div>
          <div class="text-xs text-secondary mt-0.5">
            Transaction <span class="font-mono text-primary font-medium">TXN-2024-998811</span> was captured successfully, but no corresponding order was created in the database.
          </div>
        </div>
      </div>

      <!-- Payments Table -->
      <div class="op-table-container">
        <table class="op-table">
          <thead>
            <tr>
              <th>Reference ID</th>
              <th>Linked Order</th>
              <th>Customer</th>
              <th>Amount</th>
              <th>Payment Rail</th>
              <th>Timestamp</th>
              <th>Status</th>
              <th>Gateway Response</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let p of payments()" [class.bg-rose-500/5]="p.is_orphan">
              <td class="font-mono font-semibold text-brand">{{ p.transaction_reference }}</td>
              <td class="font-mono text-xs">
                <span *ngIf="p.order_number" class="text-primary">{{ p.order_number }}</span>
                <span *ngIf="!p.order_number" class="badge badge-danger text-[10px]">ORPHAN (NONE)</span>
              </td>
              <td class="text-secondary">{{ p.customer_name || 'Customer #' + p.customer_id }}</td>
              <td class="font-mono text-primary font-medium">\${{ p.amount | number:'1.2-2' }}</td>
              <td class="text-xs text-muted font-mono uppercase">{{ p.payment_method }}</td>
              <td class="font-mono text-muted text-[11px]">{{ p.transaction_date | date:'yyyy-MM-dd HH:mm' }}</td>
              <td>
                <span class="badge" [ngClass]="getPaymentBadge(p.status)">
                  {{ p.status | uppercase }}
                </span>
              </td>
              <td class="font-mono text-muted text-[11px]">{{ p.gateway_response || 'CAPTURED' }}</td>
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
export class PaymentsComponent implements OnInit {
  private readonly ops = inject(OpsService);
  readonly payments = signal<Payment[]>([]);

  ngOnInit(): void {
    this.loadPayments();
  }

  loadPayments(): void {
    this.ops.listPayments().subscribe({
      next: (res) => this.payments.set(res),
      error: (err) => console.error('Failed to load payments', err)
    });
  }

  hasOrphan(): boolean {
    return this.payments().some(p => p.is_orphan);
  }

  getPaymentBadge(status: string): string {
    switch (status.toLowerCase()) {
      case 'successful': return 'badge-success';
      case 'pending': return 'badge-warning';
      case 'failed': return 'badge-danger';
      case 'refunded': return 'badge-neutral';
      default: return 'badge-neutral';
    }
  }
}
