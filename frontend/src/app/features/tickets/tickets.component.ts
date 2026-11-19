import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { OpsService } from '../../core/services/ops.service';
import { SupportTicket } from '../../core/models';

@Component({
  selector: 'app-tickets',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-primary">Support Tickets Ledger</h1>
          <p class="text-xs text-secondary mt-0.5">Automated ticket dispatches, customer inquiries, and escalation tracking</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadTickets()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <!-- Tickets Table -->
      <div class="op-table-container">
        <table class="op-table">
          <thead>
            <tr>
              <th>Ticket ID</th>
              <th>Customer</th>
              <th>Linked Order</th>
              <th>Subject & Issue Narrative</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Created Date</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let t of tickets()" class="hover:bg-[var(--bg-hover)] transition">
              <td class="font-mono font-semibold text-brand">{{ t.ticket_number }}</td>
              <td class="text-secondary">{{ t.customer_name || 'Customer #' + t.customer_id }}</td>
              <td class="font-mono text-muted text-xs">{{ t.order_number || '—' }}</td>
              <td>
                <div class="font-medium text-primary text-xs">{{ t.subject }}</div>
                <div class="text-muted text-[11px] truncate max-w-sm mt-0.5" [title]="t.description">{{ t.description }}</div>
              </td>
              <td>
                <span class="badge" [ngClass]="getPriorityBadge(t.priority)">
                  {{ t.priority | uppercase }}
                </span>
              </td>
              <td>
                <span class="badge" [ngClass]="getTicketStatusBadge(t.status)">
                  {{ t.status | uppercase }}
                </span>
              </td>
              <td class="font-mono text-muted text-[11px]">{{ t.created_at | date:'yyyy-MM-dd HH:mm' }}</td>
            </tr>
            <tr *ngIf="tickets().length === 0">
              <td colspan="7" class="p-8 text-center text-muted text-xs">No support tickets recorded.</td>
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
export class TicketsComponent implements OnInit {
  private readonly ops = inject(OpsService);
  readonly tickets = signal<SupportTicket[]>([]);

  ngOnInit(): void {
    this.loadTickets();
  }

  loadTickets(): void {
    this.ops.listTickets().subscribe({
      next: (res) => this.tickets.set(res),
      error: (err) => console.error('Failed to load tickets', err)
    });
  }

  getPriorityBadge(priority: string): string {
    switch (priority.toLowerCase()) {
      case 'urgent': return 'badge-danger';
      case 'high': return 'badge-warning';
      case 'medium': return 'badge-brand';
      case 'low': return 'badge-neutral';
      default: return 'badge-neutral';
    }
  }

  getTicketStatusBadge(status: string): string {
    switch (status.toLowerCase()) {
      case 'resolved': return 'badge-success';
      case 'open': return 'badge-warning';
      case 'in_progress': return 'badge-brand';
      case 'closed': return 'badge-neutral';
      default: return 'badge-neutral';
    }
  }
}
