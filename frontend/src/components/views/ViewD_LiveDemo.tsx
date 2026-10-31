import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Play,
  RotateCw,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  Clock,
  Loader2,
  ShieldAlert,
  Terminal,
  Layers,
  RotateCcw,
  Check,
  RefreshCw,
  ChevronRight,
  Package,
  Bot
} from 'lucide-react';
import { Card } from '../common/Card';
import { api } from '../../api/client';
import {
  Order,
  OrderJourneyData,
  Incident,
  RCAReport,
  OperatorApproval,
  AuditEvent,
  JourneyStage,
  SimulationResult
} from '../../types';

interface ViewDLiveDemoProps {
  demoSessionId: string;
  onResetSession: () => Promise<void>;
  onSelectOrder: (orderId: string) => void;
  activeOrder: Order | null;
  journeyData: OrderJourneyData | null;
  activeIncident: Incident | null;
  rcaReport: RCAReport | null;
  isLoadingJourney: boolean;
  onRefresh: () => void;
  onScenarioTriggered: (result: SimulationResult) => void;
  onDecideApproval: (
    approvalId: string,
    decision: 'APPROVED' | 'REJECTED',
    substituteSku: string,
    alternateHub: string,
    operatorId: string,
    operatorNotes: string
  ) => Promise<void>;
}

export const ViewD_LiveDemo: React.FC<ViewDLiveDemoProps> = ({
  demoSessionId,
  onResetSession,
  onSelectOrder,
  activeOrder,
  journeyData,
  activeIncident,
  rcaReport,
  isLoadingJourney,
  onRefresh,
  onScenarioTriggered,
  onDecideApproval
}) => {
  // Demo Order Form State
  const [orderIdInput, setOrderIdInput] = useState('');
  const [customerName, setCustomerName] = useState('Alex Mercer');
  const [productSku, setProductSku] = useState('SKU-CYBER-500');
  const [orderAmount, setOrderAmount] = useState(199.99);
  const [selectedScenario, setSelectedScenario] = useState<string>('SCENARIO_1_HTTP_503_SELF_HEAL');
  const [autoResolve, setAutoResolve] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Random Mode Outcome Display
  const [randomOutcomeInfo, setRandomOutcomeInfo] = useState<{
    outcome: string;
    reason: string;
  } | null>(null);

  // Session Orders list
  const [sessionOrders, setSessionOrders] = useState<Order[]>([]);
  const [isLoadingSessionOrders, setIsLoadingSessionOrders] = useState(false);

  // Timeline events for active order
  const [orderAuditLogs, setOrderAuditLogs] = useState<AuditEvent[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);

  // In-line approval state for active order
  const [inlineApproval, setInlineApproval] = useState<OperatorApproval | null>(null);
  const [substituteSku, setSubstituteSku] = useState('SKU-CYBER-500-ALT');
  const [alternateHub, setAlternateHub] = useState('HUB-EAST-02');
  const [operatorNotes, setOperatorNotes] = useState('Verified physical stock available at East hub.');
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  // Confirm Reset modal
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  // Generate unique order ID
  const generateNewOrderId = () => {
    const rand = Math.random().toString(36).substring(2, 8).toUpperCase();
    return `ORD-LIVE-${rand}`;
  };

  useEffect(() => {
    if (!orderIdInput) {
      setOrderIdInput(generateNewOrderId());
    }
  }, []);

  // Fetch session orders
  const fetchSessionOrders = async () => {
    if (!demoSessionId) return;
    setIsLoadingSessionOrders(true);
    try {
      const res = await api.getOrders({
        demo_session_id: demoSessionId,
        is_demo: true,
        limit: 50
      });
      setSessionOrders(res.items || []);
    } catch {
      // safe fallback
    } finally {
      setIsLoadingSessionOrders(false);
    }
  };

  useEffect(() => {
    fetchSessionOrders();
  }, [demoSessionId, activeOrder?.order_id]);

  // Fetch audit logs and linked approvals for active order
  useEffect(() => {
    if (!activeOrder?.order_id) {
      setOrderAuditLogs([]);
      setInlineApproval(null);
      return;
    }

    const loadOrderContext = async () => {
      setIsLoadingAudit(true);
      try {
        const [auditRes, approvalsRes] = await Promise.all([
          api.getAuditLogs({ order_id: activeOrder.order_id, limit: 50 }).catch(() => []),
          api.getPendingApprovals({ demo_session_id: demoSessionId }).catch(() => [])
        ]);
        setOrderAuditLogs(auditRes || []);

        const foundApp = approvalsRes.find((a) => a.order_id === activeOrder.order_id);
        setInlineApproval(foundApp || null);
      } catch {
        // safe fallback
      } finally {
        setIsLoadingAudit(false);
      }
    };

    loadOrderContext();
  }, [activeOrder?.order_id, activeOrder?.order_status, activeIncident?.incident_status, demoSessionId]);

  // Handle Order Submission
  const handleLaunchOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    const freshOrderId = orderIdInput.trim() || generateNewOrderId();
    setIsSubmitting(true);
    setFormError(null);
    setRandomOutcomeInfo(null);

    try {
      const result = await api.triggerScenario(selectedScenario, {
        order_id: freshOrderId,
        customer_name: customerName,
        customer_email: `${customerName.toLowerCase().replace(/\s+/g, '.')}@example.com`,
        product_sku: productSku,
        product_name: 'High-Performance Fiber Gateway',
        order_amount: orderAmount,
        auto_resolve: autoResolve,
        is_demo_order: true,
        demo_session_id: demoSessionId
      });

      if (result.selected_outcome && result.outcome_reason) {
        setRandomOutcomeInfo({
          outcome: result.selected_outcome,
          reason: result.outcome_reason
        });
      }

      // Pre-generate next unique ID for subsequent order
      setOrderIdInput(generateNewOrderId());

      onScenarioTriggered(result);
      fetchSessionOrders();
    } catch (err: any) {
      setFormError(err?.message || 'Failed to trigger live test order.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle In-line Approval decision
  const handleInlineDecision = async (decision: 'APPROVED' | 'REJECTED') => {
    if (!inlineApproval || isSubmittingDecision) return;
    setIsSubmittingDecision(true);
    try {
      await onDecideApproval(
        inlineApproval.approval_id,
        decision,
        substituteSku,
        alternateHub,
        'OP-DEMO-LEAD',
        operatorNotes
      );
      setInlineApproval(null);
      onRefresh();
    } catch (err: any) {
      alert(`Approval decision failed: ${err?.message || err}`);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  // Handle Safe Reset
  const handleConfirmReset = async () => {
    setIsResetting(true);
    try {
      await onResetSession();
      setShowResetConfirm(false);
      setSessionOrders([]);
      setRandomOutcomeInfo(null);
      setOrderIdInput(generateNewOrderId());
    } catch (err: any) {
      alert(`Failed to reset demo session: ${err?.message || err}`);
    } finally {
      setIsResetting(false);
    }
  };

  // Stage mapping helper
  const stageNamesOrder = [
    'CUSTOMER_ORDER',
    'ADDRESS_VALIDATION',
    'PAYMENT',
    'INVENTORY',
    'FULFILMENT',
    'DELIVERY',
    'NOTIFICATION'
  ];

  const stageLabels: Record<string, string> = {
    CUSTOMER_ORDER: '1. Customer Order',
    ADDRESS_VALIDATION: '2. Address Validation',
    PAYMENT: '3. Payment Processing',
    INVENTORY: '4. Inventory Reservation',
    FULFILMENT: '5. Warehouse Fulfilment',
    DELIVERY: '6. Delivery Dispatch',
    NOTIFICATION: '7. Customer Notification'
  };

  const getStageItem = (stageName: string): JourneyStage | undefined => {
    if (!journeyData?.stages) return undefined;
    return journeyData.stages.find(
      (s) => s.stage_name === stageName || s.stage_name?.toUpperCase() === stageName
    );
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Session Context & Safe Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 sm:p-5 text-white shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start space-x-3">
            <div className="p-2.5 bg-blue-600/20 border border-blue-500/30 rounded-lg text-blue-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base font-bold tracking-tight text-white">
                  Live Demonstration Workspace
                </h2>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500 text-slate-950 uppercase tracking-wider">
                  Live Demo Mode
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Active Session Token:{' '}
                <span className="font-mono text-blue-300 font-semibold">{demoSessionId}</span>
                {' · '}
                <span className="text-slate-300">
                  {sessionOrders.length} demonstration order(s) created
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onRefresh}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 rounded transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Status</span>
            </button>
            <button
              onClick={() => setShowResetConfirm(true)}
              disabled={sessionOrders.length === 0}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-rose-950/70 hover:bg-rose-900/80 text-rose-300 border border-rose-800 rounded text-xs font-medium transition disabled:opacity-40"
              title="Clears ONLY orders tagged with this active demo session token. Historical database records are preserved."
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Demo Session</span>
            </button>
          </div>
        </div>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6 shadow-2xl border border-slate-200 animate-in fade-in duration-150">
            <div className="flex items-center space-x-3 text-rose-600 mb-3">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-slate-900">Reset Demo Session?</h3>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">
              This action will purge only the{' '}
              <strong className="text-slate-900 font-semibold">
                {sessionOrders.length} live demonstration order(s)
              </strong>{' '}
              created during session <code className="font-mono text-xs text-blue-700">{demoSessionId}</code>.
            </p>
            <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded text-xs text-emerald-800 flex items-center space-x-2">
              <Check className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              <span>
                <strong>Zero Data Loss Guarantee:</strong> All pre-existing historical orders, incidents, and approvals remain safely intact.
              </span>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowResetConfirm(false)}
                disabled={isResetting}
                className="px-4 py-2 border border-slate-300 rounded text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReset}
                disabled={isResetting}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold transition flex items-center space-x-1.5"
              >
                {isResetting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Purge Session Records</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Form on Left, Active Tracker on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Order Creation Card */}
        <div className="lg:col-span-5 space-y-6">
          <Card className="p-5 border-slate-200 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div className="flex items-center space-x-2">
                <Package className="w-4 h-4 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-sm">Create Live Test Order</h3>
              </div>
              <span className="text-[11px] font-mono text-slate-400">Step 1 of Demonstration</span>
            </div>

            <form onSubmit={handleLaunchOrder} className="space-y-4">
              {/* Order ID with auto-generate button */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-700">Order ID (Auto-Generated)</label>
                  <button
                    type="button"
                    onClick={() => setOrderIdInput(generateNewOrderId())}
                    className="text-[11px] text-blue-600 hover:text-blue-800 font-medium flex items-center space-x-1"
                  >
                    <RefreshCw className="w-3 h-3" />
                    <span>Regenerate ID</span>
                  </button>
                </div>
                <input
                  type="text"
                  value={orderIdInput}
                  onChange={(e) => setOrderIdInput(e.target.value)}
                  className="w-full font-mono text-xs px-3 py-2 border border-slate-300 rounded bg-slate-50 text-slate-800 focus:bg-white focus:ring-1 focus:ring-blue-500"
                  required
                />
              </div>

              {/* Customer & Amount details */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Customer Name</label>
                  <input
                    type="text"
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded text-slate-800 focus:ring-1 focus:ring-blue-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Amount (USD)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={orderAmount}
                    onChange={(e) => setOrderAmount(parseFloat(e.target.value) || 0)}
                    className="w-full text-xs px-3 py-2 border border-slate-300 rounded text-slate-800 focus:ring-1 focus:ring-blue-500"
                    required
                  />
                </div>
              </div>

              {/* Product SKU */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Product SKU</label>
                <input
                  type="text"
                  value={productSku}
                  onChange={(e) => setProductSku(e.target.value)}
                  className="w-full font-mono text-xs px-3 py-2 border border-slate-300 rounded text-slate-800 focus:ring-1 focus:ring-blue-500"
                  required
                />
              </div>

              {/* Scenario Selector Radio Cards */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Select Simulation Scenario
                </label>
                <div className="space-y-2">
                  {/* Scenario 0 */}
                  <label
                    className={`flex items-start p-2.5 rounded-lg border cursor-pointer transition ${
                      selectedScenario === 'SCENARIO_0_CLEAN_RUN'
                        ? 'border-emerald-500 bg-emerald-50/50 ring-1 ring-emerald-400'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="scenario"
                      value="SCENARIO_0_CLEAN_RUN"
                      checked={selectedScenario === 'SCENARIO_0_CLEAN_RUN'}
                      onChange={(e) => setSelectedScenario(e.target.value)}
                      className="mt-0.5 text-emerald-600 focus:ring-emerald-500"
                    />
                    <div className="ml-2.5">
                      <div className="flex items-center space-x-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-xs font-bold text-slate-900">Scenario 0: Normal Order</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Clean 7-stage baseline journey. Executes without injected faults to COMPLETED.
                      </p>
                    </div>
                  </label>

                  {/* Scenario 1 */}
                  <label
                    className={`flex items-start p-2.5 rounded-lg border cursor-pointer transition ${
                      selectedScenario === 'SCENARIO_1_HTTP_503_SELF_HEAL'
                        ? 'border-blue-500 bg-blue-50/50 ring-1 ring-blue-400'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="scenario"
                      value="SCENARIO_1_HTTP_503_SELF_HEAL"
                      checked={selectedScenario === 'SCENARIO_1_HTTP_503_SELF_HEAL'}
                      onChange={(e) => setSelectedScenario(e.target.value)}
                      className="mt-0.5 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="ml-2.5">
                      <div className="flex items-center space-x-1.5">
                        <RotateCw className="w-3.5 h-3.5 text-blue-600" />
                        <span className="text-xs font-bold text-slate-900">Scenario 1: HTTP 503 API Failure</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Transient error at Inventory. Advisory RCA generated, policy retry authorized, inventory state verified, auto-healed.
                      </p>
                    </div>
                  </label>

                  {/* Scenario 2 */}
                  <label
                    className={`flex items-start p-2.5 rounded-lg border cursor-pointer transition ${
                      selectedScenario === 'SCENARIO_2_SLA_DELAY'
                        ? 'border-amber-500 bg-amber-50/50 ring-1 ring-amber-400'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="scenario"
                      value="SCENARIO_2_SLA_DELAY"
                      checked={selectedScenario === 'SCENARIO_2_SLA_DELAY'}
                      onChange={(e) => setSelectedScenario(e.target.value)}
                      className="mt-0.5 text-amber-600 focus:ring-amber-500"
                    />
                    <div className="ml-2.5">
                      <div className="flex items-center space-x-1.5">
                        <Clock className="w-3.5 h-3.5 text-amber-600" />
                        <span className="text-xs font-bold text-slate-900">Scenario 2: SLA Delay (Alert)</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        10,000ms latency. SLA breach detected (+5,000ms). Order marked DELAYED. Operator alert issued. Zero auto-cancellation.
                      </p>
                    </div>
                  </label>

                  {/* Scenario 3 */}
                  <label
                    className={`flex items-start p-2.5 rounded-lg border cursor-pointer transition ${
                      selectedScenario === 'SCENARIO_3_HARD_REJECTION'
                        ? 'border-rose-500 bg-rose-50/50 ring-1 ring-rose-400'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="scenario"
                      value="SCENARIO_3_HARD_REJECTION"
                      checked={selectedScenario === 'SCENARIO_3_HARD_REJECTION'}
                      onChange={(e) => setSelectedScenario(e.target.value)}
                      className="mt-0.5 text-rose-600 focus:ring-rose-500"
                    />
                    <div className="ml-2.5">
                      <div className="flex items-center space-x-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-rose-600" />
                        <span className="text-xs font-bold text-slate-900">Scenario 3: Out-of-Stock (HITL Approval)</span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        HTTP 422 permanent business rejection. High-risk advisory RCA. Queued for operator authorization and SKU reallocation.
                      </p>
                    </div>
                  </label>

                  {/* Option 5: Random Demo Mode */}
                  <label
                    className={`flex items-start p-2.5 rounded-lg border cursor-pointer transition ${
                      selectedScenario === 'RANDOM'
                        ? 'border-purple-500 bg-purple-50/50 ring-1 ring-purple-400'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="scenario"
                      value="RANDOM"
                      checked={selectedScenario === 'RANDOM'}
                      onChange={(e) => setSelectedScenario(e.target.value)}
                      className="mt-0.5 text-purple-600 focus:ring-purple-500"
                    />
                    <div className="ml-2.5">
                      <div className="flex items-center space-x-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                        <span className="text-xs font-bold text-slate-900">🎲 Random Demo Mode</span>
                        <span className="text-[10px] bg-purple-100 text-purple-800 px-1.5 py-0.2 rounded font-bold">
                          PROBABILISTIC
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        Live random outcome based on production demo distribution:
                      </p>
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        <span className="text-[10px] bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded font-mono">
                          50% Normal
                        </span>
                        <span className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-mono">
                          25% 503 Retry
                        </span>
                        <span className="text-[10px] bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded font-mono">
                          15% SLA Delay
                        </span>
                        <span className="text-[10px] bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded font-mono">
                          10% Rejection
                        </span>
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Auto Resolve Toggle */}
              {selectedScenario === 'SCENARIO_1_HTTP_503_SELF_HEAL' && (
                <div className="flex items-center justify-between p-2.5 bg-slate-50 border border-slate-200 rounded">
                  <div>
                    <span className="text-xs font-semibold text-slate-800 block">Auto-Execute Self-Healing</span>
                    <span className="text-[11px] text-slate-500">
                      Executes policy-authorized idempotent retry and downstream verification immediately
                    </span>
                  </div>
                  <input
                    type="checkbox"
                    checked={autoResolve}
                    onChange={(e) => setAutoResolve(e.target.checked)}
                    className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4 cursor-pointer"
                  />
                </div>
              )}

              {formError && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-700 rounded text-xs flex items-center space-x-1.5">
                  <XCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded font-bold text-xs shadow transition flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Launching Order Journey...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Launch Live Test Order</span>
                  </>
                )}
              </button>
            </form>
          </Card>

          {/* Session Orders Drawer List */}
          <Card className="p-4 border-slate-200 shadow-sm">
            <div className="flex items-center justify-between pb-2.5 border-b border-slate-100 mb-3">
              <div className="flex items-center space-x-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <h4 className="text-xs font-bold text-slate-800">
                  Live Orders in Current Session ({sessionOrders.length})
                </h4>
              </div>
              {isLoadingSessionOrders && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />}
            </div>

            {sessionOrders.length === 0 ? (
              <p className="text-xs text-slate-400 py-3 text-center italic">
                No orders submitted yet in this session. Click "Launch Live Test Order" above to begin.
              </p>
            ) : (
              <div className="space-y-1.5 max-h-52 overflow-y-auto pr-1">
                {sessionOrders.map((ord) => {
                  const isSelected = activeOrder?.order_id === ord.order_id;
                  return (
                    <button
                      key={ord.order_id}
                      onClick={() => onSelectOrder(ord.order_id)}
                      className={`w-full text-left p-2 rounded border text-xs flex items-center justify-between transition ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50 text-blue-900 font-semibold'
                          : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-[11px]">{ord.order_id}</span>
                        <span className="text-[11px] text-slate-500">{ord.customer_name}</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <span
                          className={`text-[10px] px-1.5 py-0.2 rounded font-bold uppercase ${
                            ord.order_status === 'COMPLETED'
                              ? 'bg-emerald-100 text-emerald-800'
                              : ord.order_status === 'DELAYED'
                              ? 'bg-amber-100 text-amber-800'
                              : ord.order_status === 'FAILED'
                              ? 'bg-rose-100 text-rose-800'
                              : 'bg-blue-100 text-blue-800'
                          }`}
                        >
                          {ord.order_status}
                        </span>
                        <ChevronRight className="w-3 h-3 text-slate-400" />
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Right Column (7 cols): Active Live Order Journey Tracker & Timeline */}
        <div className="lg:col-span-7 space-y-6">
          {!activeOrder ? (
            <Card className="p-12 text-center border-dashed border-2 border-slate-300">
              <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h4 className="text-sm font-bold text-slate-700">No Live Order Selected</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                Configure parameters on the left and click <strong>"Launch Live Test Order"</strong> to witness fresh multi-hop journey progression and recovery in real-time.
              </p>
            </Card>
          ) : (
            <>
              {/* Active Order Header */}
              <Card className="p-4 border-slate-200 shadow-sm bg-gradient-to-r from-slate-900 to-slate-800 text-white">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs uppercase tracking-wider text-slate-400 font-bold">
                        Live Monitored Order:
                      </span>
                      <span className="font-mono text-sm font-bold text-blue-300">
                        {activeOrder.order_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-300 mt-1 flex items-center space-x-2">
                      <span>{activeOrder.customer_name}</span>
                      <span>·</span>
                      <span className="font-mono text-slate-400">{activeOrder.product_sku}</span>
                      <span>·</span>
                      <span>${Number(activeOrder.order_amount).toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-xs px-2.5 py-1 rounded font-bold uppercase tracking-wider ${
                        activeOrder.order_status === 'COMPLETED'
                          ? 'bg-emerald-500 text-slate-950'
                          : activeOrder.order_status === 'DELAYED'
                          ? 'bg-amber-500 text-slate-950'
                          : activeOrder.order_status === 'FAILED'
                          ? 'bg-rose-500 text-white'
                          : 'bg-blue-500 text-white animate-pulse'
                      }`}
                    >
                      {activeOrder.order_status}
                    </span>
                    <span className="text-xs bg-slate-800 text-slate-300 px-2 py-1 rounded font-mono">
                      Stage: {activeOrder.current_stage}
                    </span>
                  </div>
                </div>

                {/* Random Outcome Banner if triggered */}
                {randomOutcomeInfo && (
                  <div className="mt-3 p-2.5 bg-purple-950/80 border border-purple-700/60 rounded text-xs text-purple-200 flex items-center space-x-2">
                    <Sparkles className="w-4 h-4 text-purple-400 flex-shrink-0" />
                    <div>
                      <span className="font-bold text-white uppercase mr-1">
                        🎲 Random Outcome:
                      </span>
                      <span>{randomOutcomeInfo.reason}</span>
                    </div>
                  </div>
                )}
              </Card>

              {/* 7-Stage Live Progression Stepper */}
              <Card className="p-4 border-slate-200 shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                  <div className="flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-blue-600" />
                    <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
                      7-Stage Progression Stepper
                    </h3>
                  </div>
                  <div className="flex items-center space-x-2">
                    {isLoadingJourney && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />}
                    <span className="text-[11px] text-slate-400 font-mono">
                      Polling interval: 3.0s
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  {stageNamesOrder.map((stageName) => {
                    const stageItem = getStageItem(stageName);
                    const isSuccess = stageItem?.status === 'SUCCESS';
                    const isDelayed = stageItem?.status === 'DELAYED';
                    const isFailed = stageItem?.status === 'FAILED';
                    const isProcessing =
                      stageItem?.status === 'PROCESSING' ||
                      (activeOrder.current_stage === stageName && activeOrder.order_status === 'PROCESSING' && !isFailed);

                    let bgClass = 'bg-slate-50 border-slate-200 text-slate-400';
                    let icon = <Clock className="w-4 h-4 text-slate-400" />;

                    if (isSuccess) {
                      bgClass = 'bg-emerald-50/70 border-emerald-300 text-emerald-900';
                      icon = <CheckCircle2 className="w-4 h-4 text-emerald-600" />;
                    } else if (isProcessing) {
                      bgClass = 'bg-blue-50 border-blue-300 text-blue-900 ring-1 ring-blue-400';
                      icon = <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />;
                    } else if (isDelayed) {
                      bgClass = 'bg-amber-50 border-amber-300 text-amber-900';
                      icon = <AlertTriangle className="w-4 h-4 text-amber-600" />;
                    } else if (isFailed) {
                      bgClass = 'bg-rose-50 border-rose-300 text-rose-900';
                      icon = <XCircle className="w-4 h-4 text-rose-600" />;
                    }

                    return (
                      <div
                        key={stageName}
                        className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition ${bgClass}`}
                      >
                        <div className="flex items-center space-x-3">
                          <span className="flex-shrink-0">{icon}</span>
                          <div>
                            <span className="font-bold text-slate-900 block">
                              {stageLabels[stageName]}
                            </span>
                            {stageItem?.error_message && (
                              <span className="text-[11px] text-rose-600 block mt-0.5">
                                {stageItem.error_message}
                              </span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          {stageItem?.http_status && (
                            <span
                              className={`px-1.5 py-0.2 rounded font-mono text-[10px] font-bold ${
                                stageItem.http_status === 200
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : stageItem.http_status === 503
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-rose-100 text-rose-800'
                              }`}
                            >
                              HTTP {stageItem.http_status}
                            </span>
                          )}

                          {stageItem?.duration_ms !== undefined && (
                            <span className="font-mono text-[11px] text-slate-600">
                              {stageItem.duration_ms}ms
                            </span>
                          )}

                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              isSuccess
                                ? 'bg-emerald-600 text-white'
                                : isProcessing
                                ? 'bg-blue-600 text-white'
                                : isDelayed
                                ? 'bg-amber-600 text-white'
                                : isFailed
                                ? 'bg-rose-600 text-white'
                                : 'bg-slate-200 text-slate-600'
                            }`}
                          >
                            {isProcessing
                              ? 'PROCESSING'
                              : stageItem?.status || 'PENDING'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Card>

              {/* In-Line Operator Human-in-the-Loop Action for Scenario 3 */}
              {inlineApproval && (
                <Card className="p-4 border-rose-300 bg-rose-50/60 shadow-sm animate-in fade-in">
                  <div className="flex items-center justify-between pb-2 border-b border-rose-200 mb-3">
                    <div className="flex items-center space-x-2 text-rose-900">
                      <ShieldAlert className="w-4 h-4 text-rose-600" />
                      <h4 className="font-bold text-xs uppercase tracking-wider">
                        Human-in-the-Loop Operator Authorization Required
                      </h4>
                    </div>
                    <span className="text-[10px] font-mono bg-rose-200 text-rose-900 px-1.5 py-0.2 rounded font-bold">
                      {inlineApproval.approval_id}
                    </span>
                  </div>

                  <p className="text-xs text-rose-800 leading-relaxed mb-3">
                    Inventory reservation failed due to <strong>HTTP 422 Out-of-Stock</strong>. Permanent business rejections strictly prohibit automatic retries. Authorize SKU substitution and warehouse reallocation below:
                  </p>

                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 mb-1">
                        Substitute SKU (Verified)
                      </label>
                      <input
                        type="text"
                        value={substituteSku}
                        onChange={(e) => setSubstituteSku(e.target.value)}
                        className="w-full text-xs font-mono px-2.5 py-1.5 border border-slate-300 rounded bg-white"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-bold text-slate-700 mb-1">
                        Alternate Hub
                      </label>
                      <input
                        type="text"
                        value={alternateHub}
                        onChange={(e) => setAlternateHub(e.target.value)}
                        className="w-full text-xs font-mono px-2.5 py-1.5 border border-slate-300 rounded bg-white"
                        required
                      />
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Operator Audit Notes
                    </label>
                    <input
                      type="text"
                      value={operatorNotes}
                      onChange={(e) => setOperatorNotes(e.target.value)}
                      className="w-full text-xs px-2.5 py-1.5 border border-slate-300 rounded bg-white"
                    />
                  </div>

                  <div className="flex items-center justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => handleInlineDecision('REJECTED')}
                      disabled={isSubmittingDecision}
                      className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded text-xs font-semibold transition"
                    >
                      Reject Order (Mark Failed)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleInlineDecision('APPROVED')}
                      disabled={isSubmittingDecision || !substituteSku || !alternateHub}
                      className="px-4 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold transition flex items-center space-x-1.5 shadow"
                    >
                      {isSubmittingDecision && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      <span>Approve & Verify Reallocation</span>
                    </button>
                  </div>
                </Card>
              )}

              {/* Scenario 2 SLA Delay Alert Banner */}
              {activeOrder.order_status === 'DELAYED' && (
                <Card className="p-4 border-amber-300 bg-amber-50/70 shadow-sm">
                  <div className="flex items-start space-x-3 text-amber-900">
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider">
                        Fulfilment SLA Breach Alert
                      </h4>
                      <p className="text-xs text-amber-800 mt-1 leading-relaxed">
                        Warehouse fulfilment stage duration (10,000ms) breached the configured SLA threshold (5,000ms). Order status transitioned to <strong>DELAYED</strong>.
                      </p>
                      <div className="mt-2 text-[11px] text-amber-900 bg-amber-100 p-2 rounded">
                        <strong>Policy Engine Guard:</strong> Automatic cancellation and warehouse reassignment are strictly blocked. Non-destructive priority expedition authorized upon operator review.
                      </div>
                    </div>
                  </div>
                </Card>
              )}

              {/* Advisory RCA Card */}
              {rcaReport && (
                <Card className="p-4 border-blue-200 bg-blue-50/50 shadow-sm">
                  <div className="flex items-center justify-between pb-2 border-b border-blue-200 mb-2.5">
                    <div className="flex items-center space-x-2 text-blue-900">
                      <Bot className="w-4 h-4 text-blue-600" />
                      <h4 className="font-bold text-xs uppercase tracking-wider">
                        Advisory Root Cause Analysis
                      </h4>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-mono font-bold">
                        {rcaReport.model_source}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                          rcaReport.risk_level === 'HIGH'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        Risk: {rcaReport.risk_level}
                      </span>
                    </div>
                  </div>
                  <div className="text-xs space-y-1.5 text-slate-800">
                    <p className="font-semibold text-slate-900">
                      {rcaReport.probable_root_cause}
                    </p>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      {rcaReport.explanation}
                    </p>
                    <div className="flex items-center space-x-3 pt-1 text-[11px]">
                      <span>
                        Recommended Action: <strong className="text-blue-700 font-mono">{rcaReport.recommended_action}</strong>
                      </span>
                      <span>·</span>
                      <span>
                        Evidence Signals: <strong className="text-slate-700">{rcaReport.corroborating_signals_count}</strong>
                      </span>
                    </div>
                  </div>
                </Card>
              )}

              {/* Live Execution Timeline */}
              <Card className="p-4 border-slate-200 shadow-sm">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                  <div className="flex items-center space-x-2">
                    <Terminal className="w-4 h-4 text-blue-600" />
                    <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
                      Live Execution Timeline (Audit & Telemetry Records)
                    </h3>
                  </div>
                  <div className="flex items-center space-x-2">
                    {isLoadingAudit && <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-500" />}
                    <span className="text-[11px] font-mono text-slate-400">
                      {orderAuditLogs.length} events logged
                    </span>
                  </div>
                </div>

                {orderAuditLogs.length === 0 ? (
                  <p className="text-xs text-slate-400 py-3 text-center italic">
                    Awaiting recorded telemetry events...
                  </p>
                ) : (
                  <div className="space-y-2.5 max-h-64 overflow-y-auto pr-1">
                    {orderAuditLogs.map((log) => {
                      let badgeColor = 'bg-slate-100 text-slate-700';
                      if (log.event_type.includes('COMPLETED')) badgeColor = 'bg-emerald-100 text-emerald-800';
                      else if (log.event_type.includes('DETECTED') || log.event_type.includes('BREACH')) badgeColor = 'bg-amber-100 text-amber-800';
                      else if (log.event_type.includes('REJECTED') || log.event_type.includes('FAILED')) badgeColor = 'bg-rose-100 text-rose-800';
                      else if (log.event_type.includes('RCA') || log.event_type.includes('RESOLUTION')) badgeColor = 'bg-blue-100 text-blue-800';

                      return (
                        <div
                          key={log.log_id}
                          className="p-2.5 rounded border border-slate-200 bg-white text-xs flex items-start justify-between gap-3 shadow-xs"
                        >
                          <div className="space-y-1">
                            <div className="flex items-center space-x-2">
                              <span className={`px-1.5 py-0.2 rounded font-mono text-[10px] font-bold ${badgeColor}`}>
                                {log.event_type}
                              </span>
                              <span className="text-[11px] font-mono text-slate-400">
                                {log.actor_type}:{log.actor_id}
                              </span>
                            </div>
                            <p className="text-slate-800 leading-snug">{log.summary}</p>
                          </div>
                          <span className="text-[10px] font-mono text-slate-400 whitespace-nowrap">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
