import React, { useState } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  FileText,
  Clock,
  Filter,
  Loader2,
  AlertTriangle,
  Building,
  Layers,
  UserCheck
} from 'lucide-react';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { OperatorApproval, AuditEvent } from '../../types';

interface ViewCApprovalsAuditProps {
  pendingApprovals: OperatorApproval[];
  auditLogs: AuditEvent[];
  totalAuditLogs: number;
  isLoadingApprovals: boolean;
  isLoadingAudit: boolean;
  demoSessionId?: string;
  onDecideApproval: (
    approvalId: string,
    decision: 'APPROVED' | 'REJECTED',
    substituteSku: string,
    alternateHub: string,
    operatorId: string,
    operatorNotes: string
  ) => Promise<void>;
  onRefreshApprovals: () => void;
  onFilterAudit: (filters: { orderId?: string; incidentId?: string; actorType?: string }) => void;
  verificationResult: {
    approvalId: string;
    success: boolean;
    orderStatus: string;
    currentStage: string;
    message: string;
  } | null;
}

export const ViewC_ApprovalsAudit: React.FC<ViewCApprovalsAuditProps> = ({
  pendingApprovals,
  auditLogs,
  totalAuditLogs,
  isLoadingApprovals,
  isLoadingAudit,
  demoSessionId,
  onDecideApproval,
  onRefreshApprovals,
  onFilterAudit,
  verificationResult
}) => {
  const [approvalScope, setApprovalScope] = useState<'ALL' | 'DEMO'>('ALL');
  // Approval Form State (keyed by approval_id)
  const [formState, setFormState] = useState<
    Record<
      string,
      {
        substituteSku: string;
        alternateHub: string;
        operatorId: string;
        operatorNotes: string;
        isSubmitting: boolean;
        error: string | null;
      }
    >
  >({});

  // Audit filter state
  const [auditOrderId, setAuditOrderId] = useState('');
  const [auditIncidentId, setAuditIncidentId] = useState('');
  const [auditActorType, setAuditActorType] = useState('ALL');

  // Initialize or get form state for approval
  const getApprovalForm = (approval: OperatorApproval) => {
    let params: any = {};
    if (approval.action_parameters) {
      if (typeof approval.action_parameters === 'string') {
        try {
          params = JSON.parse(approval.action_parameters);
        } catch {
          params = {};
        }
      } else {
        params = approval.action_parameters;
      }
    }

    return (
      formState[approval.approval_id] || {
        substituteSku: params.substitute_sku || 'SKU-CYBER-500-ALT',
        alternateHub: params.alternate_hub || 'HUB-EAST-02',
        operatorId: 'OP-JATAYU-01',
        operatorNotes: 'Verified inventory replenishment at alternate hub. Safe to reallocate.',
        isSubmitting: false,
        error: null
      }
    );
  };

  const updateFormField = (
    approvalId: string,
    field: string,
    value: string
  ) => {
    setFormState((prev) => ({
      ...prev,
      [approvalId]: {
        ...(prev[approvalId] || {
          substituteSku: 'SKU-CYBER-500-ALT',
          alternateHub: 'HUB-EAST-02',
          operatorId: 'OP-JATAYU-01',
          operatorNotes: 'Verified replenishment.',
          isSubmitting: false,
          error: null
        }),
        [field]: value
      }
    }));
  };

  const handleSubmitDecision = async (
    approval: OperatorApproval,
    decision: 'APPROVED' | 'REJECTED'
  ) => {
    const current = getApprovalForm(approval);

    // Validation
    if (decision === 'APPROVED') {
      if (!current.substituteSku.trim()) {
        updateFormField(approval.approval_id, 'error', 'Substitute SKU is required for approval.');
        return;
      }
      if (!current.alternateHub.trim()) {
        updateFormField(approval.approval_id, 'error', 'Alternate Hub identifier is required.');
        return;
      }
    }

    setFormState((prev) => ({
      ...prev,
      [approval.approval_id]: { ...current, isSubmitting: true, error: null }
    }));

    try {
      await onDecideApproval(
        approval.approval_id,
        decision,
        current.substituteSku,
        current.alternateHub,
        current.operatorId,
        current.operatorNotes
      );
    } catch (err: any) {
      setFormState((prev) => ({
        ...prev,
        [approval.approval_id]: {
          ...current,
          isSubmitting: false,
          error: err?.message || 'Failed to submit operator decision'
        }
      }));
    }
  };

  const handleApplyAuditFilters = () => {
    onFilterAudit({
      orderId: auditOrderId.trim() || undefined,
      incidentId: auditIncidentId.trim() || undefined,
      actorType: auditActorType !== 'ALL' ? auditActorType : undefined
    });
  };

  const actorTypes = ['ALL', 'SYSTEM', 'AI_AGENT', 'OPERATOR', 'SIMULATOR'];

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">
          Human-in-the-Loop Approval Queue & Audit Trail
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Supervised operator intervention for hard rejections (Scenario 3) and append-only governance trail.
        </p>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border flex items-start space-x-3.5 shadow-xs ${
            verificationResult.success
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : 'bg-rose-50 border-rose-300 text-rose-900'
          }`}
        >
          {verificationResult.success ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          )}
          <div className="text-xs space-y-1">
            <div className="font-bold text-sm">
              {verificationResult.success
                ? 'Operator Decision Verified & Dispatched'
                : 'Execution Verification Failed'}
            </div>
            <p className="leading-relaxed">{verificationResult.message}</p>
            <div className="flex items-center space-x-4 pt-1 font-mono text-[11px]">
              <span>
                Order Status:{' '}
                <strong className="text-emerald-700">{verificationResult.orderStatus}</strong>
              </span>
              <span>
                Current Stage:{' '}
                <strong className="text-blue-700">{verificationResult.currentStage}</strong>
              </span>
            </div>
          </div>
        </div>
      )}

      {/* SECTION 1: Human Approval Queue */}
      {(() => {
        const demoApprovals = pendingApprovals.filter(
          (a) => a.order?.is_demo_order || (demoSessionId && a.order?.demo_session_id === demoSessionId)
        );
        const displayedApprovals = approvalScope === 'DEMO' ? demoApprovals : pendingApprovals;

        return (
          <Card
            title={
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <ShieldAlert className="w-4 h-4 text-rose-600" />
                  <span>Pending Human Approvals</span>
                  <span className="bg-rose-100 text-rose-700 font-bold px-2 py-0.5 rounded-full text-xs ml-1 font-mono">
                    {pendingApprovals.length} pending
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
                    <button
                      type="button"
                      onClick={() => setApprovalScope('ALL')}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                        approvalScope === 'ALL'
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-500 hover:text-slate-700'
                      }`}
                    >
                      All Historical ({pendingApprovals.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setApprovalScope('DEMO')}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition ${
                        approvalScope === 'DEMO'
                          ? 'bg-blue-600 text-white font-bold'
                          : 'text-slate-500 hover:text-slate-700'
                      }`}
                    >
                      Current Demo Session ({demoApprovals.length})
                    </button>
                  </div>
                  <button
                    onClick={onRefreshApprovals}
                    disabled={isLoadingApprovals}
                    className="text-xs text-slate-600 hover:text-slate-900 flex items-center space-x-1 px-2.5 py-1 bg-white border border-slate-300 rounded-lg shadow-2xs disabled:opacity-50 font-medium"
                  >
                    <Clock className={`w-3.5 h-3.5 ${isLoadingApprovals ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>
              </div>
            }
            subtitle="Permanent Out-of-Stock rejections (HTTP 422) requiring operator parameter validation and authorization"
          >
            {displayedApprovals.length === 0 ? (
              <div className="py-8 text-center text-slate-400">
                <UserCheck className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                <p className="font-semibold text-slate-700 text-sm">
                  {approvalScope === 'DEMO'
                    ? 'No pending approvals in current demo session.'
                    : 'Human Approval Queue is empty.'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Trigger "Scenario 3: Hard Rejection" from the top bar or Live Demo workspace to dispatch an approval request.
                </p>
              </div>
            ) : (
              <div className="space-y-5">
                {displayedApprovals.map((approval) => {
                  const form = getApprovalForm(approval);
                  const isDemo =
                    approval.order?.is_demo_order ||
                    (demoSessionId && approval.order?.demo_session_id === demoSessionId);

                  return (
                    <div
                      key={approval.approval_id}
                      className={`border rounded-xl p-5 shadow-xs space-y-4 transition ${
                        isDemo
                          ? 'bg-blue-50/20 border-blue-300 ring-1 ring-blue-300/60'
                          : 'bg-slate-50/70 border-slate-200'
                      }`}
                    >
                      {/* Top Bar */}
                      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-200/80">
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-300 shadow-2xs">
                            {approval.approval_id}
                          </span>
                          {isDemo && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-600 text-white font-mono shadow-xs">
                              LIVE DEMO
                            </span>
                          )}
                          <span className="text-xs text-slate-500">
                            Incident: <strong className="font-mono text-slate-700">{approval.incident_id}</strong>
                          </span>
                          <span className="text-xs text-slate-500">
                            Order: <strong className="font-mono text-blue-600">{approval.order_id}</strong>
                          </span>
                        </div>

                        <div className="flex items-center space-x-2">
                          <Badge variant="danger" id="badge-high-risk">
                            HIGH RISK
                          </Badge>
                          <Badge variant="warning">AWAITING OPERATOR</Badge>
                        </div>
                      </div>

                      {/* Context and Evidence */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                        <div className="bg-white p-3 rounded-lg border border-slate-200/80 space-y-1">
                          <span className="font-bold text-slate-900 block font-mono">Failure Evidence:</span>
                          <p className="text-slate-600 leading-relaxed">
                            Inventory service returned HTTP 422 Unprocessable Entity (OUT_OF_STOCK).
                            Automatic retry was prohibited by policy.
                          </p>
                          <div className="text-[11px] text-slate-400 font-mono mt-1">
                            Requested: {new Date(approval.requested_at).toLocaleString()}
                          </div>
                        </div>

                        <div className="bg-white p-3 rounded-lg border border-slate-200/80 space-y-1">
                          <span className="font-bold text-slate-900 block font-mono">Policy Rule:</span>
                          <p className="text-slate-600 leading-relaxed">
                            Order reallocation requires operator-supplied substitute SKU and alternate warehouse hub.
                          </p>
                          <div className="text-[11px] text-amber-700 font-medium font-mono mt-1">
                            Action Type: {approval.selected_action}
                          </div>
                        </div>
                      </div>

                      {/* Operator Form */}
                      <div className="bg-white p-4 rounded-xl border border-slate-200/90 space-y-3.5">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          {/* Substitute SKU */}
                          <div>
                            <label
                              htmlFor="substituteSkuInput"
                              className="block text-xs font-semibold text-slate-700 mb-1"
                            >
                              Substitute Product SKU <span className="text-rose-500">*</span>
                            </label>
                            <div className="relative">
                              <Layers className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                              <input
                                id="substituteSkuInput"
                                name="substituteSkuInput"
                                type="text"
                                value={form.substituteSku}
                                onChange={(e) =>
                                  updateFormField(approval.approval_id, 'substituteSku', e.target.value)
                                }
                                placeholder="e.g. SKU-CYBER-500-ALT"
                                className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:outline-none font-mono"
                              />
                            </div>
                          </div>

                          {/* Alternate Warehouse Hub */}
                          <div>
                            <label
                              htmlFor="alternateHubInput"
                              className="block text-xs font-semibold text-slate-700 mb-1"
                            >
                              Alternate Warehouse Hub <span className="text-rose-500">*</span>
                            </label>
                            <div className="relative">
                              <Building className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                              <input
                                id="alternateHubInput"
                                name="alternateHubInput"
                                type="text"
                                value={form.alternateHub}
                                onChange={(e) =>
                                  updateFormField(approval.approval_id, 'alternateHub', e.target.value)
                                }
                                placeholder="e.g. HUB-EAST-02"
                                className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:outline-none font-mono"
                              />
                            </div>
                          </div>

                          {/* Operator ID */}
                          <div>
                            <label className="block text-xs font-semibold text-slate-700 mb-1">
                              Operator ID
                            </label>
                            <input
                              type="text"
                              value={form.operatorId}
                              onChange={(e) =>
                                updateFormField(approval.approval_id, 'operatorId', e.target.value)
                              }
                              className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:outline-none font-mono"
                            />
                          </div>
                        </div>

                        {/* Operator Notes */}
                        <div>
                          <label className="block text-xs font-semibold text-slate-700 mb-1">
                            Operator Audit Notes & Verification Rationale
                          </label>
                          <textarea
                            rows={2}
                            value={form.operatorNotes}
                            onChange={(e) =>
                              updateFormField(approval.approval_id, 'operatorNotes', e.target.value)
                            }
                            className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-1 focus:ring-blue-500 focus:outline-none"
                            placeholder="Rationale recorded permanently in audit trail..."
                          />
                        </div>

                        {form.error && (
                          <div className="text-xs text-rose-600 bg-rose-50 p-2 rounded-lg border border-rose-200">
                            {form.error}
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex items-center justify-end space-x-2.5 pt-1">
                          <button
                            id="btn-reject"
                            onClick={() => handleSubmitDecision(approval, 'REJECTED')}
                            disabled={form.isSubmitting}
                            className="px-3.5 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold rounded-lg transition disabled:opacity-50 flex items-center space-x-1.5"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Reject Order</span>
                          </button>

                          <button
                            id="btn-approve"
                            onClick={() => handleSubmitDecision(approval, 'APPROVED')}
                            disabled={form.isSubmitting}
                            className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50 flex items-center space-x-1.5"
                          >
                            {form.isSubmitting ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <CheckCircle2 className="w-3.5 h-3.5" />
                            )}
                            <span>Approve Substitution</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        );
      })()}

      {/* SECTION 2: Queryable Append-Only Audit Trail Table */}
      <Card
        title={
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <span>Immutable Application Audit Trail</span>
            <span className="text-xs text-slate-500 font-normal font-mono">
              ({totalAuditLogs.toLocaleString()} events recorded)
            </span>
          </div>
        }
        subtitle="Append-only log of all system transitions, AI advisories, policy decisions, and operator actions"
      >
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-4 bg-slate-50/70 p-3 rounded-lg border border-slate-200 text-xs">
          <div className="flex items-center space-x-1 text-slate-700 font-semibold">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          <div>
            <input
              type="text"
              placeholder="Order ID..."
              value={auditOrderId}
              onChange={(e) => setAuditOrderId(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg font-mono text-xs w-36 bg-white"
            />
          </div>

          <div>
            <input
              type="text"
              placeholder="Incident ID..."
              value={auditIncidentId}
              onChange={(e) => setAuditIncidentId(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg font-mono text-xs w-36 bg-white"
            />
          </div>

          <div className="flex items-center space-x-1.5">
            <span className="text-slate-500">Actor:</span>
            <select
              value={auditActorType}
              onChange={(e) => setAuditActorType(e.target.value)}
              className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs bg-white font-mono"
            >
              {actorTypes.map((act) => (
                <option key={act} value={act}>
                  {act}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={handleApplyAuditFilters}
            disabled={isLoadingAudit}
            className="px-3.5 py-1.5 bg-slate-900 text-white rounded-lg hover:bg-slate-800 font-semibold text-xs transition disabled:opacity-50 flex items-center space-x-1 shadow-2xs"
          >
            {isLoadingAudit && <Loader2 className="w-3 h-3 animate-spin" />}
            <span>Apply Filters</span>
          </button>
        </div>

        {/* Audit Log Table */}
        <div className="overflow-x-auto border border-slate-200/90 rounded-lg">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50/80 text-slate-600 font-semibold">
              <tr>
                <th className="px-3.5 py-3 font-mono">Timestamp</th>
                <th className="px-3.5 py-3 font-mono">Order / Correlation ID</th>
                <th className="px-3.5 py-3 font-mono">Incident ID</th>
                <th className="px-3.5 py-3">Event Type</th>
                <th className="px-3.5 py-3">Actor</th>
                <th className="px-3.5 py-3">Summary</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-slate-400">
                    No audit records match the current filters.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.log_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-3.5 py-3 font-mono text-slate-500 text-[11px] whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-3.5 py-3 font-mono text-slate-900">
                      <div className="font-semibold text-blue-600">{log.order_id || '—'}</div>
                      <div className="text-[10px] text-slate-400 truncate max-w-[140px]">
                        {log.correlation_id}
                      </div>
                    </td>
                    <td className="px-3.5 py-3 font-mono text-slate-700 text-[11px]">
                      {log.incident_id || '—'}
                    </td>
                    <td className="px-3.5 py-3 font-medium">
                      <span className="bg-slate-100 text-slate-800 px-2 py-0.5 rounded text-[10px] font-mono border border-slate-200">
                        {log.event_type}
                      </span>
                    </td>
                    <td className="px-3.5 py-3 whitespace-nowrap">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono border ${
                          log.actor_type === 'OPERATOR'
                            ? 'bg-purple-50 text-purple-700 border-purple-200'
                            : log.actor_type === 'AI_AGENT'
                            ? 'bg-blue-50 text-blue-700 border-blue-200'
                            : log.actor_type === 'SYSTEM'
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-slate-100 text-slate-700 border-slate-200'
                        }`}
                      >
                        {log.actor_type}: {log.actor_id}
                      </span>
                    </td>
                    <td className="px-3.5 py-3 text-slate-700 text-xs leading-relaxed">
                      {log.summary}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};
