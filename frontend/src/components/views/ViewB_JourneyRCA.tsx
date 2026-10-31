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
  ShieldAlert
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
    DELIVERY: '6. Delivery',
    NOTIFICATION: '7. Customer Notification'
  };

  const getStageIndicator = (stage: JourneyStage | undefined) => {
    if (!stage) {
      return {
        icon: <Clock className="w-5 h-5 text-slate-300" />,
        bg: 'bg-slate-100 border-slate-300 text-slate-400',
        statusLabel: 'PENDING'
      };
    }

    switch (stage.status) {
      case 'SUCCESS':
        return {
          icon: <CheckCircle2 className="w-5 h-5 text-white" />,
          bg: 'bg-emerald-500 border-emerald-600 text-white',
          statusLabel: 'SUCCESS'
        };
      case 'PROCESSING':
        return {
          icon: <Loader2 className="w-5 h-5 text-white animate-spin" />,
          bg: 'bg-blue-600 border-blue-700 text-white',
          statusLabel: 'PROCESSING'
        };
      case 'DELAYED':
        return {
          icon: <AlertTriangle className="w-5 h-5 text-white" />,
          bg: 'bg-amber-500 border-amber-600 text-white',
          statusLabel: 'DELAYED'
        };
      case 'FAILED':
        return {
          icon: <XCircle className="w-5 h-5 text-white" />,
          bg: 'bg-rose-500 border-rose-600 text-white',
          statusLabel: 'FAILED'
        };
      default:
        return {
          icon: <Clock className="w-5 h-5 text-slate-400" />,
          bg: 'bg-slate-100 border-slate-300 text-slate-500',
          statusLabel: 'PENDING'
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
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Order Journey & Incident Root Cause Analysis
          </h2>
          <p className="text-xs text-slate-500">
            Chronological 7-stage order lifecycle, telemetry stream, and advisory AI diagnosis.
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
            className="text-xs border border-slate-300 rounded-md py-1.5 px-2.5 bg-slate-50 text-slate-800 font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
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
          <div className="bg-slate-900 text-white p-4 rounded-lg border border-slate-800 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center space-x-4">
              <div>
                <span className="text-[10px] text-slate-400 uppercase font-mono block">
                  Order ID
                </span>
                <span className="text-base font-bold font-mono text-blue-400">
                  {selectedOrder.order_id}
                </span>
              </div>
              <div className="h-8 w-px bg-slate-700" />
              <div>
                <span className="text-[10px] text-slate-400 uppercase block">Customer</span>
                <span className="text-sm font-medium">{selectedOrder.customer_name}</span>
              </div>
              <div className="h-8 w-px bg-slate-700 hidden sm:block" />
              <div className="hidden sm:block">
                <span className="text-[10px] text-slate-400 uppercase block">Product SKU</span>
                <span className="text-sm font-mono text-slate-300">{selectedOrder.product_sku}</span>
              </div>
              <div className="h-8 w-px bg-slate-700 hidden sm:block" />
              <div className="hidden sm:block">
                <span className="text-[10px] text-slate-400 uppercase block">Amount</span>
                <span className="text-sm font-semibold text-emerald-400">
                  ${Number(selectedOrder.order_amount).toFixed(2)}
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-xs text-slate-400">Current Stage:</span>
              <span className="bg-slate-800 border border-slate-700 text-blue-300 text-xs px-2.5 py-1 rounded font-semibold font-mono">
                {selectedOrder.current_stage}
              </span>
              <span className="text-xs text-slate-400">Status:</span>
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
              >
                {selectedOrder.order_status}
              </Badge>
            </div>
          </div>

          {/* Interactive 7-Stage Chronological Order Timeline */}
          <Card
            title={
              <div className="flex items-center justify-between">
                <span>Chronological 7-Stage Order Timeline</span>
                {isLoadingJourney && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
              </div>
            }
            subtitle="Authoritative progress through all sequential fulfillment phases"
          >
            <div className="py-4">
              <div className="relative">
                {/* Timeline connector bar */}
                <div className="absolute top-6 left-6 right-6 h-1 bg-slate-200 -z-0 hidden md:block" />

                {/* 7 Stages Grid */}
                <div className="grid grid-cols-1 md:grid-cols-7 gap-4 relative z-10">
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
                        className="flex flex-col items-center text-center p-3 rounded-lg border border-slate-100 bg-white hover:bg-slate-50 transition"
                      >
                        {/* Circle Badge */}
                        <div
                          className={`w-11 h-11 rounded-full flex items-center justify-center border-2 shadow-sm ${indicator.bg}`}
                        >
                          {indicator.icon}
                        </div>

                        {/* Title */}
                        <div className="mt-2 text-xs font-semibold text-slate-800">
                          {stageDisplayNames[stageKey]}
                        </div>

                        {/* Status Label */}
                        <div className="mt-1">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
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

                        {/* Latency & HTTP Status */}
                        {stage && (
                          <div className="mt-2 text-[11px] text-slate-500 space-y-0.5">
                            {stage.duration_ms > 0 && (
                              <div
                                className={`font-mono ${
                                  stage.duration_ms >= 5000
                                    ? 'text-amber-600 font-bold'
                                    : 'text-slate-500'
                                }`}
                              >
                                {stage.duration_ms >= 1000
                                  ? `${(stage.duration_ms / 1000).toFixed(1)}s`
                                  : `${stage.duration_ms}ms`}
                              </div>
                            )}
                            {stage.http_status && (
                              <div
                                className={`font-mono text-[10px] px-1.5 py-0.2 rounded inline-block ${
                                  stage.http_status === 200
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : stage.http_status === 503
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-rose-100 text-rose-800'
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

          {/* Active Incident & Advisory RCA Diagnostic Grid */}
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
              subtitle="Incident dispatcher detection and state tracking"
            >
              {activeIncident ? (
                <div className="space-y-3.5 text-xs">
                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Incident ID:</span>
                    <span className="font-mono font-bold text-slate-800">
                      {activeIncident.incident_id}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Failure Category:</span>
                    <span className="font-semibold text-slate-800">
                      {activeIncident.failure_category}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Failure Type:</span>
                    <Badge variant="warning">{activeIncident.failure_type}</Badge>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Severity:</span>
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
                    <span className="text-slate-500">Incident Status:</span>
                    <span className="bg-slate-100 text-slate-800 px-2 py-0.5 rounded font-mono font-semibold">
                      {activeIncident.incident_status}
                    </span>
                  </div>

                  <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                    <span className="text-slate-500">Retry Counter:</span>
                    <span className="font-mono text-slate-700">
                      {activeIncident.retry_count} / {activeIncident.max_retries} retries
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Detected Timestamp:</span>
                    <span className="font-mono text-slate-500">
                      {new Date(activeIncident.detected_at).toLocaleString()}
                    </span>
                  </div>

                  {activeIncident.failure_type === 'OUT_OF_STOCK' && (
                    <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-md flex items-center justify-between">
                      <div className="flex items-center space-x-2 text-rose-800">
                        <ShieldAlert className="w-4 h-4 flex-shrink-0" />
                        <span>Requires human operator SKU & warehouse substitution.</span>
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
                  <p className="font-medium text-slate-600">No active incidents for this order.</p>
                  <p className="text-[11px] text-slate-400 mt-1">
                    Order has executed cleanly with zero policy or SLA violations.
                  </p>
                </div>
              )}
            </Card>

            {/* Advisory RCA Diagnostic Card */}
            <Card
              title={
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <BrainCircuit className="w-4 h-4 text-blue-600" />
                    <span>Advisory Root Cause Analysis</span>
                    {isLoadingRCA && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />}
                  </div>
                  {rcaReport && (
                    <div className="flex items-center space-x-1.5">
                      <Bot className="w-3.5 h-3.5 text-blue-500" />
                      <span className="text-[11px] font-mono text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded">
                        {rcaReport.model_source}
                      </span>
                    </div>
                  )}
                </div>
              }
              subtitle="Evidence-grounded diagnostic intelligence (non-authoritative recommendation)"
            >
              {rcaReport ? (
                <div className="space-y-4 text-xs">
                  {/* Evidence Strength & Corroborating Signals */}
                  <div className="flex items-center justify-between bg-slate-50 p-2.5 rounded border border-slate-200">
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

                  {/* Root Cause Explanation */}
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                      Probable Root Cause:
                    </span>
                    <p className="text-slate-800 bg-slate-50 p-2.5 rounded border border-slate-200 leading-relaxed font-sans">
                      {rcaReport.probable_root_cause}
                    </p>
                  </div>

                  {/* Observed Evidence */}
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                      Corroborating Telemetry Evidence:
                    </span>
                    <div className="bg-slate-50 p-2.5 rounded border border-slate-200 font-mono text-[11px] text-slate-700 space-y-1">
                      {Array.isArray(rcaReport.observed_evidence) ? (
                        rcaReport.observed_evidence.map((ev, i) => (
                          <div key={i} className="flex items-start space-x-1.5">
                            <span className="text-blue-500">•</span>
                            <span>{ev}</span>
                          </div>
                        ))
                      ) : (
                        <div>{rcaReport.observed_evidence}</div>
                      )}
                    </div>
                  </div>

                  {/* Recommended Action */}
                  <div className="flex items-center justify-between p-2.5 bg-blue-50 border border-blue-200 rounded">
                    <div>
                      <span className="text-slate-500 font-medium block">
                        Advisory Recommended Action:
                      </span>
                      <span className="font-mono font-bold text-blue-800 text-sm">
                        {rcaReport.recommended_action}
                      </span>
                    </div>
                    <Badge variant="purple">ADVISORY ONLY</Badge>
                  </div>

                  {/* Strict Non-Authoritative Advisory Disclaimer */}
                  <div className="p-2.5 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800 leading-normal flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong>Advisory Notice:</strong> RCA diagnostics represent advisory suggestions
                      and are never executed automatically. System recovery requires deterministic
                      policy authorization (Scenario 1) or human approval (Scenario 3).
                    </div>
                  </div>
                </div>
              ) : activeIncident ? (
                <div className="py-8 text-center">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-500 mx-auto mb-2" />
                  <p className="text-xs text-slate-600 font-medium">Generating advisory RCA diagnosis...</p>
                  <button
                    onClick={() => onAnalyzeRCA(activeIncident.incident_id)}
                    className="mt-3 px-3 py-1.5 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-500 transition"
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

          {/* Telemetry Event Drawer / Accordion */}
          {(() => {
            const telemetryList = journeyData?.raw_events || journeyData?.telemetry_events || [];
            return (
              <Card
                title={
                  <div
                    onClick={() => setTelemetryOpen(!telemetryOpen)}
                    className="flex items-center justify-between cursor-pointer w-full"
                  >
                    <div className="flex items-center space-x-2">
                      <Terminal className="w-4 h-4 text-slate-700" />
                      <span>Telemetry Event Stream ({telemetryList.length} events)</span>
                    </div>
                    <div className="flex items-center space-x-1 text-slate-500 text-xs">
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
                      <div className="max-h-80 overflow-y-auto border border-slate-200 rounded-md divide-y divide-slate-100">
                        {telemetryList.map((evt) => (
                          <div
                            key={evt.event_id}
                            onClick={() => setSelectedTelemetryEvent(evt)}
                            className={`p-3 text-xs flex items-center justify-between hover:bg-slate-50 cursor-pointer transition ${
                              selectedTelemetryEvent?.event_id === evt.event_id ? 'bg-blue-50/70' : ''
                            }`}
                          >
                            <div className="flex items-center space-x-3">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  evt.http_status === 200
                                    ? 'bg-emerald-500'
                                    : evt.http_status === 503
                                    ? 'bg-amber-500'
                                    : 'bg-rose-500'
                                }`}
                              />
                              <span className="font-mono text-slate-400 text-[11px]">
                                {new Date(evt.timestamp).toLocaleTimeString()}
                              </span>
                              <span className="font-semibold text-slate-800">{evt.service_name}</span>
                              <span className="font-mono text-slate-500 text-[11px]">{evt.endpoint}</span>
                            </div>

                            <div className="flex items-center space-x-3">
                              <span className="font-mono text-slate-500 text-[11px]">
                                {evt.duration_ms}ms
                              </span>
                              <span
                                className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                                  evt.http_status === 200
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : evt.http_status === 503
                                    ? 'bg-amber-100 text-amber-800'
                                    : 'bg-rose-100 text-rose-800'
                                }`}
                              >
                                HTTP {evt.http_status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Selected Event Payload Detail */}
                    {selectedTelemetryEvent && (
                      <div className="p-3 bg-slate-900 text-slate-200 rounded-md text-xs font-mono">
                        <div className="flex justify-between items-center mb-2 pb-1 border-b border-slate-800">
                          <span className="font-bold text-blue-400">
                            Event Payload: {selectedTelemetryEvent.event_id}
                          </span>
                          <button
                            onClick={() => setSelectedTelemetryEvent(null)}
                            className="text-slate-400 hover:text-white"
                          >
                            ✕
                          </button>
                        </div>
                        <pre className="overflow-x-auto whitespace-pre-wrap text-[11px]">
                          {selectedTelemetryEvent.payload_summary ||
                            JSON.stringify(selectedTelemetryEvent, null, 2)}
                        </pre>
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
          <p className="text-slate-500 text-sm">
            Please select an order from the list or trigger a scenario to view its journey and RCA.
          </p>
        </Card>
      )}
    </div>
  );
};
