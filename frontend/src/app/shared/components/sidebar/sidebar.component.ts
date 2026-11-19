import { Component, inject, signal, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <aside class="sidebar" [class.mobile-open]="isOpen">
      <!-- Brand Header -->
      <div class="brand">
        <div class="brand-left">
          <div class="logo-box">
            <svg width="16" height="16" class="w-4 h-4 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m13 2-2 10h8L7 22l2-10H1L13 2z"/>
            </svg>
          </div>
          <div class="brand-text">
            <div class="brand-title">OpsPilot <span class="brand-tag">Ops</span></div>
            <div class="brand-sub">Platform v2.4</div>
          </div>
        </div>

        <button *ngIf="isOpen" class="close-mobile-btn md:hidden" (click)="closeSidebar.emit()">
          <svg width="16" height="16" class="w-4 h-4 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Navigation Links -->
      <nav class="nav-menu">
        <div class="nav-section-label">Operations</div>
        
        <a routerLink="/overview" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>
          </svg>
          <span>Overview</span>
        </a>

        <a routerLink="/agent" routerLinkActive="active" class="nav-item agent-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>
          </svg>
          <span class="flex-1">Agent Workspace</span>
          <span class="status-indicator live"></span>
        </a>

        <a routerLink="/inspector" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 12h20"/><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6"/><path d="M12 2v10"/><path d="m17 7-5-5-5 5"/>
          </svg>
          <span>Live Inspector</span>
        </a>

        <a routerLink="/approvals" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon text-warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>
          </svg>
          <span>Approval Queue</span>
        </a>

        <div class="nav-section-label">Entities</div>

        <a routerLink="/orders" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>
          </svg>
          <span>Orders</span>
        </a>

        <a routerLink="/payments" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>
          </svg>
          <span>Payments</span>
        </a>

        <a routerLink="/shipments" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/><path d="M15 18H9"/><path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/><circle cx="17" cy="18" r="2"/><circle cx="7" cy="18" r="2"/>
          </svg>
          <span>Shipments</span>
        </a>

        <a routerLink="/returns-refunds" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m3 9 4-4 4 4"/><path d="M7 5v10a4 4 0 0 0 4 4h10"/><path d="m21 15-4 4-4-4"/>
          </svg>
          <span>Returns & Refunds</span>
        </a>

        <a routerLink="/tickets" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v2"/><path d="M13 17v2"/><path d="M13 11v2"/>
          </svg>
          <span>Support Tickets</span>
        </a>

        <div class="nav-section-label">System</div>

        <a routerLink="/knowledge" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M6 6h10"/><path d="M6 10h10"/>
          </svg>
          <span>Knowledge Base (RAG)</span>
        </a>

        <a routerLink="/audit-logs" routerLinkActive="active" class="nav-item" (click)="onNavClick()">
          <svg width="16" height="16" class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>
          </svg>
          <span>Audit Logs</span>
        </a>
      </nav>

      <!-- User Box Footer -->
      <div class="user-box" *ngIf="auth.currentUser() as user">
        <div class="user-avatar">{{ user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U' }}</div>
        <div class="user-info">
          <div class="user-name" [title]="user.full_name">{{ user.full_name || 'Operator' }}</div>
          <div class="user-role">{{ user.role.replace('_', ' ') }}</div>
        </div>
        <button class="logout-btn" (click)="auth.logout()" title="Sign out of console">
          <svg width="14" height="14" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>
          </svg>
        </button>
      </div>
    </aside>
  `,
  styles: [`
    .sidebar {
      width: 220px;
      height: 100vh;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-default);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      user-select: none;
      z-index: 40;
      transition: transform 0.2s ease;
    }

    .brand {
      height: 52px;
      padding: 0 1rem;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand-left {
      display: flex;
      align-items: center;
      gap: 0.625rem;
    }

    .logo-box {
      width: 26px;
      height: 26px;
      border-radius: var(--radius-sm);
      background: var(--bg-elevated);
      border: 1px solid var(--border-default);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .brand-title {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--text-primary);
      letter-spacing: -0.01em;
      line-height: 1.1;
    }

    .brand-tag {
      font-size: 0.625rem;
      font-weight: 500;
      background: var(--brand-bg);
      color: var(--brand-primary);
      padding: 0.1rem 0.3rem;
      border-radius: var(--radius-xs);
      border: 1px solid var(--brand-border);
      margin-left: 0.25rem;
    }

    .brand-sub {
      font-size: 0.625rem;
      color: var(--text-muted);
    }

    .close-mobile-btn {
      background: transparent;
      border: none;
      cursor: pointer;
      padding: 0.25rem;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .nav-menu {
      flex: 1;
      padding: 0.75rem 0.5rem;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }

    .nav-section-label {
      font-size: 0.625rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--text-tertiary);
      padding: 0.75rem 0.5rem 0.25rem;
    }

    .nav-section-label:first-child {
      padding-top: 0.25rem;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.625rem;
      padding: 0.375rem 0.625rem;
      color: var(--text-secondary);
      text-decoration: none;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      font-weight: 500;
      transition: all 0.12s ease;
      position: relative;
    }

    .nav-icon {
      width: 15px;
      height: 15px;
      flex-shrink: 0;
      color: var(--text-muted);
      transition: color 0.12s ease;
    }

    .nav-item:hover {
      background: var(--bg-elevated);
      color: var(--text-primary);
    }

    .nav-item:hover .nav-icon {
      color: var(--text-primary);
    }

    .nav-item.active {
      background: var(--bg-elevated);
      color: var(--text-primary);
      font-weight: 600;
    }

    .nav-item.active::before {
      content: '';
      position: absolute;
      left: -0.5rem;
      top: 4px;
      bottom: 4px;
      width: 2px;
      background: var(--brand-primary);
      border-radius: 0 2px 2px 0;
    }

    .nav-item.active .nav-icon {
      color: var(--brand-primary);
    }

    .user-box {
      padding: 0.625rem 0.75rem;
      border-top: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .user-avatar {
      width: 26px;
      height: 26px;
      border-radius: var(--radius-sm);
      background: var(--bg-subtle);
      border: 1px solid var(--border-default);
      color: var(--text-primary);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 0.6875rem;
      flex-shrink: 0;
    }

    .user-info {
      flex: 1;
      min-width: 0;
    }

    .user-name {
      font-size: 0.6875rem;
      font-weight: 600;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 1.2;
    }

    .user-role {
      font-size: 0.5625rem;
      color: var(--text-muted);
      text-transform: capitalize;
    }

    .logout-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding: 0.3rem;
      border-radius: var(--radius-xs);
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.12s ease;
    }

    .logout-btn:hover {
      background: var(--bg-elevated);
      color: var(--color-danger);
    }

    /* Mobile drawer states */
    @media (max-width: 768px) {
      .sidebar {
        position: fixed;
        left: 0;
        top: 0;
        bottom: 0;
        transform: translateX(-100%);
      }
      .sidebar.mobile-open {
        transform: translateX(0);
        box-shadow: var(--shadow-modal);
      }
    }
  `]
})
export class SidebarComponent {
  readonly auth = inject(AuthService);

  @Input() isOpen = false;
  @Output() closeSidebar = new EventEmitter<void>();

  onNavClick(): void {
    if (this.isOpen) {
      this.closeSidebar.emit();
    }
  }
}
