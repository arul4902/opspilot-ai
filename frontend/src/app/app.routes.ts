import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { LoginComponent } from './features/login/login.component';
import { OverviewComponent } from './features/overview/overview.component';
import { AgentWorkspaceComponent } from './features/agent-workspace/agent-workspace.component';
import { ApprovalsComponent } from './features/approvals/approvals.component';
import { OrdersComponent } from './features/orders/orders.component';
import { PaymentsComponent } from './features/payments/payments.component';
import { ShipmentsComponent } from './features/shipments/shipments.component';
import { ReturnsRefundsComponent } from './features/returns-refunds/returns-refunds.component';
import { TicketsComponent } from './features/tickets/tickets.component';
import { KnowledgeComponent } from './features/knowledge/knowledge.component';
import { AuditLogsComponent } from './features/audit-logs/audit-logs.component';
import { ExecutionInspectorComponent } from './features/execution-inspector/execution-inspector.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'overview', component: OverviewComponent, canActivate: [authGuard] },
  { path: 'agent', component: AgentWorkspaceComponent, canActivate: [authGuard] },
  { path: 'inspector', component: ExecutionInspectorComponent, canActivate: [authGuard] },
  { path: 'approvals', component: ApprovalsComponent, canActivate: [authGuard] },
  { path: 'orders', component: OrdersComponent, canActivate: [authGuard] },
  { path: 'payments', component: PaymentsComponent, canActivate: [authGuard] },
  { path: 'shipments', component: ShipmentsComponent, canActivate: [authGuard] },
  { path: 'returns-refunds', component: ReturnsRefundsComponent, canActivate: [authGuard] },
  { path: 'tickets', component: TicketsComponent, canActivate: [authGuard] },
  { path: 'knowledge', component: KnowledgeComponent, canActivate: [authGuard] },
  { path: 'audit-logs', component: AuditLogsComponent, canActivate: [authGuard] },
  { path: '', redirectTo: 'overview', pathMatch: 'full' },
  { path: '**', redirectTo: 'overview' }
];
