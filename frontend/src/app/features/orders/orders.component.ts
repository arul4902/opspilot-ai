import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OpsService } from '../../core/services/ops.service';
import { Order } from '../../core/models';

@Component({
  selector: 'app-orders',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <h1 class="text-xl font-semibold tracking-tight text-primary">Orders Ledger</h1>
          <p class="text-xs text-secondary mt-0.5">Real-time e-commerce order fulfillment records and item-level details</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadOrders()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <!-- Controls & Filter Bar -->
      <div class="op-card p-3 flex flex-col sm:flex-row justify-between items-center gap-3">
        <div class="w-full sm:w-80">
          <input
            type="text"
            [(ngModel)]="searchQuery"
            placeholder="Filter by order number (e.g. ORD-2024-1002)..."
            class="op-input text-xs"
          />
        </div>
        <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
          <span class="text-xs text-muted">Status:</span>
          <select [(ngModel)]="statusFilter" (change)="loadOrders()" class="op-input text-xs" style="width: auto;">
            <option value="">All Statuses</option>
            <option value="delivered">Delivered</option>
            <option value="shipped">Shipped</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      <!-- Orders Data Table -->
      <div class="op-table-container">
        <table class="op-table">
          <thead>
            <tr>
              <th>Order Number</th>
              <th>Customer Name</th>
              <th>Order Date</th>
              <th>Total Amount</th>
              <th>Status</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let ord of filteredOrders()" class="cursor-pointer hover:bg-[var(--bg-hover)] transition" (click)="selectOrder(ord)">
              <td class="font-mono font-semibold text-brand">{{ ord.order_number }}</td>
              <td class="text-secondary">{{ ord.customer_name || 'Customer #' + ord.customer_id }}</td>
              <td class="font-mono text-muted text-[11px]">{{ ord.order_date | date:'yyyy-MM-dd HH:mm' }}</td>
              <td class="font-mono text-primary font-medium">\${{ ord.total_amount | number:'1.2-2' }}</td>
              <td>
                <span class="badge" [ngClass]="getStatusBadge(ord.status)">
                  {{ ord.status | uppercase }}
                </span>
              </td>
              <td class="text-right">
                <button class="btn btn-ghost btn-xs text-muted hover:text-primary">
                  Inspect
                </button>
              </td>
            </tr>
            <tr *ngIf="filteredOrders().length === 0">
              <td colspan="6" class="p-8 text-center text-muted text-xs">No orders matching filter criteria.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Order Detail Drawer Modal -->
      <div class="modal-overlay" *ngIf="selectedOrder() as ord" (click)="selectedOrder.set(null)">
        <div class="modal-card p-5 max-w-2xl space-y-4" (click)="$event.stopPropagation()">
          <div class="flex justify-between items-center pb-3 border-b border-[var(--border-subtle)]">
            <div class="flex items-center gap-2">
              <h2 class="text-sm font-semibold text-primary font-mono">{{ ord.order_number }}</h2>
              <span class="badge" [ngClass]="getStatusBadge(ord.status)">{{ ord.status | uppercase }}</span>
            </div>
            <button class="text-muted hover:text-primary" (click)="selectedOrder.set(null)">&times;</button>
          </div>

          <div class="grid grid-cols-2 gap-3 text-xs">
            <div class="p-3 rounded bg-[var(--bg-canvas)] border border-[var(--border-default)]">
              <div class="tech-label mb-1">Customer Profile</div>
              <div class="font-medium text-primary">{{ ord.customer_name || 'Customer #' + ord.customer_id }}</div>
              <div class="text-muted text-[11px] font-mono">{{ ord.customer_email || 'No email on record' }}</div>
            </div>
            <div class="p-3 rounded bg-[var(--bg-canvas)] border border-[var(--border-default)]">
              <div class="tech-label mb-1">Order Financials</div>
              <div class="font-mono font-bold text-brand text-sm">\${{ ord.total_amount | number:'1.2-2' }}</div>
              <div class="text-muted text-[11px] font-mono">Date: {{ ord.order_date | date:'yyyy-MM-dd' }}</div>
            </div>
          </div>

          <!-- Items Table -->
          <div>
            <div class="tech-label mb-2">Order Line Items ({{ ord.items?.length || 0 }})</div>
            <div class="op-table-container">
              <table class="op-table text-xs">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th>Qty</th>
                    <th>Unit Price</th>
                    <th>Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let item of ord.items">
                    <td class="font-medium text-primary">{{ item.product_name }}</td>
                    <td class="font-mono text-muted text-[11px]">{{ item.sku }}</td>
                    <td class="font-mono text-secondary">{{ item.quantity }}</td>
                    <td class="font-mono text-secondary">\${{ item.unit_price | number:'1.2-2' }}</td>
                    <td class="font-mono font-medium text-primary">\${{ item.subtotal | number:'1.2-2' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="flex justify-end pt-3 border-t border-[var(--border-subtle)]">
            <button class="btn btn-secondary btn-xs" (click)="selectedOrder.set(null)">Close</button>
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
export class OrdersComponent implements OnInit {
  private readonly opsService = inject(OpsService);

  readonly orders = signal<Order[]>([]);
  readonly selectedOrder = signal<Order | null>(null);

  searchQuery = '';
  statusFilter = '';

  ngOnInit(): void {
    this.loadOrders();
  }

  loadOrders(): void {
    this.opsService.listOrders(0, 50, this.statusFilter || undefined).subscribe({
      next: (res) => this.orders.set(res),
      error: (err) => console.error('Failed to load orders', err)
    });
  }

  filteredOrders(): Order[] {
    let list = this.orders();
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter(o => 
        o.order_number.toLowerCase().includes(q) ||
        (o.customer_name && o.customer_name.toLowerCase().includes(q))
      );
    }
    return list;
  }

  selectOrder(ord: Order): void {
    this.opsService.getOrderDetail(ord.id).subscribe({
      next: (detail: Order) => this.selectedOrder.set(detail),
      error: () => this.selectedOrder.set(ord)
    });
  }

  getStatusBadge(status: string): string {
    switch (status.toLowerCase()) {
      case 'delivered': return 'badge-success';
      case 'shipped': return 'badge-brand';
      case 'processing': return 'badge-neutral';
      case 'confirmed': return 'badge-neutral';
      case 'pending': return 'badge-warning';
      case 'cancelled': return 'badge-danger';
      default: return 'badge-neutral';
    }
  }
}
