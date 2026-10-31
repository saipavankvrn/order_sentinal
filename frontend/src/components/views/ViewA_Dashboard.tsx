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
  RefreshCw
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell
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
        return <Badge variant="success">COMPLETED</Badge>;
      case 'PROCESSING':
        return <Badge variant="info">PROCESSING</Badge>;
      case 'DELAYED':
        return <Badge variant="warning">DELAYED</Badge>;
      case 'FAILED':
        return <Badge variant="danger">FAILED</Badge>;
      case 'PENDING':
        return <Badge variant="neutral">PENDING</Badge>;
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

  return (
    <div className="space-y-6">
      {/* View Title & Context */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">
            Operational Monitoring & Diagnostics
          </h2>
          <p className="text-sm text-slate-500">
            Real-time telemetry, stage progression, and automated failure detection.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onRefresh}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-300 rounded-md hover:bg-slate-50 shadow-sm transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Update KPIs</span>
          </button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Total Orders */}
        <Card className="!p-4 border-l-4 border-l-slate-600">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Ingested</span>
            <Package className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-900">
            {metrics?.total_orders ?? totalOrders}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Across all journeys</div>
        </Card>

        {/* Completed */}
        <Card className="!p-4 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-emerald-700">Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-600">
            {metrics?.completed_orders ?? 0}
          </div>
          <div className="text-[11px] text-emerald-600/70 mt-1">Stage 7 confirmed</div>
        </Card>

        {/* In Progress */}
        <Card className="!p-4 border-l-4 border-l-blue-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-blue-700">In Progress</span>
            <Loader2 className="w-4 h-4 text-blue-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-blue-600">
            {metrics?.in_progress_orders ?? 0}
          </div>
          <div className="text-[11px] text-blue-600/70 mt-1">Active processing</div>
        </Card>

        {/* Delayed */}
        <Card className="!p-4 border-l-4 border-l-amber-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-amber-700">Delayed</span>
            <Clock className="w-4 h-4 text-amber-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-600">
            {metrics?.delayed_orders ?? 0}
          </div>
          <div className="text-[11px] text-amber-600/70 mt-1">SLA breached</div>
        </Card>

        {/* Failed */}
        <Card className="!p-4 border-l-4 border-l-rose-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-rose-700">Failed</span>
            <XCircle className="w-4 h-4 text-rose-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-600">
            {metrics?.failed_orders ?? 0}
          </div>
          <div className="text-[11px] text-rose-600/70 mt-1">Terminal rejections</div>
        </Card>

        {/* Pending Approvals */}
        <Card className="!p-4 border-l-4 border-l-purple-500">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-purple-700">Pending Approvals</span>
            <ShieldAlert className="w-4 h-4 text-purple-500" />
          </div>
          <div className="mt-2 text-2xl font-bold text-purple-600">
            {metrics?.pending_approvals ?? 0}
          </div>
          <div className="text-[11px] text-purple-600/70 mt-1">Awaiting operator</div>
        </Card>
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
        <div className="h-48 w-full">
          {distribution && distribution.total_incidents > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: any) => [`${value} Incidents`, 'Count']}
                  contentStyle={{ backgroundColor: '#0F172A', color: '#fff', borderRadius: '6px', fontSize: '12px' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
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
                className="pl-8 pr-3 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 w-56"
              />
            </div>
          </div>
        }
      >
        {/* Scope & Status Filters */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-100">
          {/* Status Filters */}
          <div className="flex items-center space-x-1 overflow-x-auto pb-1">
            <span className="text-xs font-medium text-slate-500 mr-2">Status:</span>
            {statusFilters.map((s) => (
              <button
                key={s}
                onClick={() => onStatusFilterChange(s)}
                className={`px-2.5 py-1 text-xs rounded-full font-medium transition ${
                  statusFilter === s
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Demo Scope Filter */}
          {onDemoFilterChange && (
            <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg">
              <span className="text-[11px] font-bold text-slate-500 px-2 uppercase">View:</span>
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
                className={`px-2.5 py-1 text-xs rounded-md font-semibold transition flex items-center space-x-1 ${
                  demoFilter === 'DEMO'
                    ? 'bg-amber-500 text-white shadow-xs font-bold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
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

        {/* Orders Table */}
        <div className="overflow-x-auto border border-slate-200 rounded-md">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold">
              <tr>
                <th className="px-3.5 py-2.5">Order ID</th>
                <th className="px-3.5 py-2.5">Customer</th>
                <th className="px-3.5 py-2.5">Product SKU</th>
                <th className="px-3.5 py-2.5">Amount</th>
                <th className="px-3.5 py-2.5">Current Stage</th>
                <th className="px-3.5 py-2.5">Status</th>
                <th className="px-3.5 py-2.5">Created At</th>
                <th className="px-3.5 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {orders.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-400">
                    No orders match your filter criteria. Trigger a scenario above to ingest test orders.
                  </td>
                </tr>
              ) : (
                orders.map((o) => (
                  <tr
                    key={o.order_id}
                    onClick={() => onSelectOrder(o.order_id)}
                    className="hover:bg-blue-50/50 cursor-pointer transition"
                  >
                    <td className="px-3.5 py-3 font-mono font-medium text-blue-600">
                      <div className="flex items-center space-x-1.5">
                        <span>{o.order_id}</span>
                        {o.is_demo_order && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                            LIVE DEMO
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3.5 py-3 text-slate-700 font-medium">
                      {o.customer_name}
                    </td>
                    <td className="px-3.5 py-3 text-slate-500 font-mono">
                      {o.product_sku}
                    </td>
                    <td className="px-3.5 py-3 text-slate-700">
                      ${Number(o.order_amount).toFixed(2)}
                    </td>
                    <td className="px-3.5 py-3 text-slate-600 font-medium">
                      <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[11px]">
                        {o.current_stage}
                      </span>
                    </td>
                    <td className="px-3.5 py-3">
                      {getStatusBadge(o.order_status)}
                    </td>
                    <td className="px-3.5 py-3 text-slate-400 text-[11px]">
                      {new Date(o.created_at).toLocaleTimeString()}
                    </td>
                    <td className="px-3.5 py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectOrder(o.order_id);
                        }}
                        className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 font-medium text-[11px]"
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

        {/* Pagination Bar */}
        {totalOrders > 0 && (
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
            <div>
              Showing <span className="font-semibold text-slate-700">{(page - 1) * pageSize + 1}</span> to{' '}
              <span className="font-semibold text-slate-700">{Math.min(page * pageSize, totalOrders)}</span> of{' '}
              <span className="font-semibold text-slate-700">{totalOrders}</span> orders
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => onPageChange(page - 1)}
                disabled={page <= 1}
                className="px-2.5 py-1 border border-slate-300 rounded bg-white hover:bg-slate-50 font-medium text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                Previous
              </button>
              <span className="px-2 text-slate-600 font-mono">
                {page} / {Math.max(1, Math.ceil(totalOrders / pageSize))}
              </span>
              <button
                onClick={() => onPageChange(page + 1)}
                disabled={page >= Math.ceil(totalOrders / pageSize)}
                className="px-2.5 py-1 border border-slate-300 rounded bg-white hover:bg-slate-50 font-medium text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
};
