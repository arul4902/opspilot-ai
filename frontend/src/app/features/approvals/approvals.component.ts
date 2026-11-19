import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OpsService } from '../../core/services/ops.service';
import { ApprovalRequestItem } from '../../core/models';

@Component({
  selector: 'app-approvals',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold tracking-tight text-primary">Human Approval Queue</h1>
            <span class="badge badge-warning font-mono text-[10px]">HITL GOVERNANCE</span>
          </div>
          <p class="text-xs text-secondary mt-0.5">Operator verification for consequential business actions and financial operations</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadApprovals()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh Queue</span>
          </button>
        </div>
      </div>

      <!-- Filter Tabs Strip -->
      <div class="flex items-center gap-1 border-b border-[var(--border-default)] pb-2 text-xs">
        <button
          class="px-2.5 py-1 rounded-[var(--radius-sm)] transition font-medium"
          [class.bg-[var(--bg-elevated)]]="selectedTab() === 'all'"
          [class.text-primary]="selectedTab() === 'all'"
          [class.text-muted]="selectedTab() !== 'all'"
          (click)="setTab('all')"
        >
          All Requests ({{ approvals().length }})
        </button>
        <button
          class="px-2.5 py-1 rounded-[var(--radius-sm)] transition font-medium flex items-center gap-1.5"
          [class.bg-[var(--bg-elevated)]]="selectedTab() === 'pending'"
          [class.text-warning]="selectedTab() === 'pending'"
          [class.text-muted]="selectedTab() !== 'pending'"
          (click)="setTab('pending')"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-amber-400" *ngIf="pendingCount() > 0"></span>
          <span>Pending Review ({{ pendingCount() }})</span>
        </button>
        <button
          class="px-2.5 py-1 rounded-[var(--radius-sm)] transition font-medium"
          [class.bg-[var(--bg-elevated)]]="selectedTab() === 'approved'"
          [class.text-success]="selectedTab() === 'approved'"
          [class.text-muted]="selectedTab() !== 'approved'"
          (click)="setTab('approved')"
        >
          Approved
        </button>
        <button
          class="px-2.5 py-1 rounded-[var(--radius-sm)] transition font-medium"
          [class.bg-[var(--bg-elevated)]]="selectedTab() === 'rejected'"
          [class.text-danger]="selectedTab() === 'rejected'"
          [class.text-muted]="selectedTab() !== 'rejected'"
          (click)="setTab('rejected')"
        >
          Rejected
        </button>
      </div>

      <!-- Loading State -->
      <div *ngIf="isLoading()" class="py-12 text-center text-muted text-xs">
        Loading approval requests...
      </div>

      <!-- Approvals List Table -->
      <div *ngIf="!isLoading()" class="op-table-container">
        <table class="op-table">
          <thead>
            <tr>
              <th>Request ID</th>
              <th>Action Workflow</th>
              <th>Origin Agent</th>
              <th>Linked Order</th>
              <th>Financial Impact</th>
              <th>Timestamp</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngIf="filteredApprovals().length === 0">
              <td colspan="8" class="text-center py-8 text-muted">
                No approval requests found for this filter tab.
              </td>
            </tr>
            <tr *ngFor="let item of filteredApprovals()" class="hover:bg-[var(--bg-hover)] transition">
              <td class="font-mono text-secondary">#{{ item.id }}</td>
              <td>
                <span class="font-medium text-primary">{{ formatRequestType(item.request_type) }}</span>
              </td>
              <td class="font-mono text-muted text-[11px]">{{ item.requested_by_agent }}</td>
              <td>
                <span *ngIf="item.order_id" class="font-mono text-brand">ORD-{{ item.order_id }}</span>
                <span *ngIf="!item.order_id" class="text-muted text-xs">—</span>
              </td>
              <td class="font-mono text-primary">
                {{ item.payload['amount'] ? ('$' + (item.payload['amount'] | number:'1.2-2')) : 'N/A' }}
              </td>
              <td class="font-mono text-muted text-[11px]">
                {{ item.created_at | date:'yyyy-MM-dd HH:mm' }}
              </td>
              <td>
                <span class="badge" [ngClass]="getStatusBadgeClass(item.status)">
                  {{ item.status | uppercase }}
                </span>
              </td>
              <td class="text-right">
                <button
                  *ngIf="item.status === 'pending'"
                  class="btn btn-primary btn-xs"
                  (click)="openModal(item)"
                >
                  Review Request
                </button>
                <button
                  *ngIf="item.status !== 'pending'"
                  class="btn btn-secondary btn-xs"
                  (click)="openModal(item)"
                >
                  View Details
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Review & Decision Modal -->
      <div *ngIf="activeItem" class="modal-overlay" (click)="closeModal()">
        <div class="modal-card p-5 space-y-4" (click)="$event.stopPropagation()">
          <div class="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
            <div>
              <h3 class="text-sm font-semibold text-primary">Review Consequential Action</h3>
              <p class="text-xs text-muted font-mono">Request #{{ activeItem.id }} • {{ activeItem.request_type }}</p>
            </div>
            <button class="text-muted hover:text-primary" (click)="closeModal()">&times;</button>
          </div>

          <!-- Payload Context -->
          <div class="space-y-2 text-xs">
            <div class="p-3 rounded bg-[var(--bg-canvas)] border border-[var(--border-default)] font-mono space-y-1">
              <div class="flex justify-between"><span class="text-muted">Target Order:</span> <span class="text-primary">ORD-{{ activeItem.order_id }}</span></div>
              <div class="flex justify-between" *ngIf="activeItem.payload['amount']"><span class="text-muted">Requested Amount:</span> <span class="text-brand font-bold">\${{ activeItem.payload['amount'] | number:'1.2-2' }}</span></div>
              <div class="flex justify-between"><span class="text-muted">Staged By Agent:</span> <span class="text-secondary">{{ activeItem.requested_by_agent }}</span></div>
              <div class="pt-1 border-t border-[var(--border-subtle)] text-[11px] text-secondary">
                <span class="text-muted">Reason / Context:</span> {{ activeItem.payload['reason'] || 'No explicit justification payload' }}
              </div>
            </div>

            <!-- Operator Justification Input (for pending requests) -->
            <div *ngIf="activeItem.status === 'pending'">
              <label class="op-label">Operator Review Justification <span class="text-danger">*</span></label>
              <textarea
                [(ngModel)]="operatorComments"
                rows="3"
                class="op-input text-xs resize-none"
                placeholder="Enter mandatory justification notes for audit compliance..."
              ></textarea>
            </div>

            <!-- Read-only inspection for already approved/rejected items -->
            <div *ngIf="activeItem.status !== 'pending'" class="p-2.5 rounded bg-[var(--bg-canvas)] border border-[var(--border-subtle)] text-xs space-y-1">
              <div class="text-muted text-[11px]">Reviewed by: {{ activeItem.reviewed_by_name || 'Admin Operator' }} at {{ activeItem.reviewed_at }}</div>
              <div class="text-secondary">Comments: "{{ activeItem.comments || 'No comments recorded' }}"</div>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border-subtle)]">
            <button class="btn btn-secondary btn-xs" (click)="closeModal()">
              Cancel
            </button>
            <ng-container *ngIf="activeItem.status === 'pending'">
              <button 
                class="btn btn-danger btn-xs"
                [disabled]="isSubmitting"
                (click)="rejectRequest()"
              >
                Reject Action
              </button>
              <button 
                class="btn btn-primary btn-xs bg-emerald-600 hover:bg-emerald-500 border-none"
                [disabled]="isSubmitting"
                (click)="approveRequest()"
              >
                Authorize Action
              </button>
            </ng-container>
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
export class ApprovalsComponent implements OnInit {
  private readonly opsService = inject(OpsService);

  readonly approvals = signal<ApprovalRequestItem[]>([]);
  readonly selectedTab = signal<'all' | 'pending' | 'approved' | 'rejected'>('pending');
  readonly isLoading = signal(false);

  activeItem: ApprovalRequestItem | null = null;
  operatorComments = 'Verified order details and customer eligibility.';
  isSubmitting = false;

  ngOnInit(): void {
    this.loadApprovals();
  }

  loadApprovals(): void {
    this.isLoading.set(true);
    this.opsService.listApprovals().subscribe({
      next: (res) => {
        this.approvals.set(res);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load approvals', err);
        this.isLoading.set(false);
      }
    });
  }

  setTab(tab: 'all' | 'pending' | 'approved' | 'rejected'): void {
    this.selectedTab.set(tab);
  }

  pendingCount(): number {
    return this.approvals().filter(a => a.status === 'pending').length;
  }

  filteredApprovals(): ApprovalRequestItem[] {
    const tab = this.selectedTab();
    if (tab === 'all') return this.approvals();
    return this.approvals().filter(a => a.status === tab);
  }

  formatRequestType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'pending': return 'badge-warning';
      case 'approved': return 'badge-success';
      case 'rejected': return 'badge-danger';
      default: return 'badge-neutral';
    }
  }

  openModal(item: ApprovalRequestItem): void {
    this.activeItem = item;
    this.operatorComments = 'Verified order details and customer eligibility.';
  }

  closeModal(): void {
    this.activeItem = null;
    this.operatorComments = '';
  }

  approveRequest(): void {
    if (!this.activeItem) return;
    this.isSubmitting = true;

    this.opsService.approveRequest(this.activeItem.id, this.operatorComments).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.closeModal();
        this.loadApprovals();
      },
      error: (err) => {
        console.error('Approval failed', err);
        this.isSubmitting = false;
      }
    });
  }

  rejectRequest(): void {
    if (!this.activeItem) return;
    this.isSubmitting = true;

    this.opsService.rejectRequest(this.activeItem.id, this.operatorComments).subscribe({
      next: () => {
        this.isSubmitting = false;
        this.closeModal();
        this.loadApprovals();
      },
      error: (err) => {
        console.error('Rejection failed', err);
        this.isSubmitting = false;
      }
    });
  }
}
