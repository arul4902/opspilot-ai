import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Order, Payment, Shipment, ReturnRequest, RefundRequest,
  SupportTicket, Escalation, ApprovalRequestItem, AgentOrchestrationResult,
  AgentRunSummary, KnowledgeDocument, AuditLogItem, AnalyticsOverview, DailyTrendPoint, PolicyCitation
} from '../models';

export interface SSEAgentEvent {
  event: string;
  data: any;
  id?: string;
}

@Injectable({
  providedIn: 'root'
})
export class OpsService {
  private readonly baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // 1. Agent Endpoints
  sendAgentMessage(query: string, customerId?: number, conversationId?: number): Observable<AgentOrchestrationResult> {
    return this.http.post<AgentOrchestrationResult>(`${this.baseUrl}/agent/message`, {
      query,
      customer_id: customerId,
      conversation_id: conversationId
    });
  }

  streamAgentMessage(query: string, customerId?: number, conversationId?: number): Observable<SSEAgentEvent> {
    return new Observable<SSEAgentEvent>(observer => {
      const controller = new AbortController();
      const token = localStorage.getItem('opspilot_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      fetch(`${this.baseUrl}/agent/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query,
          customer_id: customerId,
          conversation_id: conversationId
        }),
        signal: controller.signal
      }).then(async response => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const reader = response.body?.getReader();
        if (!reader) throw new Error('Response stream not readable');
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          for (const part of parts) {
            if (!part.trim() || part.startsWith(':')) continue;
            let eventType = 'message';
            let eventData = '';
            let eventId = '';

            for (const line of part.split('\n')) {
              if (line.startsWith('event:')) {
                eventType = line.substring(6).trim();
              } else if (line.startsWith('data:')) {
                eventData = line.substring(5).trim();
              } else if (line.startsWith('id:')) {
                eventId = line.substring(3).trim();
              }
            }

            try {
              const parsed = eventData ? JSON.parse(eventData) : {};
              observer.next({ event: eventType, data: parsed, id: eventId });
            } catch {
              observer.next({ event: eventType, data: eventData, id: eventId });
            }
          }
        }
        observer.complete();
      }).catch(err => {
        if (err.name !== 'AbortError') {
          observer.error(err);
        }
      });

      return () => controller.abort();
    });
  }

  listAgentRuns(skip = 0, limit = 20): Observable<AgentRunSummary[]> {
    const params = new HttpParams().set('skip', skip).set('limit', limit);
    return this.http.get<AgentRunSummary[]>(`${this.baseUrl}/agent/runs`, { params });
  }

  getAgentRunDetail(id: number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/agent/runs/${id}`);
  }

  getAgentRunEvents(id: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/agent/runs/${id}/events`);
  }

  // 2. Real-Time Dashboard Events (SSE)
  listenToDashboardEvents(): Observable<SSEAgentEvent> {
    return new Observable<SSEAgentEvent>(observer => {
      const eventSource = new EventSource(`${this.baseUrl}/events/stream`);

      const registeredEvents = [
        'system.connected',
        'order.created',
        'order.updated',
        'approval.created',
        'approval.reviewed',
        'agent.run_completed'
      ];

      registeredEvents.forEach(evtName => {
        eventSource.addEventListener(evtName, (e: any) => {
          try {
            const parsed = JSON.parse(e.data);
            observer.next({ event: evtName, data: parsed, id: e.lastEventId });
          } catch {
            observer.next({ event: evtName, data: e.data, id: e.lastEventId });
          }
        });
      });

      eventSource.onmessage = (e) => {
        try {
          observer.next({ event: 'message', data: JSON.parse(e.data), id: e.lastEventId });
        } catch {
          observer.next({ event: 'message', data: e.data, id: e.lastEventId });
        }
      };

      eventSource.onerror = (err) => {
        console.warn('[SSE Feed] Stream disconnected or reconnecting...', err);
      };

      return () => eventSource.close();
    });
  }

  // 3. Analytics
  getAnalyticsOverview(): Observable<AnalyticsOverview> {
    return this.http.get<AnalyticsOverview>(`${this.baseUrl}/analytics/overview`);
  }

  getAnalyticsTrends(days = 14): Observable<DailyTrendPoint[]> {
    const params = new HttpParams().set('days', days);
    return this.http.get<DailyTrendPoint[]>(`${this.baseUrl}/analytics/trends`, { params });
  }

  // 4. Approvals
  listApprovals(status?: string): Observable<ApprovalRequestItem[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    return this.http.get<ApprovalRequestItem[]>(`${this.baseUrl}/approvals`, { params });
  }

  approveRequest(id: number, comments?: string): Observable<ApprovalRequestItem> {
    return this.http.post<ApprovalRequestItem>(`${this.baseUrl}/approvals/${id}/approve`, { comments });
  }

  rejectRequest(id: number, comments: string): Observable<ApprovalRequestItem> {
    return this.http.post<ApprovalRequestItem>(`${this.baseUrl}/approvals/${id}/reject`, { comments });
  }

  // 5. Orders
  listOrders(skipOrStatus?: any, limitOrCustomerId?: any, status?: string, customerId?: number): Observable<Order[]> {
    let skip = 0;
    let limit = 50;
    let s = status;
    let c = customerId;

    if (typeof skipOrStatus === 'number') {
      skip = skipOrStatus;
      limit = typeof limitOrCustomerId === 'number' ? limitOrCustomerId : 50;
      s = status;
    } else if (typeof skipOrStatus === 'string') {
      s = skipOrStatus;
      c = limitOrCustomerId;
    }

    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (s) params = params.set('status', s);
    if (c) params = params.set('customer_id', c);
    return this.http.get<Order[]>(`${this.baseUrl}/orders`, { params });
  }

  getOrder(id: number): Observable<Order> {
    return this.http.get<Order>(`${this.baseUrl}/orders/${id}`);
  }

  getOrderDetail(id: number): Observable<Order> {
    return this.getOrder(id);
  }

  createOrder(orderData: any): Observable<Order> {
    return this.http.post<Order>(`${this.baseUrl}/orders`, orderData);
  }

  updateOrderStatus(id: number, newStatus: string): Observable<Order> {
    return this.http.patch<Order>(`${this.baseUrl}/orders/${id}/status`, { status: newStatus });
  }

  // 6. Payments
  listPayments(skip = 0, limit = 50): Observable<Payment[]> {
    const params = new HttpParams().set('skip', skip).set('limit', limit);
    return this.http.get<Payment[]>(`${this.baseUrl}/payments`, { params });
  }

  // 7. Shipments
  listShipments(skipOrStatus?: any, limitOrDelayed?: any, delayedOnly?: boolean): Observable<Shipment[]> {
    let params = new HttpParams();
    if (typeof skipOrStatus === 'string') {
      params = params.set('status', skipOrStatus);
    } else {
      const skip = typeof skipOrStatus === 'number' ? skipOrStatus : 0;
      const limit = typeof limitOrDelayed === 'number' ? limitOrDelayed : 50;
      params = params.set('skip', skip).set('limit', limit);
      if (delayedOnly || limitOrDelayed === true) {
        params = params.set('status', 'delayed');
      }
    }
    return this.http.get<Shipment[]>(`${this.baseUrl}/shipments`, { params });
  }

  // 8. Returns & Refunds
  listReturns(status?: string): Observable<ReturnRequest[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    return this.http.get<ReturnRequest[]>(`${this.baseUrl}/returns`, { params });
  }

  listRefunds(status?: string): Observable<RefundRequest[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    return this.http.get<RefundRequest[]>(`${this.baseUrl}/refunds`, { params });
  }

  // 9. Tickets
  listTickets(status?: string, priority?: string): Observable<SupportTicket[]> {
    let params = new HttpParams();
    if (status) params = params.set('status', status);
    if (priority) params = params.set('priority', priority);
    return this.http.get<SupportTicket[]>(`${this.baseUrl}/tickets`, { params });
  }

  // 10. Knowledge & RAG
  listKnowledgeDocuments(): Observable<KnowledgeDocument[]> {
    return this.http.get<KnowledgeDocument[]>(`${this.baseUrl}/knowledge/documents`);
  }

  getKnowledgeDocumentDetail(id: number): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/knowledge/documents/${id}`);
  }

  searchKnowledge(query: string, topK = 3): Observable<{ query: string; total_results: number; citations: PolicyCitation[] }> {
    const params = new HttpParams().set('query', query).set('top_k', topK);
    return this.http.get<any>(`${this.baseUrl}/knowledge/search`, { params });
  }

  uploadDocument(file: File, category = 'operational_policy'): Observable<KnowledgeDocument> {
    const form = new FormData();
    form.append('file', file);
    form.append('category', category);
    return this.http.post<KnowledgeDocument>(`${this.baseUrl}/knowledge/upload`, form);
  }

  deleteKnowledgeDocument(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/knowledge/documents/${id}`);
  }

  // 11. Audit Logs
  listAuditLogs(skip = 0, limit = 50, action?: string): Observable<AuditLogItem[]> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (action) params = params.set('action', action);
    return this.http.get<AuditLogItem[]>(`${this.baseUrl}/audit-logs`, { params });
  }
}
