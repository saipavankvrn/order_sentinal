import React, { useState } from 'react';
import { Play, RotateCw, AlertTriangle, XCircle, CheckCircle2, ArrowRight, Loader2, Sparkles, Terminal } from 'lucide-react';
import { api } from '../../api/client';
import { SimulationResult } from '../../types';

interface SimulationControlsProps {
  onScenarioTriggered: (result: SimulationResult, targetView: 'dashboard' | 'journey' | 'approvals' | 'live-demo') => void;
  onOpenLiveDemo?: () => void;
}

export const SimulationControls: React.FC<SimulationControlsProps> = ({ onScenarioTriggered, onOpenLiveDemo }) => {
  const [loadingScenario, setLoadingScenario] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    scenarioKey: string;
    message: string;
    orderId?: string;
    incidentId?: string;
    approvalId?: string;
    result?: SimulationResult;
  } | null>(null);

  const handleTrigger = async (
    scenarioKey: string,
    targetView: 'dashboard' | 'journey' | 'approvals',
    autoResolve: boolean = true
  ) => {
    if (loadingScenario) return; // Prevent double-triggering

    setLoadingScenario(scenarioKey);
    setFeedback(null);

    try {
      const result = await api.triggerScenario(scenarioKey, {
        customer_name: scenarioKey === 'SCENARIO_2_SLA_DELAY' ? 'Kyle Reese' : 'Sarah Connor',
        product_sku: 'SKU-CYBER-500',
        order_amount: 199.99,
        auto_resolve: autoResolve
      });

      const orderId = result.order?.order_id;
      const incidentId = result.incident?.incident_id;
      const approvalId = result.approval?.approval_id;

      let msg = `Scenario [${scenarioKey}] triggered successfully.`;
      if (scenarioKey === 'SCENARIO_0_CLEAN_RUN') {
        msg = `Clean order completed 7 stages successfully. Order ID: ${orderId}`;
      } else if (scenarioKey === 'SCENARIO_1_HTTP_503_SELF_HEAL') {
        msg = `Transient HTTP 503 detected, advisory RCA generated, and idempotent retry auto-healed order. Order ID: ${orderId}`;
      } else if (scenarioKey === 'SCENARIO_2_SLA_DELAY') {
        msg = `Fulfilment latency exceeded 5,000ms SLA threshold. Order set to DELAYED with Operator Alert. Order ID: ${orderId}`;
      } else if (scenarioKey === 'SCENARIO_3_HARD_REJECTION') {
        msg = `HTTP 422 Out-of-Stock rejection routed to Human Approval Queue. Order ID: ${orderId}`;
      }

      setFeedback({
        type: 'success',
        scenarioKey,
        message: msg,
        orderId,
        incidentId,
        approvalId,
        result
      });

      onScenarioTriggered(result, targetView);
    } catch (err: any) {
      setFeedback({
        type: 'error',
        scenarioKey,
        message: err?.message || 'Failed to trigger simulation scenario'
      });
    } finally {
      setLoadingScenario(null);
    }
  };

  return (
    <div className="bg-[#0F172A] border-b border-slate-800 text-slate-200 py-2.5 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        {/* Title / Section Marker */}
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
            Scenario Simulator:
          </span>
          <span className="text-[11px] text-slate-400 hidden xl:inline">
            (Trigger repeatable telemetry failure scenarios)
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Create Live Test Order Primary Button */}
          {onOpenLiveDemo && (
            <button
              onClick={onOpenLiveDemo}
              className="group flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 hover:from-blue-500 hover:to-indigo-500 text-xs font-bold text-white shadow-sm border border-blue-400/30 transition-all ring-1 ring-blue-400/40"
              title="Open Live Demonstration Workspace to launch custom test orders in real time"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>Create Live Test Order</span>
            </button>
          )}

          <div className="hidden sm:block h-5 w-px bg-slate-800 mx-1" />

          {/* Scenario 0 */}
          <button
            onClick={() => handleTrigger('SCENARIO_0_CLEAN_RUN', 'journey')}
            disabled={!!loadingScenario}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-slate-800/90 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700/80 transition disabled:opacity-50"
            title="Clean 7-stage baseline order with zero failures"
          >
            {loadingScenario === 'SCENARIO_0_CLEAN_RUN' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
            ) : (
              <Play className="w-3.5 h-3.5 text-blue-400" />
            )}
            <span>Scenario 0: Clean Run</span>
          </button>

          {/* Scenario 1 */}
          <button
            onClick={() => handleTrigger('SCENARIO_1_HTTP_503_SELF_HEAL', 'journey')}
            disabled={!!loadingScenario}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-emerald-950/50 hover:bg-emerald-900/60 text-xs font-medium text-emerald-300 border border-emerald-800/70 transition disabled:opacity-50"
            title="Simulates HTTP 503 transient failure, advisory RCA, and self-healing retry"
          >
            {loadingScenario === 'SCENARIO_1_HTTP_503_SELF_HEAL' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
            ) : (
              <RotateCw className="w-3.5 h-3.5 text-emerald-400" />
            )}
            <span>Scenario 1: 503 Self-Heal</span>
          </button>

          {/* Scenario 2 */}
          <button
            onClick={() => handleTrigger('SCENARIO_2_SLA_DELAY', 'journey', false)}
            disabled={!!loadingScenario}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-amber-950/50 hover:bg-amber-900/60 text-xs font-medium text-amber-300 border border-amber-800/70 transition disabled:opacity-50"
            title="Simulates 10,000ms fulfilment delay, SLA breach detection, and operator alert"
          >
            {loadingScenario === 'SCENARIO_2_SLA_DELAY' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            )}
            <span>Scenario 2: SLA Delay (Alert)</span>
          </button>

          {/* Scenario 3 */}
          <button
            onClick={() => handleTrigger('SCENARIO_3_HARD_REJECTION', 'approvals')}
            disabled={!!loadingScenario}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 rounded-md bg-rose-950/50 hover:bg-rose-900/60 text-xs font-medium text-rose-300 border border-rose-800/70 transition disabled:opacity-50"
            title="Simulates HTTP 422 Out-of-Stock permanent rejection requiring human approval"
          >
            {loadingScenario === 'SCENARIO_3_HARD_REJECTION' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-400" />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span>Scenario 3: Hard Rejection (HITL)</span>
          </button>
        </div>
      </div>

      {/* Feedback Toast Banner */}
      {feedback && (
        <div className="max-w-7xl mx-auto mt-2">
          <div
            className={`flex items-center justify-between p-2.5 rounded-lg text-xs border transition-all ${
              feedback.type === 'success'
                ? 'bg-blue-950/70 border-blue-800/80 text-blue-200'
                : 'bg-rose-950/70 border-rose-800/80 text-rose-200'
            }`}
          >
            <div className="flex items-center space-x-2.5 min-w-0">
              {feedback.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              )}
              <div className="flex flex-wrap items-center gap-2 truncate">
                <span className="font-medium text-slate-100">{feedback.message}</span>
                {feedback.orderId && (
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded text-[11px] font-mono text-blue-300 border border-slate-700">
                    Order: {feedback.orderId}
                  </span>
                )}
                {feedback.incidentId && (
                  <span className="bg-slate-900 px-1.5 py-0.5 rounded text-[11px] font-mono text-amber-300 border border-slate-700">
                    Incident: {feedback.incidentId}
                  </span>
                )}
              </div>
            </div>

            {feedback.result && (
              <button
                onClick={() =>
                  onScenarioTriggered(
                    feedback.result!,
                    feedback.scenarioKey === 'SCENARIO_3_HARD_REJECTION' ? 'approvals' : 'journey'
                  )
                }
                className="flex items-center space-x-1 ml-3 bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded text-xs font-semibold whitespace-nowrap transition shadow-sm flex-shrink-0"
              >
                <span>
                  {feedback.scenarioKey === 'SCENARIO_3_HARD_REJECTION'
                    ? 'Review in Approval Queue'
                    : 'Inspect Order Timeline'}
                </span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
