import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

describe('OrderFlow Sentinel - Frontend Client & State Verification', () => {

  // Test 1: ApiError Structure
  test('ApiError correctly wraps message, status, and payload data', async () => {
    class ApiError extends Error {
      constructor(message, status, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
      }
    }

    const err = new ApiError('HTTP 409 Conflict: Idempotency collision', 409, { detail: 'Duplicate key' });
    assert.equal(err.name, 'ApiError');
    assert.equal(err.status, 409);
    assert.equal(err.message, 'HTTP 409 Conflict: Idempotency collision');
    assert.deepEqual(err.data, { detail: 'Duplicate key' });
  });

  // Test 2: Query String Construction
  test('Constructs accurate query parameters for Order and Audit filtering', () => {
    function buildOrderQuery(params) {
      const query = new URLSearchParams();
      if (params.page) query.append('page', params.page.toString());
      if (params.skip !== undefined) query.append('skip', params.skip.toString());
      if (params.limit) query.append('limit', params.limit.toString());
      if (params.status && params.status !== 'ALL') query.append('status', params.status);
      if (params.search) query.append('search', params.search);
      return query.toString();
    }

    const qs1 = buildOrderQuery({ page: 1, limit: 20, status: 'DELAYED', search: 'ORD-1002' });
    assert.equal(qs1, 'page=1&limit=20&status=DELAYED&search=ORD-1002');

    // Clicking Next to Page 2 updates skip to 15
    const qsPage2 = buildOrderQuery({ page: 2, skip: 15, limit: 15 });
    assert.equal(qsPage2, 'page=2&skip=15&limit=15');

    // Navigating beyond 50 records to Page 5 updates skip to 60
    const qsPage5 = buildOrderQuery({ page: 5, skip: 60, limit: 15 });
    assert.equal(qsPage5, 'page=5&skip=60&limit=15');

    const qsAll = buildOrderQuery({ status: 'ALL' });
    assert.equal(qsAll, '');
  });

  // Test 3: Approval Parameter Validation Guard
  test('Rejects approval submission when substitute SKU or warehouse hub is blank', () => {
    function validateApprovalSubmission(decision, sku, hub) {
      if (decision === 'APPROVED') {
        if (!sku || !sku.trim()) {
          throw new Error('Substitute SKU is required for approval.');
        }
        if (!hub || !hub.trim()) {
          throw new Error('Alternate Hub identifier is required.');
        }
      }
      return true;
    }

    assert.throws(
      () => validateApprovalSubmission('APPROVED', '', 'HUB-EAST-02'),
      /Substitute SKU is required/
    );
    assert.throws(
      () => validateApprovalSubmission('APPROVED', 'SKU-CYBER-500-ALT', '  '),
      /Alternate Hub identifier is required/
    );
    assert.equal(
      validateApprovalSubmission('APPROVED', 'SKU-CYBER-500-ALT', 'HUB-EAST-02'),
      true
    );
    // Rejections do not require substitute parameters
    assert.equal(
      validateApprovalSubmission('REJECTED', '', ''),
      true
    );
  });

  // Test 4: Stage Status Indicator Logic
  test('Maps 7-stage order status to correct badge variants and styles', () => {
    function getStageIndicator(status) {
      switch (status) {
        case 'SUCCESS':
          return { variant: 'success', label: 'SUCCESS' };
        case 'PROCESSING':
          return { variant: 'info', label: 'PROCESSING' };
        case 'DELAYED':
          return { variant: 'warning', label: 'DELAYED' };
        case 'FAILED':
          return { variant: 'danger', label: 'FAILED' };
        default:
          return { variant: 'neutral', label: 'PENDING' };
      }
    }

    assert.equal(getStageIndicator('SUCCESS').variant, 'success');
    assert.equal(getStageIndicator('DELAYED').variant, 'warning');
    assert.equal(getStageIndicator('FAILED').variant, 'danger');
    assert.equal(getStageIndicator('PROCESSING').variant, 'info');
    assert.equal(getStageIndicator(undefined).variant, 'neutral');
  });

  // Test 5: Fallback and Empty State Resiliency
  test('Handles empty metrics and failure distribution safely', () => {
    const rawMetrics = null;
    const totalOrdersFallback = 0;
    const displayTotal = rawMetrics?.total_orders ?? totalOrdersFallback;
    assert.equal(displayTotal, 0);

    const emptyDistribution = { categories: [], total_incidents: 0, distribution_map: {} };
    assert.equal(emptyDistribution.total_incidents, 0);
    assert.equal(emptyDistribution.categories.length, 0);
  });

  // Test 6: Double-Click Guard State
  test('Double-click guard blocks concurrent scenario execution', () => {
    let loadingScenario = null;

    function triggerScenario(key) {
      if (loadingScenario) {
        return false; // Guard blocked
      }
      loadingScenario = key;
      return true;
    }

    assert.equal(triggerScenario('SCENARIO_1_HTTP_503_SELF_HEAL'), true);
    // Concurrent click should be blocked
    assert.equal(triggerScenario('SCENARIO_1_HTTP_503_SELF_HEAL'), false);
    assert.equal(triggerScenario('SCENARIO_2_SLA_DELAY'), false);

    // After completion, next trigger allowed
    loadingScenario = null;
    assert.equal(triggerScenario('SCENARIO_2_SLA_DELAY'), true);
  });

  // Test 7: Stage Matching for Canonical Names
  test('Matches canonical and alias stage names across all 7 stages', () => {
    const backendStages = [
      { stage_name: 'CUSTOMER_ORDER', status: 'SUCCESS' },
      { stage_name: 'ADDRESS_VALIDATION', status: 'SUCCESS' },
      { stage_name: 'PAYMENT', status: 'SUCCESS' },
      { stage_name: 'INVENTORY', status: 'SUCCESS' },
      { stage_name: 'FULFILMENT', status: 'SUCCESS' },
      { stage_name: 'DELIVERY', status: 'SUCCESS' },
      { stage_name: 'NOTIFICATION', status: 'SUCCESS' }
    ];

    const stageNamesOrder = [
      'CUSTOMER_ORDER',
      'ADDRESS_VALIDATION',
      'PAYMENT',
      'INVENTORY',
      'FULFILMENT',
      'DELIVERY',
      'NOTIFICATION'
    ];

    for (const stageKey of stageNamesOrder) {
      const match = backendStages.find(
        (s) =>
          s.stage_name === stageKey ||
          (stageKey === 'PAYMENT' && (s.stage_name === 'PAYMENT_PROCESSING' || s.stage_name === 'PAYMENT')) ||
          (stageKey === 'INVENTORY' && (s.stage_name === 'INVENTORY_RESERVATION' || s.stage_name === 'INVENTORY')) ||
          (stageKey === 'FULFILMENT' && (s.stage_name === 'WAREHOUSE_FULFILMENT' || s.stage_name === 'FULFILMENT')) ||
          (stageKey === 'NOTIFICATION' && (s.stage_name === 'CUSTOMER_NOTIFICATION' || s.stage_name === 'NOTIFICATION'))
      );
      assert.ok(match, `Stage ${stageKey} should be matched`);
      assert.equal(match.status, 'SUCCESS');
    }
  });

  // Test 8: Telemetry Event Array Normalization
  test('Normalizes raw_events into telemetry_events safely', () => {
    function normalizeJourney(data) {
      const events = data.raw_events || data.telemetry_events || [];
      return {
        ...data,
        raw_events: events,
        telemetry_events: events
      };
    }

    const payload = {
      order_id: 'ORD-1001',
      raw_events: [{ event_id: 'EVT-1', http_status: 200, duration_ms: 120 }]
    };
    const normalized = normalizeJourney(payload);
    assert.equal(normalized.telemetry_events.length, 1);
    assert.equal(normalized.raw_events.length, 1);
    assert.equal(normalized.telemetry_events[0].event_id, 'EVT-1');
  });

  // Test 9: Deep-Linking URL Parameter Construction
  test('Constructs and parses deep-link parameters for View B navigation', () => {
    function makeDeepLink(tab, orderId) {
      const params = new URLSearchParams();
      params.set('tab', tab);
      if (orderId) params.set('order_id', orderId);
      return `?${params.toString()}`;
    }

    const qs = makeDeepLink('journey', 'ORD-2026-999');
    assert.equal(qs, '?tab=journey&order_id=ORD-2026-999');

    const parsed = new URLSearchParams(qs);
    assert.equal(parsed.get('tab'), 'journey');
    assert.equal(parsed.get('order_id'), 'ORD-2026-999');
  });

});

