import {
  Order,
  OrderListResponse,
  OrderJourneyData,
  Incident,
  IncidentDetail,
  RCAReport,
  OperatorApproval,
  AuditEvent,
  AnalyticsMetrics,
  FailureDistribution,
  SimulationResult
} from '../types';

export class ApiError extends Error {
  status: number;
  data?: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

const API_BASE = '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  try {
    const res = await fetch(url, { ...options, headers });
    const json = await res.json().catch(() => null);

    if (!res.ok) {
      const errorMsg =
        json?.detail ||
        json?.error?.message ||
        json?.message ||
        `HTTP ${res.status}: ${res.statusText}`;
      throw new ApiError(errorMsg, res.status, json);
    }

    if (json && typeof json === 'object' && 'data' in json && 'success' in json) {
      return json.data as T;
    }

    return json as T;
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(err?.message || 'Network request failed', 0);
  }
}

export const api = {
  // Analytics
  async getMetrics(): Promise<AnalyticsMetrics> {
    return request<AnalyticsMetrics>('/analytics/metrics');
  },

  async getFailureDistribution(): Promise<FailureDistribution> {
    return request<FailureDistribution>('/analytics/distribution');
  },

  // Orders
  async getOrders(params: {
    page?: number;
    limit?: number;
    skip?: number;
    status?: string;
    search?: string;
    is_demo?: boolean;
    demo_session_id?: string;
  } = {}): Promise<OrderListResponse> {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page.toString());
    if (params.skip !== undefined) query.append('skip', params.skip.toString());
    if (params.limit) query.append('limit', params.limit.toString());
    if (params.status && params.status !== 'ALL') query.append('status', params.status);
    if (params.search) query.append('search', params.search);
    if (params.is_demo !== undefined) query.append('is_demo', params.is_demo.toString());
    if (params.demo_session_id) query.append('demo_session_id', params.demo_session_id);
    const qs = query.toString();
    return request<OrderListResponse>(`/orders${qs ? `?${qs}` : ''}`);
  },

  async getOrder(orderId: string): Promise<Order> {
    return request<Order>(`/orders/${encodeURIComponent(orderId)}`);
  },

  async getOrderJourney(orderId: string): Promise<OrderJourneyData> {
    const data = await request<any>(`/orders/${encodeURIComponent(orderId)}/journey`);
    const events = data.raw_events || data.telemetry_events || [];
    return {
      ...data,
      raw_events: events,
      telemetry_events: events
    } as OrderJourneyData;
  },

  // Incidents
  async getIncidents(params: { status?: string; order_id?: string } = {}): Promise<Incident[]> {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.order_id) query.append('order_id', params.order_id);
    const qs = query.toString();
    return request<Incident[]>(`/incidents${qs ? `?${qs}` : ''}`);
  },

  async getIncident(incidentId: string): Promise<Incident> {
    return request<Incident>(`/incidents/${encodeURIComponent(incidentId)}`);
  },

  async getIncidentDetail(incidentId: string): Promise<IncidentDetail> {
    return request<IncidentDetail>(`/incidents/${encodeURIComponent(incidentId)}`);
  },

  // Advisory RCA
  async getIncidentRCA(incidentId: string): Promise<RCAReport> {
    return request<RCAReport>(`/rca/${encodeURIComponent(incidentId)}/analyze`, {
      method: 'POST'
    });
  },

  // Resolutions
  async executeResolution(payload: { incident_id: string; action_type: string; idempotency_key: string }): Promise<any> {
    return request<any>('/resolutions/execute', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  // Approvals
  async getPendingApprovals(params: { demo_session_id?: string; is_demo?: boolean } = {}): Promise<OperatorApproval[]> {
    const query = new URLSearchParams();
    if (params.demo_session_id) query.append('demo_session_id', params.demo_session_id);
    if (params.is_demo !== undefined) query.append('is_demo', params.is_demo.toString());
    const qs = query.toString();
    return request<OperatorApproval[]>(`/approvals/pending${qs ? `?${qs}` : ''}`);
  },

  async getApproval(approvalId: string): Promise<OperatorApproval> {
    return request<OperatorApproval>(`/approvals/${encodeURIComponent(approvalId)}`);
  },

  async decideApproval(
    approvalId: string,
    payload: {
      decision: 'APPROVED' | 'REJECTED';
      operator_id: string;
      operator_name?: string;
      operator_notes?: string;
      selected_action?: string;
      action_parameters?: Record<string, any>;
    }
  ): Promise<any> {
    return request<any>(`/approvals/${encodeURIComponent(approvalId)}/decide`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  // Audit Logs
  async getAuditLogs(params: { order_id?: string; incident_id?: string; actor_type?: string; page?: number; limit?: number } = {}): Promise<AuditEvent[]> {
    const query = new URLSearchParams();
    if (params.order_id) query.append('order_id', params.order_id);
    if (params.incident_id) query.append('incident_id', params.incident_id);
    if (params.actor_type && params.actor_type !== 'ALL') query.append('actor_type', params.actor_type);
    if (params.page) query.append('page', params.page.toString());
    if (params.limit) query.append('limit', params.limit.toString());
    const qs = query.toString();
    const res = await request<any>(`/audit${qs ? `?${qs}` : ''}`);
    if (Array.isArray(res)) {
      return res as AuditEvent[];
    }
    if (res && Array.isArray(res.items)) {
      return res.items as AuditEvent[];
    }
    return [];
  },

  // Simulation Controls & Live Demo
  async triggerScenario(
    scenarioKey: string,
    params: {
      order_id?: string;
      customer_name?: string;
      customer_email?: string;
      product_sku?: string;
      product_name?: string;
      order_amount?: number;
      auto_resolve?: boolean;
      is_demo_order?: boolean;
      demo_session_id?: string;
      random_seed?: number;
      random_outcome_override?: string;
    } = {}
  ): Promise<SimulationResult> {
    return request<SimulationResult>('/simulation/trigger-scenario', {
      method: 'POST',
      body: JSON.stringify({
        scenario_key: scenarioKey,
        order_id: params.order_id,
        customer_name: params.customer_name || 'Sarah Connor',
        customer_email: params.customer_email || 'sarah.connor@example.com',
        product_sku: params.product_sku || 'SKU-CYBER-500',
        product_name: params.product_name || 'High-Performance Fiber Gateway',
        order_amount: params.order_amount ?? 199.99,
        auto_resolve: params.auto_resolve ?? true,
        is_demo_order: params.is_demo_order ?? true,
        demo_session_id: params.demo_session_id,
        random_seed: params.random_seed,
        random_outcome_override: params.random_outcome_override
      })
    });
  },

  async resetDemoSession(demoSessionId: string): Promise<{ demo_session_id: string; cleared_orders_count: number; message: string }> {
    return request<{ demo_session_id: string; cleared_orders_count: number; message: string }>('/simulation/reset-demo-session', {
      method: 'POST',
      body: JSON.stringify({ demo_session_id: demoSessionId })
    });
  },

  // Health
  async getHealth(): Promise<{ status: string; database: string }> {
    return request<{ status: string; database: string }>('/health');
  }
};
