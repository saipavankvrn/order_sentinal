import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  AlertTriangle,
  Bot,
  BrainCircuit,
  Terminal,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ShieldAlert,
  Info
} from 'lucide-react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import {
  Order,
  OrderJourneyData,
  Incident,
  RCAReport,
  JourneyStage,
  TelemetryEvent
} from '../../types';

interface ViewBJourneyRCAProps {
  orders: Order[];
  selectedOrderId: string | null;
  activeOrder?: Order | null;
  onSelectOrder: (orderId: string) => void;
  journeyData: OrderJourneyData | null;
  activeIncident: Incident | null;
  rcaReport: RCAReport | null;
  isLoadingJourney: boolean;
  isLoadingRCA: boolean;
  onAnalyzeRCA: (incidentId: string) => void;
  onNavigateToApprovals: () => void;
}

export const ViewB_JourneyRCA: React.FC<ViewBJourneyRCAProps> = ({
  orders,
  selectedOrderId,
  activeOrder,
  onSelectOrder,
  journeyData,
  activeIncident,
  rcaReport,
  isLoadingJourney,
  isLoadingRCA,
  onAnalyzeRCA,
  onNavigateToApprovals
}) => {
  const [telemetryOpen, setTelemetryOpen] = useState(false);
  const [selectedTelemetryEvent, setSelectedTelemetryEvent] = useState<TelemetryEvent | null>(null);

  const selectedOrder = activeOrder || orders.find((o) => o.order_id === selectedOrderId) || null;

  const stageNamesOrder = [
    'CUSTOMER_ORDER',
    'ADDRESS_VALIDATION',
    'PAYMENT',
    'INVENTORY',
    'FULFILMENT',
    'DELIVERY',
    'NOTIFICATION'
  ];

  const stageDisplayNames: Record<string, string> = {
    CUSTOMER_ORDER: '1. Customer Order',
    ADDRESS_VALIDATION: '2. Address Validation',
    PAYMENT: '3. Payment Processing',
    INVENTORY: '4. Inventory Reservation',
    FULFILMENT: '5. Warehouse Fulfilment',
    DELIVERY: '6. Delivery Dispatch',
    NOTIFICATION: '7. Customer Notification'
  };

  const getStageIndicator = (stage: JourneyStage | undefined) => {
    if (!stage) {
      return {
        icon: <Clock className="w-5 h-5 text-slate-300" />,
        bg: 'bg-slate-50 border-slate-200 text-slate-400',
        statusLabel: 'PENDING'
      };
    }

    switch (stage.status) {
      case 'SUCCESS':
        return {
          icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
          bg: 'bg-emerald-50 border-emerald-200 text-emerald-700',
          statusLabel: 'SUCCESS'
        };
      case 'PROCESSING':
        return {
          icon: <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />,
          bg: 'bg-blue-50 border-blue-200 text-blue-700',
          statusLabel: 'PROCESSING'
        };
      case 'DELAYED':
        return {
          icon: <Clock className="w-5 h-5 text-amber-600" />,
          bg: 'bg-amber-50 border-amber-200 text-amber-800',
          statusLabel: 'DELAYED'
        };
      case 'FAILED':
        return {
          icon: <XCircle className="w-5 h-5 text-rose-600" />,
          bg: 'bg-rose-50 border-rose-200 text-rose-700',
          statusLabel: 'FAILED'
        };
      default:
        return {
          icon: <Clock className="w-5 h-5 text-slate-400" />,
          bg: 'bg-slate-50 border-slate-200 text-slate-500',
          statusLabel: stage.status
        };
    }
  };

  const getEvidenceStrengthVariant = (strength: string) => {
    switch (strength) {
      case 'HIGH':
        return 'success';
      case 'MEDIUM':
        return 'warning';
      case 'LOW':
        return 'neutral';
      default:
        return 'neutral';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Order Selector */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200/90 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Order Journey & Incident Root Cause Analysis
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Sequential 7-stage order lifecycle, telemetry event stream, and advisory AI diagnosis.
          </p>
        </div>

        {/* Order Selector Dropdown */}
        <div className="flex items-center space-x-2">
          <label className="text-xs font-semibold text-slate-600 whitespace-nowrap">
            Selected Order:
          </label>
          <select
            value={selectedOrderId || ''}
            onChange={(e) => onSelectOrder(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg py-1.5 px-3 bg-white text-slate-800 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 shadow-xs"
          >
            {orders.length === 0 ? (
              <option value="">No orders found</option>
            ) : (
              orders.map((o) => (
                <option key={o.order_id} value={o.order_id}>
                  {o.order_id} — {o.order_status} ({o.customer_name})
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {selectedOrder ? (
        <>
          {/* Order Snapshot Banner */}
          <div className="bg-[#0B1120] text-white p-4 rounded-xl border border-slate-800 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-5">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-mono block">
                  Order ID
                </span>
                <span className="text-base font-bold font-mono text-blue-400">
                  {selectedOrder.order_id}
                </span>
              </div>
              <div className="h-8 w-px bg-slate-800" />
              <div>
                <span className="text-[10px] text-slate-400 uppercase block font-mono">Customer</span>
                <span className="text-sm font-semibold text-slate-200">{selectedOrder.customer_name}</span>
              </div>
              <div className="h-8 w-px bg-slate-800 hidden sm:block" />
              <div className="hidden sm:block">
                <span className="text-[10px] text-slate-400 uppercase block font-mono">Product SKU</span>
                <span className="text-sm font-mono text-slate-300">{selectedOrder.product_sku}</span>
              </div>
              <div className="h-8 w-px bg-slate-800 hidden sm:block" />
              <div className="hidden sm:block">
                <span className="text-[10px] text-slate-400 uppercase block font-mono">Total Amount</span>
                <span className="text-sm font-mono font-bold text-emerald-400">
                  ${Number(selectedOrder.order_amount).toFixed(2)}
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-xs text-slate-400 font-mono">Current Stage:</span>
              <span className="bg-slate-900 border border-slate-700 text-blue-300 text-xs px-2.5 py-1 rounded-md font-semibold font-mono">
                {selectedOrder.current_stage}
              </span>
              <span className="text-xs text-slate-400 font-mono">Status:</span>
              <Badge
                variant={
                  selectedOrder.order_status === 'COMPLETED'
                    ? 'success'
                    : selectedOrder.order_status === 'DELAYED'
                    ? 'warning'
                    : selectedOrder.order_status === 'FAILED'
                    ? 'danger'
                    : 'info'
                }
                dot
              >
                {selectedOrder.order_status}
              </Badge>
            </div>
          </div>

          {/* 7-Stage Chronological Order Stepper */}
          <Card
            title={
              <div className="flex items-center justify-between">
                <span>Chronological 7-Stage Order Timeline</span>
                {isLoadingJourney && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
              </div>
            }
            subtitle="Real-time sequential stage progression with latency and HTTP status indicators"
          >
            <div className="py-2">
              <div className="relative">
                {/* 7 Stages Grid */}
                <div className="grid grid-cols-1 md:grid-cols-7 gap-3 relative z-10">
                  {stageNamesOrder.map((stageKey) => {
                    const stage = journeyData?.stages.find(
                      (s) =>
                        s.stage_name === stageKey ||
                        (stageKey === 'PAYMENT' && (s.stage_name === 'PAYMENT_PROCESSING' || s.stage_name === 'PAYMENT')) ||
                        (stageKey === 'INVENTORY' && (s.stage_name === 'INVENTORY_RESERVATION' || s.stage_name === 'INVENTORY')) ||
                        (stageKey === 'FULFILMENT' && (s.stage_name === 'WAREHOUSE_FULFILMENT' || s.stage_name === 'FULFILMENT')) ||
                        (stageKey === 'NOTIFICATION' && (s.stage_name === 'CUSTOMER_NOTIFICATION' || s.stage_name === 'NOTIFICATION'))
                    );
                    const indicator = getStageIndicator(stage);

                    return (
                      <div
                        key={stageKey}
                        className="flex flex-col items-center text-center p-3 rounded-xl border border-slate-100 bg-white hover:border-slate-200 transition shadow-[0_1px_2px_rgba(0,0,0,0.02)]"
                      >
                        {/* Circle Badge */}
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center border ${indicator.bg} shadow-xs`}
                        >
                          {indicator.icon}
                        </div>

                        {/* Stage Name */}
                        <div className="mt-2 text-xs font-semibold text-slate-900 truncate max-w-full">
                          {stageDisplayNames[stageKey]}
                        </div>

                        {/* Status Label */}
                        <div className="mt-1">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider font-mono ${
                              indicator.statusLabel === 'SUCCESS'
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : indicator.statusLabel === 'PROCESSING'
                                ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                : indicator.statusLabel === 'DELAYED'
                                ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                : indicator.statusLabel === 'FAILED'
                                ? 'bg-rose-50 text-rose-700 border border-rose-200'
                                : 'bg-slate-100 text-slate-500'
                            }`}
                          >
                            {indicator.statusLabel}
                          </span>
                        </div>

                        {/* Micro-Telemetry: Latency & HTTP Status */}
                        {stage && (
                          <div className="mt-2 text-[11px] text-slate-500 space-y-1">
                            {stage.duration_ms > 0 && (
                              <div
                                className={`font-mono ${
                                  stage.duration_ms >= 5000
                                    ? 'text-amber-600 font-bold'
                                    : 'text-slate-600 font-medium'
                                }`}
                              >
                                {stage.duration_ms >= 1000
                                  ? `${(stage.duration_ms / 1000).toFixed(1)}s`
                                  : `${stage.duration_ms}ms`}
                              </div>
                            )}
                            {stage.http_status && (
                              <div
                                className={`font-mono text-[10px] px-1.5 py-0.2 rounded font-bold inline-block border ${
                                  stage.http_status === 200
                                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                    : stage.http_status === 503
                                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                                    : 'bg-rose-50 text-rose-700 border-rose-200'
                                }`}
                              >
                                HTTP {stage.http_status}
                              </div>
                            )}
                            {stage.error_message && (
                              <div
                                className="text-[10px] text-rose-600 font-medium truncate max-w-[120px]"
                                title={stage.error_message}
                              >
                                {stage.error_message}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </Card>

          {/* Active Incident & Advisory RCA Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Incident Details Card */}
            <Card
              title={
                <div className="flex items-center space-x-2">
                  <AlertTriangle
                    className={`w-4 h-4 ${
                      activeIncident ? 'text-amber-500' : 'text-slate-400'
                    }`}
                  />
                  <span>Incident Context & Lifecycle</span>
                </div>
              }
              subtitle="Incident detection telemetry and state machine tracking"
            >
              {activeIncident ? (
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Incident ID:</span>
                    <span className="font-mono font-bold text-slate-900">
                      {activeIncident.incident_id}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Failure Category:</span>
                    <span className="font-semibold text-slate-800">
                      {activeIncident.failure_category}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Failure Type:</span>
                    <Badge variant="warning">{activeIncident.failure_type}</Badge>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Severity:</span>
                    <Badge
                      variant={
                        activeIncident.severity === 'HIGH' || activeIncident.severity === 'CRITICAL'
                          ? 'danger'
                          : activeIncident.severity === 'MEDIUM'
                          ? 'warning'
                          : 'neutral'
                      }
                    >
                      {activeIncident.severity}
                    </Badge>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Incident Status:</span>
                    <span className="bg-slate-100 text-slate-800 px-2.5 py-0.5 rounded font-mono font-semibold">
                      {activeIncident.incident_status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500 font-medium">Retry Counter:</span>
                    <span className="font-mono text-slate-700 font-semibold">
                      {activeIncident.retry_count} / {activeIncident.max_retries} attempts
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-500 font-medium">Detected At:</span>
                    <span className="font-mono text-slate-600">
                      {new Date(activeIncident.detected_at).toLocaleString()}
                    </span>
                  </div>

                  {activeIncident.failure_type === 'OUT_OF_STOCK' && (
                    <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-rose-800">
                        <ShieldAlert className="w-4 h-4 flex-shrink-0" />
                        <span className="text-xs">Requires operator SKU & warehouse substitution.</span>
                      </div>
                      <button
                        onClick={onNavigateToApprovals}
                        className="text-xs font-semibold text-rose-700 hover:text-rose-900 underline flex items-center space-x-1"
                      >
                        <span>Go to Queue</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-8 text-center text-slate-400">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                  <p className="font-medium text-slate-700">No active incidents for this order.</p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Order has executed cleanly with zero policy or SLA violations.
                  </p>
                </div>
              )}
            </Card>

            {/* Advisory RCA Card */}
            <Card
              title={
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center space-x-2">
                    <BrainCircuit className="w-4 h-4 text-blue-600" />
                    <span>Advisory Root Cause Analysis</span>
                    {isLoadingRCA && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />}
                  </div>
                  {rcaReport && (
                    <div className="flex items-center space-x-1.5">
                      <Bot className="w-3.5 h-3.5 text-blue-500" />
                      <span className="text-[10px] font-mono font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                        {rcaReport.model_source}
                      </span>
                    </div>
                  )}
                </div>
              }
              subtitle="Evidence-grounded diagnostic intelligence (strictly advisory recommendation)"
            >
              {rcaReport ? (
                <div className="space-y-3.5 text-xs">
                  {/* Evidence Strength & Signals */}
                  <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded-lg border border-slate-200/80">
                    <div className="flex items-center space-x-2">
                      <span className="text-slate-500 font-medium">Evidence Strength:</span>
                      <Badge variant={getEvidenceStrengthVariant(rcaReport.evidence_strength)}>
                        {rcaReport.evidence_strength}
                      </Badge>
                    </div>
                    <div className="text-slate-600">
                      Corroborating Signals: <strong className="font-mono text-slate-900">{rcaReport.corroborating_signals_count}</strong>
                    </div>
                  </div>

                  {/* Root Cause Narrative */}
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
                      Probable Root Cause:
                    </span>
                    <p className="text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 leading-relaxed font-sans text-xs">
                      {rcaReport.probable_root_cause}
                    </p>
                  </div>

                  {/* Observed Evidence */}
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1 font-mono">
                      Corroborating Telemetry Evidence:
                    </span>
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 font-mono text-[11px] text-slate-700 space-y-1">
                      {Array.isArray(rcaReport.observed_evidence) ? (
                        rcaReport.observed_evidence.map((ev, i) => (
                          <div key={i} className="flex items-start space-x-1.5">
                            <span className="text-blue-500 font-bold">•</span>
                            <span>{ev}</span>
                          </div>
                        ))
                      ) : (
                        <div>{rcaReport.observed_evidence}</div>
                      )}
                    </div>
                  </div>

                  {/* Recommended Action */}
                  <div className="flex items-center justify-between p-2.5 bg-blue-50/70 border border-blue-200/80 rounded-lg">
                    <div>
                      <span className="text-slate-500 font-medium block text-[11px]">
                        Advisory Recommended Action:
                      </span>
                      <span className="font-mono font-bold text-blue-900 text-xs">
                        {rcaReport.recommended_action}
                      </span>
                    </div>
                    <Badge variant="purple">ADVISORY ONLY</Badge>
                  </div>

                  {/* Non-Authoritative Advisory Disclaimer */}
                  <div className="p-2.5 bg-amber-50/60 border border-amber-200/80 rounded-lg text-[11px] text-amber-800 leading-normal flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong>Advisory Notice:</strong> AI diagnostics represent advisory guidance
                      and are never executed automatically. System mutations require deterministic
                      policy engine authorization (Scenario 1) or human approval (Scenario 3).
                    </div>
                  </div>
                </div>
              ) : activeIncident ? (
                <div className="py-8 text-center">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto mb-2" />
                  <p className="text-xs text-slate-600 font-medium">Generating advisory RCA diagnosis...</p>
                  <button
                    onClick={() => onAnalyzeRCA(activeIncident.incident_id)}
                    className="mt-3 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-500 transition shadow-xs"
                  >
                    Run RCA Diagnostic
                  </button>
                </div>
              ) : (
                <div className="py-8 text-center text-slate-400">
                  <BrainCircuit className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                  <p className="text-xs font-medium text-slate-500">
                    No active failures to analyze for this order.
                  </p>
                </div>
              )}
            </Card>
          </div>

          {/* Telemetry Stream Drawer */}
          {(() => {
            const telemetryList = journeyData?.raw_events || journeyData?.telemetry_events || [];
            return (
              <Card
                title={
                  <div
                    onClick={() => setTelemetryOpen(!telemetryOpen)}
                    className="flex items-center justify-between cursor-pointer w-full select-none"
                  >
                    <div className="flex items-center space-x-2">
                      <Terminal className="w-4 h-4 text-slate-700" />
                      <span>Telemetry Event Stream ({telemetryList.length} hops)</span>
                    </div>
                    <div className="flex items-center space-x-1 text-slate-500 text-xs font-medium">
                      <span>{telemetryOpen ? 'Collapse' : 'Expand Stream'}</span>
                      {telemetryOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </div>
                  </div>
                }
                subtitle="Raw microservice emission telemetry with timestamps, durations, and HTTP payloads"
              >
                {telemetryOpen && (
                  <div className="space-y-4">
                    {telemetryList.length === 0 ? (
                      <p className="text-xs text-slate-400 py-4 text-center">
                        No telemetry events recorded for this order yet.
                      </p>
                    ) : (
                      <div className="max-h-80 overflow-y-auto border border-slate-200/80 rounded-lg divide-y divide-slate-100">
                        {telemetryList.map((evt) => (
                          <div
                            key={evt.event_id}
                            onClick={() => setSelectedTelemetryEvent(evt)}
                            className={`p-3 text-xs flex items-center justify-between hover:bg-slate-50 cursor-pointer transition ${
                              selectedTelemetryEvent?.event_id === evt.event_id ? 'bg-blue-50/60' : ''
                            }`}
                          >
                            <div className="flex items-center space-x-3">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                                  evt.http_status === 200
                                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                    : evt.http_status === 503
                                    ? 'bg-amber-50 text-amber-700 border border-amber-200'
                                    : 'bg-rose-50 text-rose-700 border border-rose-200'
                                }`}
                              >
                                HTTP {evt.http_status}
                              </span>
                              <span className="font-semibold text-slate-900">{evt.stage}</span>
                              <span className="font-mono text-slate-500 text-[11px]">{evt.endpoint}</span>
                            </div>

                            <div className="flex items-center space-x-3 font-mono text-[11px] text-slate-500">
                              <span>{evt.duration_ms}ms</span>
                              <span>{new Date(evt.timestamp).toLocaleTimeString()}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {selectedTelemetryEvent && (
                      <div className="p-3 bg-slate-900 text-slate-200 rounded-lg font-mono text-[11px] space-y-2 border border-slate-800">
                        <div className="flex items-center justify-between text-slate-400 pb-1 border-b border-slate-800">
                          <span>Event Payload: {selectedTelemetryEvent.event_id}</span>
                          <span>{selectedTelemetryEvent.service_name}</span>
                        </div>
                        <div className="text-blue-300">
                          {selectedTelemetryEvent.http_method} {selectedTelemetryEvent.endpoint} &rarr; HTTP {selectedTelemetryEvent.http_status} ({selectedTelemetryEvent.duration_ms}ms)
                        </div>
                        {selectedTelemetryEvent.error_message && (
                          <div className="text-rose-400">
                            Error: {selectedTelemetryEvent.error_message}
                          </div>
                        )}
                        {selectedTelemetryEvent.payload_summary && (
                          <pre className="text-slate-300 bg-slate-950 p-2 rounded overflow-x-auto text-[10px]">
                            {typeof selectedTelemetryEvent.payload_summary === 'string'
                              ? selectedTelemetryEvent.payload_summary
                              : JSON.stringify(selectedTelemetryEvent.payload_summary, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })()}
        </>
      ) : (
        <Card className="text-center py-12">
          <Info className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-800">No Order Selected</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Select an order from the dropdown above or navigate from the Operational Dashboard to inspect its 7-stage journey and RCA.
          </p>
        </Card>
      )}
    </div>
  );
};
