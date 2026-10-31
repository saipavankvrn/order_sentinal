export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message: string;
  timestamp: string;
}

export type OrderStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'DELAYED' | 'FAILED' | 'CANCELLED';

export interface Order {
  order_id: string;
  correlation_id: string;
  customer_id: string;
  customer_name: string;
  customer_email: string;
  product_sku: string;
  product_name: string;
  order_amount: number;
  currency: string;
  current_stage: string;
  order_status: OrderStatus;
  payment_status: string;
  inventory_status: string;
  fulfilment_status: string;
  is_demo_order?: boolean;
  demo_session_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrderListResponse {
  total: number;
  page: number;
  limit: number;
  skip?: number;
  items: Order[];
}

export type StageStatus = 'SUCCESS' | 'FAILED' | 'DELAYED' | 'PROCESSING' | 'PENDING';

export interface JourneyStage {
  stage_name: string;
  display_name: string;
  status: StageStatus;
  duration_ms: number;
  http_status?: number | null;
  timestamp?: string | null;
  error_message?: string | null;
}

export interface TelemetryEvent {
  event_id: string;
  order_id: string;
  correlation_id: string;
  stage: string;
  service_name: string;
  endpoint: string;
  http_method: string;
  http_status: number;
  duration_ms: number;
  event_status: string;
  payload_summary?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  timestamp: string;
}

export interface OrderJourneyData {
  order_id: string;
  correlation_id?: string;
  current_stage: string;
  order_status: OrderStatus;
  stages: JourneyStage[];
  raw_events?: TelemetryEvent[];
  telemetry_events?: TelemetryEvent[];
}

export type IncidentStatus =
  | 'DETECTED'
  | 'ANALYZING'
  | 'PENDING_APPROVAL'
  | 'RESOLVING'
  | 'RESOLVED'
  | 'ESCALATED'
  | 'REJECTED';

export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Incident {
  incident_id: string;
  order_id: string;
  stage: string;
  service_name: string;
  failure_category: string;
  failure_type: string;
  incident_status: IncidentStatus;
  severity: SeverityLevel;
  retry_count: number;
  max_retries: number;
  detected_at: string;
  resolved_at?: string | null;
}

export interface IncidentDetail {
  incident: Incident;
  rca_report?: RCAReport | null;
  order_id: string;
  correlation_id: string;
}

export interface RCAReport {
  rca_id: string;
  incident_id: string;
  failure_category: string;
  affected_service: string;
  observed_evidence: string[] | string;
  probable_root_cause: string;
  evidence_strength: 'HIGH' | 'MEDIUM' | 'LOW';
  corroborating_signals_count: number;
  recommended_action: string;
  risk_level: SeverityLevel;
  explanation: string;
  model_source: string;
  prompt_tokens: number;
  created_at: string;
}

export interface OperatorApproval {
  approval_id: string;
  incident_id: string;
  order_id: string;
  selected_action: string;
  action_parameters?: string | Record<string, any> | null;
  risk_level: SeverityLevel;
  decision: 'PENDING' | 'APPROVED' | 'REJECTED';
  operator_id?: string | null;
  operator_name?: string | null;
  operator_notes?: string | null;
  requested_at: string;
  decided_at?: string | null;
  order?: Order;
}

export interface AuditEvent {
  log_id: number;
  correlation_id: string;
  order_id?: string | null;
  incident_id?: string | null;
  event_type: string;
  actor_type: string;
  actor_id: string;
  summary: string;
  metadata_json?: string | null;
  timestamp: string;
}

export interface AuditListResponse {
  total: number;
  page: number;
  limit: number;
  items: AuditEvent[];
}

export interface AnalyticsMetrics {
  total_orders: number;
  completed_orders: number;
  failed_orders: number;
  delayed_orders: number;
  pending_approvals: number;
  in_progress_orders: number;
}

export interface FailureCategoryCount {
  category: string;
  count: number;
}

export interface FailureDistribution {
  categories: FailureCategoryCount[];
  total_incidents: number;
  distribution_map: Record<string, number>;
}

export interface SimulationResult {
  scenario_key: string;
  order: Order;
  incident?: Incident | null;
  rca?: RCAReport | null;
  approval?: OperatorApproval | null;
  resolution?: any;
  audit_events_count?: number;
  selected_outcome?: string;
  outcome_reason?: string;
  demo_probabilities?: Record<string, number>;
  operator_alert?: any;
  events?: TelemetryEvent[];
  message?: string;
}

