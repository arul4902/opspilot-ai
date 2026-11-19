export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'operations_agent' | 'customer';
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  sku: string;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  id: number;
  order_number: string;
  customer_id: number;
  customer_name?: string;
  customer_email?: string;
  status: 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled' | 'returned';
  total_amount: number;
  order_date: string;
  estimated_delivery?: string;
  notes?: string;
  items?: OrderItem[];
}

export interface Payment {
  id: number;
  order_id?: number;
  order_number?: string;
  customer_id: number;
  customer_name?: string;
  amount: number;
  currency: string;
  payment_method: string;
  status: 'pending' | 'successful' | 'failed' | 'refunded';
  transaction_reference: string;
  gateway_response?: string;
  is_orphan?: boolean;
  transaction_date: string;
}

export interface TrackingEvent {
  timestamp: string;
  location: string;
  status: string;
}

export interface Shipment {
  id: number;
  order_id: number;
  order_number?: string;
  tracking_number: string;
  courier_name: string;
  status: 'pending' | 'in_transit' | 'out_for_delivery' | 'delivered' | 'delayed' | 'failed';
  estimated_delivery: string;
  actual_delivery?: string;
  tracking_events: TrackingEvent[];
  is_delayed?: boolean;
  created_at: string;
}

export interface ReturnRequest {
  id: number;
  request_number: string;
  order_id: number;
  order_number?: string;
  customer_id: number;
  customer_name?: string;
  reason: string;
  status: 'requested' | 'approved' | 'rejected' | 'received' | 'completed';
  requested_at: string;
  resolution_notes?: string;
}

export interface RefundRequest {
  id: number;
  refund_number: string;
  order_id: number;
  order_number?: string;
  customer_id: number;
  customer_name?: string;
  amount: number;
  reason: string;
  status: 'pending_approval' | 'approved' | 'rejected' | 'processed' | 'failed';
  is_simulated: boolean;
  approved_by?: number;
  approved_at?: string;
  rejection_reason?: string;
  created_at: string;
}

export interface SupportTicket {
  id: number;
  ticket_number: string;
  customer_id: number;
  customer_name?: string;
  order_id?: number;
  order_number?: string;
  subject: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'open' | 'in_progress' | 'waiting_customer' | 'resolved' | 'closed';
  created_at: string;
}

export interface Escalation {
  id: number;
  conversation_id?: number;
  customer_id: number;
  customer_name?: string;
  reason: string;
  priority: string;
  status: 'pending' | 'in_review' | 'assigned' | 'resolved';
  assigned_to?: number;
  assigned_to_name?: string;
  resolution_notes?: string;
  created_at: string;
}

export interface ApprovalRequestItem {
  id: number;
  agent_run_id?: number;
  order_id?: number;
  request_type: string;
  status: 'pending' | 'approved' | 'rejected';
  requested_by_agent: string;
  payload: Record<string, any>;
  reviewed_by?: number;
  reviewed_by_name?: string;
  reviewed_at?: string;
  comments?: string;
  execution_result?: Record<string, any>;
  created_at: string;
}

export interface ExecutionTimelineEvent {
  timestamp: string;
  stage: string;
  message: string;
  details?: Record<string, any>;
}

export interface PolicyCitation {
  source_document: string;
  section: string;
  snippet: string;
  page_number?: number;
  relevance_score: number;
}

export interface AgentOrchestrationResult {
  run_id: number;
  intent: string;
  confidence: number;
  status: string;
  input_query: string;
  llm_provider?: string;
  is_live_llm?: boolean;
  timeline: ExecutionTimelineEvent[];
  tools_executed: Array<{ tool: string; arguments?: Record<string, any>; result: Record<string, any> }>;
  knowledge_sources: PolicyCitation[];
  recommended_action: string;
  requires_human_approval: boolean;
  approval_request_id?: number;
  final_response: string;
  duration_ms: number;
}

export interface AgentRunSummary {
  id: number;
  intent?: string;
  input_query: string;
  status: string;
  duration_ms: number;
  tool_call_count: number;
  created_at: string;
  completed_at?: string;
  customer_id?: number;
}

export interface KnowledgeDocument {
  id: number;
  filename: string;
  document_type: string;
  file_size: number;
  chunk_count: number;
  checksum?: string;
  created_at: string;
}

export interface AuditLogItem {
  id: number;
  action: string;
  entity_type: string;
  entity_id?: string;
  user_id?: number;
  user_email?: string;
  user_name?: string;
  details: Record<string, any>;
  ip_address?: string;
  timestamp: string;
}

export interface AnalyticsOverview {
  total_orders: number;
  total_revenue: number;
  orders_by_status: Record<string, number>;
  delayed_shipments_count: number;
  failed_payments_count: number;
  orphan_payments_count: number;
  pending_refunds_count: number;
  total_refunded_amount: number;
  pending_approvals_count: number;
  open_tickets_count: number;
  pending_escalations_count: number;
  agent_runs_total: number;
  agent_avg_duration_ms: number;
  agent_success_rate_percent: number;
}

export interface DailyTrendPoint {
  date: string;
  orders_count: number;
  tickets_count: number;
}

