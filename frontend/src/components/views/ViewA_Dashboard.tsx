import React from 'react';
import {
  Package,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldAlert,
  Loader2,
  Search,
  ExternalLink,
  BarChart3,
  RefreshCw,
  Sparkles,
  Info
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid
} from 'recharts';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';
import { Order, AnalyticsMetrics, FailureDistribution, OrderStatus } from '../../types';

interface ViewADashboardProps {
  metrics: AnalyticsMetrics | null;
  distribution: FailureDistribution | null;
  orders: Order[];
  totalOrders: number;
  page: number;
  pageSize: number;
  onPageChange: (newPage: number) => void;
  isLoading: boolean;
  onSelectOrder: (orderId: string) => void;
  onRefresh: () => void;
  onSearchChange: (query: string) => void;
  onStatusFilterChange: (status: string) => void;
  statusFilter: string;
  searchQuery: string;
  demoFilter?: 'ALL' | 'DEMO' | 'HISTORICAL';
  onDemoFilterChange?: (filter: 'ALL' | 'DEMO' | 'HISTORICAL') => void;
}

export const ViewA_Dashboard: React.FC<ViewADashboardProps> = ({
  metrics,
  distribution,
  orders,
  totalOrders,
  page,
  pageSize,
  onPageChange,
  isLoading,
  onSelectOrder,
  onRefresh,
  onSearchChange,
  onStatusFilterChange,
  statusFilter,
  searchQuery,
  demoFilter = 'ALL',
  onDemoFilterChange
}) => {
  const getStatusBadge = (status: OrderStatus) => {
    switch (status) {
      case 'COMPLETED':
        return <Badge variant="success" dot>COMPLETED</Badge>;
      case 'PROCESSING':
        return <Badge variant="info" dot>PROCESSING</Badge>;
      case 'DELAYED':
        return <Badge variant="warning" dot>DELAYED</Badge>;
      case 'FAILED':
        return <Badge variant="danger" dot>FAILED</Badge>;
      case 'PENDING':
        return <Badge variant="neutral" dot>PENDING</Badge>;
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  const chartData = distribution?.categories.map((c) => ({
    name: c.category.replace('_', ' '),
    count: c.count,
    rawCategory: c.category
  })) || [
    { name: 'API ERROR', count: 0, rawCategory: 'API_ERROR' },
    { name: 'ORDER DELAY', count: 0, rawCategory: 'ORDER_DELAY' },
    { name: 'ORDER REJECTION', count: 0, rawCategory: 'ORDER_REJECTION' }
  ];

  const getBarColor = (category: string) => {
    switch (category) {
      case 'API_ERROR':
        return '#3B82F6'; // Blue
      case 'ORDER_DELAY':
        return '#F59E0B'; // Amber
      case 'ORDER_REJECTION':
        return '#EF4444'; // Red
      default:
        return '#64748B';
    }
  };

  const statusFilters = ['ALL', 'COMPLETED', 'PROCESSING', 'DELAYED', 'FAILED', 'PENDING'];
  const totalPages = Math.max(1, Math.ceil(totalOrders / pageSize));

  return (
    <div className="space-y-6">
      {/* View Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>Operational Monitoring & Diagnostics</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time telemetry, 7-stage order progression, and automated failure detection across all orders.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onRefresh}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Update KPIs</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Tiles */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Total Ingested */}
        <div className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-slate-300 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider font-mono">Total Ingested</span>
            <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
              <Package className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono tracking-tight text-slate-900">
            {(metrics?.total_orders ?? totalOrders).toLocaleString()}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Across all journeys</div>
        </div>

        {/* Completed */}
        <div className="bg-white rounded-xl border border-emerald-100 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-emerald-200 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider font-mono">Completed</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 border border-emerald-100">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono tracking-tight text-emerald-600">
            {(metrics?.completed_orders ?? 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-emerald-600/80 mt-1">100% Stage 7 confirmed</div>
        </div>

        {/* In Progress */}
        <div className="bg-white rounded-xl border border-blue-100 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-blue-200 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider font-mono">In Progress</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600 border border-blue-100">
              <Loader2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono tracking-tight text-blue-600">
            {(metrics?.in_progress_orders ?? 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-blue-600/80 mt-1">Active microservices</div>
        </div>

        {/* Delayed */}
        <div className="bg-white rounded-xl border border-amber-100 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-amber-200 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider font-mono">SLA Delayed</span>
            <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600 border border-amber-100">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono tracking-tight text-amber-600">
            {(metrics?.delayed_orders ?? 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-amber-600/80 mt-1">Latency &gt; 5,000ms</div>
        </div>

        {/* Failed */}
        <div className="bg-white rounded-xl border border-rose-100 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-rose-200 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-rose-700 uppercase tracking-wider font-mono">Failed</span>
            <div className="w-8 h-8 rounded-lg bg-rose-50 flex items-center justify-center text-rose-600 border border-rose-100">
              <XCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono tracking-tight text-rose-600">
            {(metrics?.failed_orders ?? 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-rose-600/80 mt-1">Terminal rejections</div>
        </div>

        {/* Pending Approvals */}
        <div className="bg-white rounded-xl border border-purple-100 p-4 shadow-[0_1px_2px_rgba(0,0,0,0.03)] hover:border-purple-200 transition">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-purple-700 uppercase tracking-wider font-mono">Pending Approvals</span>
            <div className="w-8 h-8 rounded-lg bg-purple-50 flex items-center justify-center text-purple-600 border border-purple-100">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-2 text-2xl font-bold font-mono tracking-tight text-purple-600">
            {(metrics?.pending_approvals ?? 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-purple-600/80 mt-1">Awaiting operator review</div>
        </div>
      </div>

      {/* Failure Distribution Section */}
      <Card
        title={
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-4 h-4 text-blue-600" />
            <span>Failure Distribution by Category</span>
          </div>
        }
        subtitle="Aggregated failure telemetry categorized by root error type"
      >
        <div className="space-y-4">
          <div className="h-48 w-full">
            {distribution && distribution.total_incidents > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    formatter={(value: any) => [`${value} Incidents`, 'Count']}
                    contentStyle={{ backgroundColor: '#0B1120', color: '#fff', borderRadius: '8px', border: '1px solid #1E293B', fontSize: '12px' }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={90}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={getBarColor(entry.rawCategory)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-slate-400">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-1" />
                <p className="text-xs font-medium text-slate-500">
                  Zero active failure incidents recorded. System running healthy.
                </p>
              </div>
            )}
          </div>

          {/* Supporting Explanations Legend */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 border-t border-slate-100">
            <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-blue-50/60 border border-blue-100">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 flex-shrink-0 mt-1" />
              <div>
                <span className="text-xs font-bold text-blue-900 block font-mono">API Errors (HTTP 503)</span>
                <span className="text-[11px] text-blue-700/80 leading-relaxed block mt-0.5">
                  Transient infrastructure & gateway timeouts. Autonomously resolved via exponential backoff retries.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-amber-50/60 border border-amber-100">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 flex-shrink-0 mt-1" />
              <div>
                <span className="text-xs font-bold text-amber-900 block font-mono">Order Delays (SLA Breach)</span>
                <span className="text-[11px] text-amber-700/80 leading-relaxed block mt-0.5">
                  Fulfilment latency exceeding policy threshold (&gt;5000ms). Order marked DELAYED with operator alert.
                </span>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-2.5 rounded-lg bg-rose-50/60 border border-rose-100">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 flex-shrink-0 mt-1" />
              <div>
                <span className="text-xs font-bold text-rose-900 block font-mono">Order Rejections (HTTP 422)</span>
                <span className="text-[11px] text-rose-700/80 leading-relaxed block mt-0.5">
                  Permanent out-of-stock rejections. Auto-retry prohibited by policy; routed to Human Approval Queue.
                </span>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Live Order Monitoring Grid */}
      <Card
        title="Live Order Monitoring Table"
        subtitle="Chronological log of synthetic and ingested customer orders"
        action={
          <div className="flex flex-wrap items-center gap-2">
            {/* Search */}
            <div className="relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
              <input
                type="text"
                placeholder="Search Order ID, Customer, SKU..."
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 w-60 bg-white"
              />
            </div>
          </div>
        }
      >
        {/* Scope & Status Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
          {/* Status Filters */}
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1">
            <span className="text-xs font-semibold text-slate-500 mr-1">Status:</span>
            {statusFilters.map((s) => (
              <button
                key={s}
                onClick={() => onStatusFilterChange(s)}
                className={`px-2.5 py-1 text-xs rounded-lg font-medium transition ${
                  statusFilter === s
                    ? 'bg-slate-900 text-white font-semibold shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Demo Scope Filter */}
          {onDemoFilterChange && (
            <div className="flex items-center space-x-1 bg-slate-100/90 p-1 rounded-lg border border-slate-200/70">
              <span className="text-[11px] font-bold text-slate-500 px-2 uppercase font-mono">Scope:</span>
              <button
                type="button"
                onClick={() => onDemoFilterChange('ALL')}
                className={`px-2.5 py-1 text-xs rounded-md font-semibold transition ${
                  demoFilter === 'ALL'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All Orders ({totalOrders})
              </button>
              <button
                type="button"
                onClick={() => onDemoFilterChange('DEMO')}
                className={`px-2.5 py-1 text-xs rounded-md font-semibold transition flex items-center space-x-1.5 ${
                  demoFilter === 'DEMO'
                    ? 'bg-blue-600 text-white shadow-xs font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sparkles className="w-3 h-3" />
                <span>Live Demo Orders</span>
              </button>
              <button
                type="button"
                onClick={() => onDemoFilterChange('HISTORICAL')}
                className={`px-2.5 py-1 text-xs rounded-md font-semibold transition ${
                  demoFilter === 'HISTORICAL'
                    ? 'bg-white text-slate-900 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Historical Baseline
              </button>
            </div>
          )}
        </div>

        {/* Order Table */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50/70 font-semibold text-slate-600">
              <tr>
                <th className="px-3 py-3 font-mono">Order ID</th>
                <th className="px-3 py-3">Customer</th>
                <th className="px-3 py-3 font-mono">Product SKU</th>
                <th className="px-3 py-3 font-mono">Amount</th>
                <th className="px-3 py-3">Current Stage</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Created At</th>
                <th className="px-3 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-500" />
                    <span>Loading order records...</span>
                  </td>
                </tr>
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <Info className="w-6 h-6 mx-auto mb-2 text-slate-300" />
                    <p className="font-medium text-slate-600">No orders match the current filter criteria.</p>
                    <p className="text-[11px] text-slate-400 mt-1">Try resetting the status filter or clearing search.</p>
                  </td>
                </tr>
              ) : (
                orders.map((o) => (
                  <tr key={o.order_id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="px-3 py-3 font-mono font-bold text-blue-600 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span>{o.order_id}</span>
                        {o.is_demo_order && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                            DEMO
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3 font-medium text-slate-900 whitespace-nowrap">
                      {o.customer_name}
                    </td>
                    <td className="px-3 py-3 font-mono text-slate-600 whitespace-nowrap">
                      {o.product_sku}
                    </td>
                    <td className="px-3 py-3 font-mono font-semibold text-slate-800 whitespace-nowrap">
                      ${Number(o.order_amount).toFixed(2)}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-100 text-slate-700 font-semibold border border-slate-200">
                        {o.current_stage}
                      </span>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      {getStatusBadge(o.order_status)}
                    </td>
                    <td className="px-3 py-3 text-slate-500 whitespace-nowrap font-mono text-[11px]">
                      {new Date(o.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-3 py-3 text-right whitespace-nowrap">
                      <button
                        onClick={() => onSelectOrder(o.order_id)}
                        className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold text-blue-600 bg-blue-50/70 border border-blue-200/80 rounded-md hover:bg-blue-100/70 hover:text-blue-700 transition"
                      >
                        <span>Inspect Journey</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="flex items-center justify-between border-t border-slate-100 pt-3 mt-3 text-xs text-slate-500">
          <div>
            Showing <span className="font-semibold text-slate-700">{orders.length}</span> of{' '}
            <span className="font-semibold text-slate-700">{totalOrders}</span> orders (Page{' '}
            <span className="font-semibold text-slate-700">{page}</span> of{' '}
            <span className="font-semibold text-slate-700">{totalPages}</span>)
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="px-3 py-1.5 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium transition"
            >
              Previous
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="px-3 py-1.5 border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed font-medium transition"
            >
              Next
            </button>
          </div>
        </div>
      </Card>
    </div>
  );
};
