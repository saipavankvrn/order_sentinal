import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Header } from './components/layout/Header';
import { Navigation, ActiveTab } from './components/layout/Navigation';
import { SimulationControls } from './components/simulation/SimulationControls';
import { ViewA_Dashboard } from './components/views/ViewA_Dashboard';
import { ViewB_JourneyRCA } from './components/views/ViewB_JourneyRCA';
import { ViewC_ApprovalsAudit } from './components/views/ViewC_ApprovalsAudit';
import { ViewD_LiveDemo } from './components/views/ViewD_LiveDemo';
import { api } from './api/client';
import {
  Order,
  AnalyticsMetrics,
  FailureDistribution,
  OrderJourneyData,
  Incident,
  RCAReport,
  OperatorApproval,
  AuditEvent,
  SimulationResult
} from './types';

export const App: React.FC = () => {
  // Navigation & View State (with query param support for deep-linking)
  const initialTab = (() => {
    if (typeof window !== 'undefined') {
      const param = new URLSearchParams(window.location.search).get('tab');
      if (param === 'journey' || param === 'approvals' || param === 'dashboard' || param === 'live-demo') {
        return param as ActiveTab;
      }
    }
    return 'live-demo' as ActiveTab;
  })();

  const initialOrderId = (() => {
    if (typeof window !== 'undefined') {
      return new URLSearchParams(window.location.search).get('order_id');
    }
    return null;
  })();

  const [activeTab, setActiveTab] = useState<ActiveTab>(initialTab);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(initialOrderId);
  const [activeOrder, setActiveOrder] = useState<Order | null>(null);

  // Demo Session State
  const [demoSessionId, setDemoSessionId] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      const existing = localStorage.getItem('orderflow_demo_session_id');
      if (existing) return existing;
      const fresh = `DEMO-SESSION-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
      localStorage.setItem('orderflow_demo_session_id', fresh);
      return fresh;
    }
    return `DEMO-SESSION-${Date.now().toString(36).substring(4).toUpperCase()}`;
  });
  const [demoFilter, setDemoFilter] = useState<'ALL' | 'DEMO' | 'HISTORICAL'>('ALL');

  // Pagination & Filtering for View A
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [auditFilters, setAuditFilters] = useState<{
    orderId?: string;
    incidentId?: string;
    actorType?: string;
  }>({});

  // Core Data State
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [distribution, setDistribution] = useState<FailureDistribution | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [totalOrders, setTotalOrders] = useState(0);
  const [journeyData, setJourneyData] = useState<OrderJourneyData | null>(null);
  const [activeIncident, setActiveIncident] = useState<Incident | null>(null);
  const [rcaReport, setRcaReport] = useState<RCAReport | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<OperatorApproval[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>([]);
  const [totalAuditLogs, setTotalAuditLogs] = useState(0);

  // System & Polling State
  const [systemStatus, setSystemStatus] = useState<'ONLINE' | 'DEGRADED' | 'OFFLINE'>('ONLINE');
  const [isPolling, setIsPolling] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoadingJourney, setIsLoadingJourney] = useState(false);
  const [isLoadingRCA, setIsLoadingRCA] = useState(false);

  // Verification Banner State
  const [verificationResult, setVerificationResult] = useState<{
    approvalId: string;
    success: boolean;
    orderStatus: string;
    currentStage: string;
    message: string;
  } | null>(null);

  // Polling overlap protection ref
  const isFetchingRef = useRef(false);

  // Synchronize Browser URL
  const updateUrl = useCallback((tab: ActiveTab, orderId: string | null) => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams();
    params.set('tab', tab);
    if (orderId) {
      params.set('order_id', orderId);
    }
    const newSearch = `?${params.toString()}`;
    if (window.location.search !== newSearch) {
      window.history.pushState(null, '', `${window.location.pathname}${newSearch}`);
    }
  }, []);

  // Listen to browser popstate (back/forward)
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get('tab');
      if (tabParam === 'journey' || tabParam === 'approvals' || tabParam === 'dashboard' || tabParam === 'live-demo') {
        setActiveTab(tabParam as ActiveTab);
      }
      const orderParam = params.get('order_id');
      if (orderParam) {
        setSelectedOrderId(orderParam);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Navigation tab switcher with URL synchronization
  const handleTabChange = (newTab: ActiveTab) => {
    setActiveTab(newTab);
    updateUrl(newTab, selectedOrderId);
  };

  // Main Data Fetcher
  const fetchData = useCallback(async (isManual: boolean = false, pageOverride?: number) => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;
    if (isManual) setIsRefreshing(true);

    const activePage = pageOverride ?? page;
    const skip = (activePage - 1) * pageSize;

    try {
      // 1. Analytics & Metrics
      const isDemoParam = demoFilter === 'DEMO' ? true : demoFilter === 'HISTORICAL' ? false : undefined;
      const demoSessionParam = demoFilter === 'DEMO' ? demoSessionId : undefined;

      const [metricsRes, distRes, approvalsRes, ordersRes] = await Promise.allSettled([
        api.getMetrics(),
        api.getFailureDistribution(),
        api.getPendingApprovals(),
        api.getOrders({
          page: activePage,
          skip,
          limit: pageSize,
          status: statusFilter,
          search: searchQuery,
          is_demo: isDemoParam,
          demo_session_id: demoSessionParam
        })
      ]);

      if (metricsRes.status === 'fulfilled') {
        setMetrics(metricsRes.value);
        setSystemStatus('ONLINE');
      } else {
        setSystemStatus('DEGRADED');
      }

      if (distRes.status === 'fulfilled') {
        setDistribution(distRes.value);
      }

      if (approvalsRes.status === 'fulfilled') {
        setPendingApprovals(approvalsRes.value);
      }

      if (ordersRes.status === 'fulfilled') {
        setOrders(ordersRes.value.items);
        setTotalOrders(ordersRes.value.total);
        // Default select first order if none selected
        if (!selectedOrderId && ordersRes.value.items.length > 0) {
          setSelectedOrderId(ordersRes.value.items[0].order_id);
          setActiveOrder(ordersRes.value.items[0]);
        }
      }

      // 2. Audit Trail
      const auditRes = await api.getAuditLogs({
        limit: 30,
        order_id: auditFilters.orderId,
        incident_id: auditFilters.incidentId,
        actor_type: auditFilters.actorType
      }).catch(() => null);

      if (auditRes) {
        setAuditLogs(auditRes);
        setTotalAuditLogs(auditRes.length);
      }
    } catch {
      setSystemStatus('OFFLINE');
    } finally {
      isFetchingRef.current = false;
      if (isManual) setIsRefreshing(false);
    }
  }, [page, statusFilter, searchQuery, auditFilters, selectedOrderId, demoFilter, demoSessionId]);

  // Fetch Order Journey & Incident RCA when selectedOrderId changes
  const fetchOrderDetails = useCallback(async (orderId: string) => {
    setIsLoadingJourney(true);
    try {
      // Parallel fetch: order details, journey progression, and linked incidents
      const [orderRes, journeyRes, incList] = await Promise.all([
        api.getOrder(orderId).catch(() => null),
        api.getOrderJourney(orderId).catch(() => null),
        api.getIncidents({ order_id: orderId }).catch(() => [])
      ]);

      if (orderRes) {
        setActiveOrder(orderRes);
      }
      if (journeyRes) {
        setJourneyData(journeyRes);
      }

      // Handle linked incidents & existing RCA report (WITHOUT auto-triggering analysis on every poll)
      if (incList && incList.length > 0) {
        const inc = incList[0];
        setActiveIncident(inc);

        // Fetch existing RCA report non-destructively via incident detail
        try {
          const detail = await api.getIncidentDetail(inc.incident_id);
          if (detail && detail.rca_report) {
            setRcaReport(detail.rca_report);
          } else {
            setRcaReport(null);
          }
        } catch {
          setRcaReport(null);
        }
      } else {
        setActiveIncident(null);
        setRcaReport(null);
      }
    } catch {
      setActiveOrder(null);
      setJourneyData(null);
      setActiveIncident(null);
      setRcaReport(null);
    } finally {
      setIsLoadingJourney(false);
    }
  }, []);

  // Update order details whenever selectedOrderId changes
  useEffect(() => {
    if (selectedOrderId) {
      fetchOrderDetails(selectedOrderId);
    }
  }, [selectedOrderId, fetchOrderDetails]);

  // 3-second non-overlapping interval polling with unmount cleanup
  useEffect(() => {
    // Initial fetch
    fetchData();

    if (!isPolling) return;

    const interval = setInterval(() => {
      fetchData();
      if (selectedOrderId) {
        fetchOrderDetails(selectedOrderId);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [isPolling, fetchData, selectedOrderId, fetchOrderDetails]);

  // Handler: Selecting an order from View A (Inspect Journey)
  const handleSelectOrder = (orderId: string) => {
    setSelectedOrderId(orderId);
    setActiveTab('journey');
    updateUrl('journey', orderId);
    fetchOrderDetails(orderId);
  };

  // Scenario Trigger Callback with quick navigation
  const handleScenarioTriggered = (
    result: SimulationResult,
    targetView: 'dashboard' | 'journey' | 'approvals' | 'live-demo'
  ) => {
    if (result.order?.order_id) {
      setSelectedOrderId(result.order.order_id);
      setActiveOrder(result.order);
      updateUrl(targetView, result.order.order_id);
    } else {
      updateUrl(targetView, selectedOrderId);
    }
    setActiveTab(targetView);
    // Immediate state refresh
    fetchData(true);
    if (result.order?.order_id) {
      fetchOrderDetails(result.order.order_id);
    }
  };

  // Safe Session Reset Handler
  const handleResetDemoSession = async () => {
    await api.resetDemoSession(demoSessionId);
    const fresh = `DEMO-SESSION-${Math.random().toString(36).substring(2, 8).toUpperCase()}`;
    if (typeof window !== 'undefined') {
      localStorage.setItem('orderflow_demo_session_id', fresh);
    }
    setDemoSessionId(fresh);
    setSelectedOrderId(null);
    setActiveOrder(null);
    setJourneyData(null);
    setActiveIncident(null);
    setRcaReport(null);
    fetchData(true);
  };

  // Human Approval Decision Handler
  const handleDecideApproval = async (
    approvalId: string,
    decision: 'APPROVED' | 'REJECTED',
    substituteSku: string,
    alternateHub: string,
    operatorId: string,
    operatorNotes: string
  ) => {
    const isApproved = decision === 'APPROVED';
    const res = await api.decideApproval(approvalId, {
      decision,
      operator_id: operatorId,
      operator_name: 'Devin Lead',
      operator_notes: operatorNotes,
      selected_action: isApproved ? 'SUBSTITUTE_SKU_AND_REALLOCATE' : 'REJECT_ORDER',
      action_parameters: isApproved
        ? {
            substitute_sku: substituteSku,
            alternate_hub: alternateHub
          }
        : undefined
    });

    setVerificationResult({
      approvalId,
      success: res.verification_passed ?? (decision === 'APPROVED'),
      orderStatus: res.order_status || (isApproved ? 'PROCESSING' : 'FAILED'),
      currentStage: res.current_stage || (isApproved ? 'FULFILMENT' : 'INVENTORY'),
      message:
        res.message ||
        (isApproved
          ? `Operator decision APPROVED. Downstream stock reservation confirmed at ${alternateHub} with SKU ${substituteSku}. Order journey resumed towards completion.`
          : 'Operator rejected the substitution request. Order transitioned to terminal FAILED.')
    });

    // Refresh immediately
    await fetchData(true);
    if (selectedOrderId) {
      await fetchOrderDetails(selectedOrderId);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col">
      {/* Enterprise Navy Header */}
      <Header
        isPolling={isPolling}
        onTogglePolling={() => setIsPolling(!isPolling)}
        onManualRefresh={() => {
          fetchData(true);
          if (selectedOrderId) fetchOrderDetails(selectedOrderId);
        }}
        isRefreshing={isRefreshing}
        systemStatus={systemStatus}
      />

      {/* Persistent Simulation Bar */}
      <SimulationControls
        onScenarioTriggered={handleScenarioTriggered}
        onOpenLiveDemo={() => handleTabChange('live-demo')}
      />

      {/* Main Navigation Bar */}
      <Navigation
        activeTab={activeTab}
        onTabChange={handleTabChange}
        pendingApprovalsCount={pendingApprovals.length}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'live-demo' && (
          <ViewD_LiveDemo
            demoSessionId={demoSessionId}
            onResetSession={handleResetDemoSession}
            onSelectOrder={handleSelectOrder}
            activeOrder={activeOrder}
            journeyData={journeyData}
            activeIncident={activeIncident}
            rcaReport={rcaReport}
            isLoadingJourney={isLoadingJourney}
            onRefresh={() => {
              fetchData(true);
              if (selectedOrderId) fetchOrderDetails(selectedOrderId);
            }}
            onScenarioTriggered={(result) => {
              handleScenarioTriggered(result, 'live-demo');
            }}
            onDecideApproval={handleDecideApproval}
          />
        )}

        {activeTab === 'dashboard' && (
          <ViewA_Dashboard
            metrics={metrics}
            distribution={distribution}
            orders={orders}
            totalOrders={totalOrders}
            page={page}
            pageSize={pageSize}
            onPageChange={(newPage) => {
              setPage(newPage);
              fetchData(true, newPage);
            }}
            isLoading={isRefreshing}
            onSelectOrder={handleSelectOrder}
            onRefresh={() => fetchData(true)}
            onSearchChange={(query) => {
              setSearchQuery(query);
              setPage(1);
            }}
            onStatusFilterChange={(status) => {
              setStatusFilter(status);
              setPage(1);
            }}
            statusFilter={statusFilter}
            searchQuery={searchQuery}
            demoFilter={demoFilter}
            onDemoFilterChange={(f) => {
              setDemoFilter(f);
              setPage(1);
            }}
          />
        )}

        {activeTab === 'journey' && (
          <ViewB_JourneyRCA
            orders={orders}
            selectedOrderId={selectedOrderId}
            activeOrder={activeOrder}
            onSelectOrder={(id) => {
              setSelectedOrderId(id);
              updateUrl('journey', id);
              fetchOrderDetails(id);
            }}
            journeyData={journeyData}
            activeIncident={activeIncident}
            rcaReport={rcaReport}
            isLoadingJourney={isLoadingJourney}
            isLoadingRCA={isLoadingRCA}
            onAnalyzeRCA={async (incidentId) => {
              setIsLoadingRCA(true);
              try {
                const rca = await api.getIncidentRCA(incidentId);
                setRcaReport(rca);
              } finally {
                setIsLoadingRCA(false);
              }
            }}
            onNavigateToApprovals={() => {
              setActiveTab('approvals');
              updateUrl('approvals', selectedOrderId);
            }}
          />
        )}

        {activeTab === 'approvals' && (
          <ViewC_ApprovalsAudit
            pendingApprovals={pendingApprovals}
            auditLogs={auditLogs}
            totalAuditLogs={totalAuditLogs}
            isLoadingApprovals={isRefreshing}
            isLoadingAudit={isRefreshing}
            demoSessionId={demoSessionId}
            onDecideApproval={handleDecideApproval}
            onRefreshApprovals={() => fetchData(true)}
            onFilterAudit={(filters) => {
              setAuditFilters(filters);
              fetchData(true);
            }}
            verificationResult={verificationResult}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-3 text-center text-xs text-slate-500">
        OrderFlow Sentinel • Virtusa Jatayu Platform • Strictly Policy-Authorized Self-Healing Engine
      </footer>
    </div>
  );
};
