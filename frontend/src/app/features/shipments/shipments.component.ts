import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OpsService } from '../../core/services/ops.service';
import { Shipment } from '../../core/models';

@Component({
  selector: 'app-shipments',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-primary">Carrier Logistics & Tracking</h1>
          <p class="text-xs text-secondary mt-0.5">Carrier GPS milestones, shipping SLA compliance, and delay exception telemetry</p>
        </div>
        <div class="flex items-center gap-2">
          <label class="flex items-center gap-2 text-xs text-secondary cursor-pointer select-none">
            <input type="checkbox" [(ngModel)]="delayedOnly" (change)="loadShipments()" class="rounded border-slate-700 bg-slate-900" />
            <span>Delayed shipments only</span>
          </label>
          <button class="btn btn-secondary btn-xs" (click)="loadShipments()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <!-- Shipments Table -->
      <div class="op-table-container">
        <table class="op-table">
          <thead>
            <tr>
              <th>Tracking Number</th>
              <th>Carrier</th>
              <th>Linked Order</th>
              <th>Estimated Delivery</th>
              <th>Actual Delivery</th>
              <th>Status</th>
              <th>SLA Exception</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let s of shipments()" class="hover:bg-[var(--bg-hover)] transition cursor-pointer" (click)="selectedShipment.set(s)">
              <td class="font-mono font-semibold text-brand">{{ s.tracking_number }}</td>
              <td class="font-medium text-primary">{{ s.courier_name }}</td>
              <td class="font-mono text-secondary text-xs">{{ s.order_number || 'Order #' + s.order_id }}</td>
              <td class="font-mono text-muted text-[11px]">{{ s.estimated_delivery | date:'yyyy-MM-dd' }}</td>
              <td class="font-mono text-muted text-[11px]">{{ (s.actual_delivery | date:'yyyy-MM-dd') || 'In Transit' }}</td>
              <td>
                <span class="badge" [ngClass]="getShipmentBadge(s.status)">
                  {{ s.status | uppercase }}
                </span>
              </td>
              <td>
                <span class="badge badge-warning text-[10px]" *ngIf="s.is_delayed">SLA BREACH</span>
                <span class="text-xs text-muted font-mono" *ngIf="!s.is_delayed">On Schedule</span>
              </td>
              <td class="text-right">
                <button class="btn btn-ghost btn-xs text-muted hover:text-primary">
                  Milestones ({{ s.tracking_events.length }})
                </button>
              </td>
            </tr>
            <tr *ngIf="shipments().length === 0">
              <td colspan="8" class="p-8 text-center text-muted text-xs">No shipments found.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Tracking Events Modal Drawer -->
      <div class="modal-overlay" *ngIf="selectedShipment() as s" (click)="selectedShipment.set(null)">
        <div class="modal-card p-5 max-w-xl space-y-4" (click)="$event.stopPropagation()">
          <div class="flex justify-between items-center pb-3 border-b border-[var(--border-subtle)]">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-semibold text-primary font-mono">{{ s.courier_name }}: {{ s.tracking_number }}</h3>
                <span class="badge" [ngClass]="getShipmentBadge(s.status)">{{ s.status | uppercase }}</span>
              </div>
              <div class="text-xs text-muted font-mono mt-0.5">Associated Order: {{ s.order_number }}</div>
            </div>
            <button class="text-muted hover:text-primary" (click)="selectedShipment.set(null)">&times;</button>
          </div>

          <!-- Exception Banner if delayed -->
          <div class="p-3 rounded bg-amber-500/10 border border-amber-500/30 text-xs text-secondary" *ngIf="s.is_delayed">
            <div class="font-semibold text-amber-400 mb-0.5">Carrier Delay Detected Past Delivery SLA</div>
            <div>This shipment has breached its estimated delivery window of {{ s.estimated_delivery | date:'mediumDate' }}. Under company SLA policy, customer qualifies for resolution.</div>
          </div>

          <!-- Milestones Timeline -->
          <div>
            <div class="tech-label mb-2">Carrier Tracking Milestones</div>
            <div class="space-y-2 max-h-64 overflow-y-auto pr-1">
              <div *ngFor="let ev of s.tracking_events" class="p-2.5 rounded bg-[var(--bg-canvas)] border border-[var(--border-subtle)] text-xs">
                <div class="flex items-center justify-between text-[11px] mb-1">
                  <span class="font-medium text-primary">{{ ev.status }}</span>
                  <span class="font-mono text-muted text-[10px]">{{ ev.timestamp | date:'yyyy-MM-dd HH:mm' }}</span>
                </div>
                <div class="text-muted text-[11px]">{{ ev.location }}</div>
              </div>
            </div>
          </div>

          <div class="flex justify-end pt-3 border-t border-[var(--border-subtle)]">
            <button class="btn btn-secondary btn-xs" (click)="selectedShipment.set(null)">Close</button>
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
export class ShipmentsComponent implements OnInit {
  private readonly ops = inject(OpsService);
  readonly shipments = signal<Shipment[]>([]);
  readonly selectedShipment = signal<Shipment | null>(null);
  delayedOnly = false;

  ngOnInit(): void {
    this.loadShipments();
  }

  loadShipments(): void {
    this.ops.listShipments(0, 50, this.delayedOnly).subscribe({
      next: (res) => this.shipments.set(res),
      error: (err) => console.error('Failed to load shipments', err)
    });
  }

  getShipmentBadge(status: string): string {
    switch (status.toLowerCase()) {
      case 'delivered': return 'badge-success';
      case 'in_transit': return 'badge-brand';
      case 'out_for_delivery': return 'badge-cyan';
      case 'delayed': return 'badge-warning';
      case 'failed': return 'badge-danger';
      default: return 'badge-neutral';
    }
  }
}
