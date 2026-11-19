import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { OpsService } from '../../core/services/ops.service';
import { AnalyticsOverview, DailyTrendPoint } from '../../core/models';

@Component({
  selector: 'app-overview',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="p-4 sm:p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-primary">Operations Overview</h1>
          <p class="text-xs text-secondary mt-0.5">Real-time fulfillment telemetry, autonomous agent activity, and exception monitoring</p>
        </div>
        <div class="flex items-center gap-2">
          <div class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono hidden sm:flex" [ngClass]="sseConnected() ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'">
            <span class="w-1.5 h-1.5 rounded-full" [class.animate-pulse]="sseConnected()" [ngClass]="sseConnected() ? 'bg-emerald-400' : 'bg-amber-400'"></span>
            <span>{{ sseConnected() ? 'Live SSE Connected' : 'Polling Fallback' }}</span>
          </div>
          <span class="text-xs text-muted font-mono hidden md:inline">Last Sync: {{ lastSyncTime }}</span>
          <button class="btn btn-secondary btn-xs" (click)="loadAnalytics()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" [class.animate-spin]="isLoading()" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/>
            </svg>
            <span>Refresh</span>
          </button>
          <a routerLink="/agent" class="btn btn-primary btn-xs">
            <svg width="14" height="14" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>
            </svg>
            <span>Launch Agent Workspace</span>
          </a>
        </div>
      </div>

      <!-- Loading State Skeleton -->
      <div *ngIf="isLoading()" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div class="op-card skeleton h-24" *ngFor="let i of [1,2,3,4]"></div>
      </div>

      <ng-container *ngIf="overview() as data">
        <!-- Metric Cells Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <!-- Total GMV -->
          <div class="op-metric-card">
            <div class="flex items-center justify-between">
              <span class="metric-label">Gross Merchandise Value</span>
              <span class="badge badge-neutral font-mono text-[10px]">{{ data.total_orders }} orders</span>
            </div>
            <div class="metric-val font-mono">\${{ data.total_revenue | number:'1.2-2' }}</div>
            <div class="metric-sub">
              <span class="text-muted">Avg Order Value:</span>
              <span class="font-mono text-secondary">\${{ (data.total_revenue / (data.total_orders || 1)) | number:'1.2-2' }}</span>
            </div>
          </div>

          <!-- Delayed Shipments -->
          <div class="op-metric-card">
            <div class="flex items-center justify-between">
              <span class="metric-label">Courier Exceptions</span>
              <span class="badge" [ngClass]="data.delayed_shipments_count > 0 ? 'badge-warning' : 'badge-success'">
                {{ data.delayed_shipments_count > 0 ? 'SLA Alert' : 'Normal' }}
              </span>
            </div>
            <div class="metric-val font-mono" [class.text-warning]="data.delayed_shipments_count > 0">
              {{ data.delayed_shipments_count }}
            </div>
            <div class="metric-sub">
              <a routerLink="/shipments" class="metric-link text-warning flex items-center gap-1">
                <span>Inspect delayed tracking telemetry</span>
                <svg width="12" height="12" class="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
              </a>
            </div>
          </div>

          <!-- Payment Discrepancies -->
          <div class="op-metric-card">
            <div class="flex items-center justify-between">
              <span class="metric-label">Payment Discrepancies</span>
              <span class="badge" [ngClass]="data.orphan_payments_count > 0 ? 'badge-danger' : 'badge-neutral'">
                {{ data.orphan_payments_count }} Orphans
              </span>
            </div>
            <div class="metric-val font-mono" [class.text-danger]="data.orphan_payments_count > 0">
              {{ data.orphan_payments_count }}
            </div>
            <div class="metric-sub">
              <a routerLink="/payments" class="metric-link text-danger flex items-center gap-1">
                <span>{{ data.failed_payments_count }} declined transactions</span>
                <svg width="12" height="12" class="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
              </a>
            </div>
          </div>

          <!-- HITL Approval Queue -->
          <div class="op-metric-card">
            <div class="flex items-center justify-between">
              <span class="metric-label">Human Approvals Required</span>
              <span class="badge" [ngClass]="data.pending_approvals_count > 0 ? 'badge-brand' : 'badge-neutral'">
                {{ data.pending_approvals_count }} Pending
              </span>
            </div>
            <div class="metric-val font-mono text-brand">
              {{ data.pending_approvals_count }}
            </div>
            <div class="metric-sub">
              <a routerLink="/approvals" class="metric-link text-brand flex items-center gap-1">
                <span>Review financial action requests</span>
                <svg width="12" height="12" class="w-3 h-3 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
              </a>
            </div>
          </div>
        </div>

        <!-- Section: Autonomous Engine SLAs & Order Lifecycle Breakdown -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <!-- Autonomous Engine SLA Panel -->
          <div class="op-card lg:col-span-5 flex flex-col justify-between">
            <div>
              <div class="panel-header">
                <div class="panel-title">
                  <svg width="16" height="16" class="w-4 h-4 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 12 2 2 4-4"/>
                  </svg>
                  <span>Autonomous Engine Performance</span>
                </div>
                <span class="badge badge-brand font-mono text-[10px]">12-STEP PIPELINE</span>
              </div>

              <div class="space-y-2.5">
                <div class="flex justify-between items-center py-1.5 border-b border-[var(--border-subtle)] text-xs">
                  <span class="text-secondary">Investigations Executed:</span>
                  <span class="font-mono font-semibold text-primary">{{ data.agent_runs_total }}</span>
                </div>
                <div class="flex justify-between items-center py-1.5 border-b border-[var(--border-subtle)] text-xs">
                  <span class="text-secondary">Mean Resolution Latency:</span>
                  <span class="font-mono font-semibold text-brand">{{ data.agent_avg_duration_ms }} ms</span>
                </div>
                <div class="flex justify-between items-center py-1.5 border-b border-[var(--border-subtle)] text-xs">
                  <span class="text-secondary">Autonomous Success Rate:</span>
                  <span class="font-mono font-semibold text-success">{{ data.agent_success_rate_percent }}%</span>
                </div>
                <div class="flex justify-between items-center py-1.5 border-b border-[var(--border-subtle)] text-xs">
                  <span class="text-secondary">Open Customer Tickets:</span>
                  <span class="font-mono font-semibold text-warning">{{ data.open_tickets_count }}</span>
                </div>
                <div class="flex justify-between items-center py-1.5 border-b border-[var(--border-subtle)] text-xs">
                  <span class="text-secondary">Pending Escalations:</span>
                  <span class="font-mono font-semibold" [class.text-danger]="data.pending_escalations_count > 0">{{ data.pending_escalations_count }}</span>
                </div>
              </div>
            </div>

            <div class="mt-4 pt-3 border-t border-[var(--border-subtle)]">
              <a routerLink="/agent" class="btn btn-secondary w-full text-xs justify-center flex items-center gap-1.5">
                <span>Run Interactive Investigation</span>
                <svg width="12" height="12" class="w-3 h-3 text-muted flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>
              </a>
            </div>
          </div>

          <!-- Order Lifecycle Breakdown -->
          <div class="op-card lg:col-span-7">
            <div class="panel-header">
              <div class="panel-title">
                <svg width="16" height="16" class="w-4 h-4 text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>
                </svg>
                <span>Order Fulfillment Distribution</span>
              </div>
              <span class="text-xs text-muted font-mono">{{ data.total_orders }} Total Records</span>
            </div>

            <!-- Stacked Distribution Bar -->
            <div class="w-full h-2.5 bg-[var(--bg-subtle)] rounded-[var(--radius-xs)] overflow-hidden flex mb-4 border border-[var(--border-subtle)]">
              <div 
                *ngFor="let item of statusEntries(data.orders_by_status)"
                [style.width.%]="(item.value / (data.total_orders || 1)) * 100"
                [ngClass]="getStatusBarClass(item.key)"
                [title]="item.key + ': ' + item.value"
              ></div>
            </div>

            <!-- Status Breakdown Rows -->
            <div class="divide-y divide-[var(--border-subtle)]">
              <div *ngFor="let item of statusEntries(data.orders_by_status)" class="py-2 flex items-center justify-between text-xs">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full flex-shrink-0" [ngClass]="getStatusDotClass(item.key)"></span>
                  <span class="font-medium text-secondary capitalize">{{ item.key }}</span>
                </div>
                <div class="flex items-center gap-3">
                  <span class="font-mono text-primary">{{ item.value }}</span>
                  <span class="font-mono text-muted text-[11px] w-12 text-right">
                    {{ ((item.value / (data.total_orders || 1)) * 100) | number:'1.0-0' }}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Section: 14-Day Velocity Trend Chart -->
        <div class="op-card" *ngIf="trends().length > 0">
          <div class="panel-header">
            <div class="panel-title">
              <svg width="16" height="16" class="w-4 h-4 text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect width="18" height="18" x="3" y="3" rx="2"/><line x1="3" x2="21" y1="9" y2="9"/><line x1="9" x2="9" y1="21" y2="9"/>
              </svg>
              <span>14-Day Operations Inbound Velocity</span>
            </div>
            <div class="flex items-center gap-3 text-xs text-muted">
              <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--brand-primary)]"></span> Orders Created</span>
              <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--color-warning)]"></span> Support Inquiries</span>
            </div>
          </div>

          <!-- Responsive Trend Bar Chart -->
          <div class="overflow-x-auto pt-2">
            <div class="flex items-end justify-between gap-1 sm:gap-2 h-36 min-w-[500px]">
              <div *ngFor="let point of trends()" class="flex-1 flex flex-col items-center gap-1 h-full justify-end group">
                <div class="flex items-end gap-0.5 sm:gap-1 w-full justify-center h-28">
                  <!-- Order Bar -->
                  <div 
                    class="w-2.5 sm:w-3.5 bg-[var(--brand-primary)] rounded-t-[var(--radius-xs)] transition-all group-hover:brightness-110" 
                    [style.height.px]="Math.max(4, point.orders_count * 18)"
                    [title]="point.date + ': ' + point.orders_count + ' orders'"
                  ></div>
                  <!-- Ticket Bar -->
                  <div 
                    class="w-2.5 sm:w-3.5 bg-[var(--color-warning)] rounded-t-[var(--radius-xs)] transition-all group-hover:brightness-110" 
                    [style.height.px]="Math.max(4, point.tickets_count * 22)"
                    [title]="point.date + ': ' + point.tickets_count + ' tickets'"
                  ></div>
                </div>
                <span class="text-[10px] font-mono text-muted group-hover:text-secondary">{{ point.date.substring(5) }}</span>
              </div>
            </div>
          </div>
        </div>
      </ng-container>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class OverviewComponent implements OnInit, OnDestroy {
  private readonly opsService = inject(OpsService);
  private sseSub?: Subscription;
  private intervalTimer: any;

  readonly overview = signal<AnalyticsOverview | null>(null);
  readonly trends = signal<DailyTrendPoint[]>([]);
  readonly isLoading = signal(false);
  readonly sseConnected = signal(true);
  readonly Math = Math;

  get lastSyncTime(): string {
    return new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' UTC';
  }

  ngOnInit(): void {
    this.loadAnalytics();

    // Subscribe to live Server-Sent Events (SSE) feed
    this.sseSub = this.opsService.listenToDashboardEvents().subscribe({
      next: (evt) => {
        console.log('[Dashboard SSE]', evt.event, evt.data);
        this.sseConnected.set(true);
        // Refresh analytics when operational entities mutate
        if (['order.created', 'order.updated', 'approval.created', 'approval.reviewed', 'agent.run_completed'].includes(evt.event)) {
          this.loadAnalytics(false);
        }
      },
      error: (err) => {
        console.warn('Dashboard SSE stream error; relying on polling fallback', err);
        this.sseConnected.set(false);
      }
    });

    // Periodic 30s background sync fallback
    this.intervalTimer = setInterval(() => {
      this.loadAnalytics(false);
    }, 30000);
  }

  ngOnDestroy(): void {
    if (this.sseSub) this.sseSub.unsubscribe();
    if (this.intervalTimer) clearInterval(this.intervalTimer);
  }

  loadAnalytics(showSpinner = true): void {
    if (showSpinner) this.isLoading.set(true);
    this.opsService.getAnalyticsOverview().subscribe({
      next: (res: AnalyticsOverview) => {
        this.overview.set(res);
        if (showSpinner) this.isLoading.set(false);
      },
      error: (err: any) => {
        console.error('Failed to load overview analytics', err);
        if (showSpinner) this.isLoading.set(false);
      }
    });

    this.opsService.getAnalyticsTrends(14).subscribe({
      next: (res: DailyTrendPoint[]) => this.trends.set(res),
      error: (err: any) => console.error('Failed to load trends', err)
    });
  }

  statusEntries(record?: Record<string, number>): Array<{ key: string; value: number }> {
    if (!record) return [];
    return Object.entries(record).map(([key, value]) => ({ key, value }));
  }

  getStatusBarClass(status: string): string {
    switch (status.toLowerCase()) {
      case 'delivered': return 'bg-emerald-500';
      case 'shipped': return 'bg-blue-500';
      case 'processing': return 'bg-cyan-500';
      case 'confirmed': return 'bg-indigo-500';
      case 'pending': return 'bg-amber-500';
      case 'cancelled': return 'bg-rose-500';
      default: return 'bg-slate-500';
    }
  }

  getStatusDotClass(status: string): string {
    switch (status.toLowerCase()) {
      case 'delivered': return 'bg-emerald-400';
      case 'shipped': return 'bg-blue-400';
      case 'processing': return 'bg-cyan-400';
      case 'confirmed': return 'bg-indigo-400';
      case 'pending': return 'bg-amber-400';
      case 'cancelled': return 'bg-rose-400';
      default: return 'bg-slate-400';
    }
  }
}
