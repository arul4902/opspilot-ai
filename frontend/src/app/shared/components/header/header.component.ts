import { Component, inject, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  template: `
    <header class="header">
      <div class="header-left">
        <!-- Mobile Drawer Hamburger Toggle -->
        <button class="menu-btn md:hidden" (click)="toggleSidebar.emit()" title="Toggle Navigation">
          <svg width="16" height="16" class="w-4 h-4 text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>

        <!-- System Heartbeat & Telemetry -->
        <div class="system-status">
          <span class="status-indicator live"></span>
          <span class="status-label">Autonomous Ops Active</span>
        </div>

        <div class="header-divider hidden sm:block"></div>

        <div class="meta-tag hidden sm:flex">
          <span class="meta-key">Environment:</span>
          <span class="meta-val font-mono">Production Engine</span>
        </div>

        <div class="header-divider hidden md:block"></div>

        <div class="meta-tag hidden md:flex">
          <span class="meta-key">Knowledge Index:</span>
          <span class="meta-val font-mono">59 Enterprise Policy Vectors</span>
        </div>
      </div>

      <div class="header-right" *ngIf="auth.currentUser() as user">
        <!-- Active Session Role Badge -->
        <div class="role-badge" [ngClass]="user.role">
          <span class="role-dot"></span>
          <span>{{ user.role.replace('_', ' ') | uppercase }}</span>
        </div>
      </div>
    </header>
  `,
  styles: [`
    .header {
      height: 44px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-default);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 1rem;
      position: sticky;
      top: 0;
      z-index: 20;
    }

    .header-left, .header-right {
      display: flex;
      align-items: center;
      gap: 0.625rem;
    }

    .menu-btn {
      background: transparent;
      border: none;
      cursor: pointer;
      padding: 0.25rem;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-xs);
    }
    .menu-btn:hover {
      background: var(--bg-elevated);
    }

    .system-status {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.6875rem;
      font-weight: 500;
      color: var(--color-success);
      padding: 0.2rem 0.45rem;
      border-radius: var(--radius-xs);
      background: var(--success-bg);
      border: 1px solid var(--success-border);
    }

    .header-divider {
      width: 1px;
      height: 16px;
      background: var(--border-subtle);
    }

    .meta-tag {
      display: flex;
      align-items: center;
      gap: 0.3125rem;
      font-size: 0.6875rem;
      color: var(--text-muted);
    }
    .meta-val {
      color: var(--text-secondary);
    }

    .role-badge {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.625rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      padding: 0.2rem 0.5rem;
      border-radius: var(--radius-xs);
      background: var(--bg-elevated);
      border: 1px solid var(--border-default);
      color: var(--text-secondary);
    }

    .role-dot {
      width: 5px;
      height: 5px;
      border-radius: var(--radius-full);
      background: var(--text-muted);
    }

    .role-badge.admin {
      background: var(--purple-bg);
      border-color: var(--purple-border);
      color: var(--color-purple);
    }
    .role-badge.admin .role-dot {
      background: var(--color-purple);
    }

    .role-badge.operations_agent {
      background: var(--brand-bg);
      border-color: var(--brand-border);
      color: var(--brand-primary);
    }
    .role-badge.operations_agent .role-dot {
      background: var(--brand-primary);
    }

    .role-badge.customer {
      background: var(--success-bg);
      border-color: var(--success-border);
      color: var(--color-success);
    }
    .role-badge.customer .role-dot {
      background: var(--color-success);
    }
  `]
})
export class HeaderComponent {
  readonly auth = inject(AuthService);
  @Output() toggleSidebar = new EventEmitter<void>();
}
