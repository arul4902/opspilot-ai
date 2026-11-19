import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  template: `
    <div class="login-wrapper">
      <div class="login-card">
        <!-- Logo Header -->
        <div class="login-header">
          <div class="logo-box">
            <svg width="20" height="20" class="w-5 h-5 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m13 2-2 10h8L7 22l2-10H1L13 2z"/>
            </svg>
          </div>
          <h1 class="login-title">OpsPilot AI</h1>
          <p class="login-subtitle">Autonomous E-Commerce Operations Platform</p>
        </div>

        <!-- Error Message Banner -->
        <div class="error-banner" *ngIf="errorMessage()">
          <svg width="16" height="16" class="w-4 h-4 text-rose-400 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <span>{{ errorMessage() }}</span>
        </div>

        <!-- Form -->
        <form [formGroup]="form" (ngSubmit)="onSubmit()" class="login-form">
          <div class="form-group">
            <label class="op-label">Email Address</label>
            <input
              type="email"
              formControlName="email"
              class="op-input"
              placeholder="operator@opspilot.ai"
              autocomplete="email"
            />
          </div>

          <div class="form-group">
            <label class="op-label">Password</label>
            <input
              type="password"
              formControlName="password"
              class="op-input font-mono"
              placeholder="••••••••••••"
              autocomplete="current-password"
            />
          </div>

          <button type="submit" class="btn btn-primary w-full mt-2" [disabled]="form.invalid || isLoading()">
            <span *ngIf="!isLoading()">Sign In to Operations Console</span>
            <span *ngIf="isLoading()">Authenticating Session...</span>
          </button>
        </form>

        <!-- Quick Fill Credentials -->
        <div class="demo-box">
          <div class="demo-title">Quick Demo Sign-In Credentials</div>
          <div class="demo-buttons">
            <button type="button" class="demo-btn admin" (click)="fillCreds('admin@opspilot.ai', 'Admin@OpsPilot2026!')">
              Lead Admin
            </button>
            <button type="button" class="demo-btn agent" (click)="fillCreds('agent@opspilot.ai', 'Agent@OpsPilot2026!')">
              Ops Specialist
            </button>
            <button type="button" class="demo-btn cust" (click)="fillCreds('customer@opspilot.ai', 'Customer@OpsPilot2026!')">
              Customer
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-wrapper {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: var(--bg-canvas);
      padding: 1.5rem;
    }
    .login-card {
      width: 100%;
      max-width: 380px;
      background: var(--bg-surface);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-lg);
      padding: 2rem;
      box-shadow: var(--shadow-lg);
    }
    .login-header {
      text-align: center;
      margin-bottom: 1.75rem;
    }
    .logo-box {
      width: 40px;
      height: 40px;
      margin: 0 auto 0.75rem;
      border-radius: var(--radius-md);
      background: var(--bg-elevated);
      border: 1px solid var(--border-default);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .login-title {
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--text-primary);
      letter-spacing: -0.015em;
    }
    .login-subtitle {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 0.25rem;
    }
    .error-banner {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--danger-bg);
      border: 1px solid var(--danger-border);
      color: var(--color-danger);
      padding: 0.625rem 0.75rem;
      border-radius: var(--radius-sm);
      font-size: 0.75rem;
      margin-bottom: 1.25rem;
    }
    .login-form {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .form-group {
      display: flex;
      flex-direction: column;
    }
    .demo-box {
      margin-top: 1.75rem;
      padding-top: 1.25rem;
      border-top: 1px solid var(--border-subtle);
    }
    .demo-title {
      font-size: 0.625rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-tertiary);
      margin-bottom: 0.5rem;
      text-align: center;
    }
    .demo-buttons {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.375rem;
    }
    .demo-btn {
      background: var(--bg-elevated);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-xs);
      padding: 0.375rem 0.25rem;
      font-size: 0.6875rem;
      font-weight: 500;
      cursor: pointer;
      color: var(--text-secondary);
      transition: all 0.12s ease;
      text-align: center;
    }
    .demo-btn:hover {
      background: var(--bg-subtle);
      border-color: var(--border-hover);
      color: var(--text-primary);
    }
    .demo-btn.admin:hover { border-color: var(--purple-border); color: var(--color-purple); }
    .demo-btn.agent:hover { border-color: var(--brand-border); color: var(--brand-primary); }
    .demo-btn.cust:hover { border-color: var(--success-border); color: var(--color-success); }
  `]
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly isLoading = signal(false);
  readonly errorMessage = signal<string | null>(null);

  readonly form = this.fb.group({
    email: ['agent@opspilot.ai', [Validators.required, Validators.email]],
    password: ['Agent@OpsPilot2026!', [Validators.required, Validators.minLength(6)]]
  });

  fillCreds(email: string, pass: string): void {
    this.form.patchValue({ email, password: pass });
    this.errorMessage.set(null);
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const { email, password } = this.form.value;
    this.auth.login(email!, password!).subscribe({
      next: () => {
        const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/overview';
        this.router.navigateByUrl(returnUrl);
      },
      error: (err: any) => {
        this.isLoading.set(false);
        let msg = 'Authentication failed. Please verify credentials.';

        if (err?.error) {
          if (typeof err.error === 'string') {
            msg = err.error;
          } else if (typeof err.error.detail === 'string') {
            msg = err.error.detail;
          } else if (Array.isArray(err.error.detail) && err.error.detail.length > 0) {
            const firstErr = err.error.detail[0];
            msg = firstErr?.msg || firstErr?.message || 'Invalid input format.';
          } else if (typeof err.error.message === 'string') {
            msg = err.error.message;
          } else if (typeof err.error.error === 'string') {
            msg = err.error.error;
          }
        } else if (err?.status === 0) {
          msg = 'Backend server unavailable. Please check backend connection.';
        } else if (err?.status === 401) {
          msg = 'Invalid credentials. Click a Demo Account button below to test.';
        } else if (typeof err?.message === 'string') {
          msg = err.message;
        }

        if (typeof msg !== 'string' || msg === '[object Object]') {
          msg = 'Authentication failed. Please verify your credentials.';
        }

        this.errorMessage.set(msg);
      }
    });
  }
}
