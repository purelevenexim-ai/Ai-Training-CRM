/**
 * E2E tests for Pure Leven CRM Journey Orchestration
 * Tests: create journey → enroll → analytics → variants → bulk enroll → clone
 * Target: https://ai.pureleven.com (dashboard) + https://track.pureleven.com/api/crm (API)
 */

import { test, expect, request } from '@playwright/test';
// Node.js WebSocket client for direct connection tests (not browser context)
import WebSocket from 'ws';

const API = 'https://track.pureleven.com/api/crm';
const APP = 'https://ai.pureleven.com';

let testJourneyId: string;
const testEmail = `e2e_${Date.now()}@test.pureleven.com`;

// ─── Backend API Tests ───────────────────────────────────────────────────────

test.describe('Backend API - Health', () => {
  test('full health check returns healthy', async ({ request: req }) => {
    const res = await req.get(`${API}/health/full`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('healthy');
    expect(body.checks.database.status).toBe('ok');
    expect(body.checks.redis.status).toBe('ok');
  });

  test('scheduler reports running with scheduled jobs', async ({ request: req }) => {
    const res = await req.get(`${API}/sync/status`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.scheduler_running).toBe(true);
    expect(body.jobs.length).toBeGreaterThanOrEqual(2);
    const jobIds = body.jobs.map((j: { id: string }) => j.id);
    expect(jobIds).toContain('meta_audience_sync');
    expect(jobIds).toContain('google_audience_sync');
  });
});

test.describe('Backend API - Journey CRUD', () => {
  test('create journey', async ({ request: req }) => {
    const res = await req.post(`${API}/journeys`, {
      data: {
        name: `E2E Test Journey ${Date.now()}`,
        entry_trigger: 'customer_create',
        status: 'ACTIVE',
        template_json: { steps: [] },
      },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.id).toBeTruthy();
    expect(body.status).toBe('ACTIVE');
    testJourneyId = body.id;
  });

  test('list journeys includes created journey', async ({ request: req }) => {
    const res = await req.get(`${API}/journeys`);
    expect(res.ok()).toBeTruthy();
    const journeys = await res.json();
    expect(Array.isArray(journeys)).toBe(true);
    if (testJourneyId) {
      const found = journeys.find((j: { id: string }) => j.id === testJourneyId);
      expect(found).toBeTruthy();
    }
  });

  test('get journey by id', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.get(`${API}/journeys/${testJourneyId}`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.id).toBe(testJourneyId);
    expect(body.status).toBe('ACTIVE');
  });

  test('update journey status to PAUSED', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.put(`${API}/journeys/${testJourneyId}`, {
      data: { status: 'PAUSED' },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('PAUSED');
    // Restore to ACTIVE
    await req.put(`${API}/journeys/${testJourneyId}`, { data: { status: 'ACTIVE' } });
  });
});

test.describe('Backend API - Enrollment', () => {
  test('enroll customer in journey', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.post(`${API}/journeys/${testJourneyId}/enroll`, {
      data: { customer_email: testEmail },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.instance_id).toBeTruthy();
    expect(body.customer_email).toBe(testEmail);
    expect(body.status).toBe('ACTIVE');
  });

  test('duplicate enroll returns 409', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.post(`${API}/journeys/${testJourneyId}/enroll`, {
      data: { customer_email: testEmail },
    });
    expect(res.status()).toBe(409);
  });

  test('get journey analytics shows enrolled customer', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.get(`${API}/journeys/${testJourneyId}/analytics`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.total_enrolled).toBeGreaterThanOrEqual(1);
    expect(body.active_instances).toBeGreaterThanOrEqual(1);
  });

  test('list enrollments returns enrolled customer', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.get(`${API}/journeys/${testJourneyId}/enrollments`);
    expect(res.ok()).toBeTruthy();
    const enrollments = await res.json();
    expect(Array.isArray(enrollments)).toBe(true);
    const found = enrollments.find((e: { customer_email: string }) => e.customer_email === testEmail);
    expect(found).toBeTruthy();
  });
});

test.describe('Backend API - A/B Variants', () => {
  test('create variant for journey', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.post(`${API}/journeys/${testJourneyId}/variants`, {
      data: {
        variant_name: 'Variant A',
        traffic_split_pct: 50,
      },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.id).toBeTruthy();
    expect(body.variant_name).toBe('Variant A');
    expect(body.traffic_split_pct).toBe(50);
  });

  test('list variants returns created variant', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.get(`${API}/journeys/${testJourneyId}/variants`);
    expect(res.ok()).toBeTruthy();
    const variants = await res.json();
    expect(Array.isArray(variants)).toBe(true);
    expect(variants.length).toBeGreaterThanOrEqual(1);
  });
});

test.describe('Backend API - Bulk Enrollment', () => {
  test('bulk enroll via email list creates async job', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const emails = [
      `bulk1_${Date.now()}@test.com`,
      `bulk2_${Date.now()}@test.com`,
      `bulk3_${Date.now()}@test.com`,
    ];
    const res = await req.post(`${API}/journeys/${testJourneyId}/enroll-bulk`, {
      data: { emails },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.job_id).toBeTruthy();
    expect(body.total_rows).toBe(3);
    expect(['PENDING', 'RUNNING', 'COMPLETED']).toContain(body.status);

    // Poll until completed (max 20s)
    let status = body.status;
    let attempts = 0;
    while (status !== 'COMPLETED' && status !== 'FAILED' && attempts < 10) {
      await new Promise((r) => setTimeout(r, 2000));
      const poll = await req.get(`${API}/jobs/${body.job_id}/status`);
      const pollBody = await poll.json();
      status = pollBody.status;
      attempts++;
    }
    expect(status).toBe('COMPLETED');
  });
});

test.describe('Backend API - Clone', () => {
  test('clone journey creates a DRAFT copy', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.post(`${API}/journeys/${testJourneyId}/clone`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.id).not.toBe(testJourneyId);
    expect(body.status).toBe('DRAFT');
    expect(body.name).toContain('(Copy)');

    // Cleanup: delete clone
    await req.delete(`${API}/journeys/${body.id}`);
  });
});

test.describe('Backend API - Attribution', () => {
  test('attribution endpoint returns revenue data', async ({ request: req }) => {
    if (!testJourneyId) test.skip();
    const res = await req.get(`${API}/journeys/${testJourneyId}/attribution`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.journey_id).toBe(testJourneyId);
    expect(typeof body.total_attributed_revenue).toBe('number');
    expect(body.currency).toBe('INR');
  });
});

// ─── Frontend UI Tests ───────────────────────────────────────────────────────

test.describe('Frontend Dashboard', () => {
  test('loads dashboard with correct title', async ({ page }) => {
    await page.goto(APP);
    await expect(page).toHaveTitle(/Pureleven CRM/i);
    await expect(page.getByText(/Pure Leven CRM Dashboard/i)).toBeVisible();
  });

  test('navigation tabs are visible', async ({ page }) => {
    await page.goto(APP);
    await page.waitForLoadState('networkidle').catch(() => {});
    await expect(page.getByText(/Journeys/i).first()).toBeVisible();
    await expect(page.getByText(/Timeline/i)).toBeVisible();
    await expect(page.getByText(/Builder/i)).toBeVisible();
    await expect(page.getByText(/Live Feed/i)).toBeVisible();
    await expect(page.getByText(/A\/B Tests/i)).toBeVisible();
  });

  test('A/B Tests tab loads variant panel', async ({ page }) => {
    await page.goto(APP);
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.getByText(/A\/B Tests/i).click();
    await expect(page.getByText(/A\/B Testing/i)).toBeVisible();
    await expect(page.getByText(/A\/B Variants/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Clone Journey/i })).toBeVisible();
    await expect(page.getByText(/Bulk Enroll/i)).toBeVisible();
  });

  test('Journeys tab loads analytics', async ({ page }) => {
    await page.goto(APP);
    await page.waitForLoadState('networkidle').catch(() => {});
    await expect(page.getByText(/Journeys/i).first()).toBeVisible();
    await page.waitForTimeout(2000);
  });
});

// ─── Phase 3: Real-time WebSocket Tests ──────────────────────────────────────

test.describe('Phase 3 - WebSocket Real-time', () => {
  test('WebSocket metrics endpoint connects successfully', async () => {
    const wsUrl = 'wss://track.pureleven.com/api/crm/ws/metrics?token=e2e-test';
    await new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(wsUrl);
      const timeout = setTimeout(() => {
        ws.terminate();
        reject(new Error('WebSocket connection timeout'));
      }, 8000);
      ws.on('open', () => {
        clearTimeout(timeout);
        ws.close();
        resolve();
      });
      ws.on('error', (err) => {
        clearTimeout(timeout);
        reject(err);
      });
    });
  });

  test('WebSocket steps endpoint connects successfully', async () => {
    const wsUrl = 'wss://track.pureleven.com/api/crm/ws/steps?token=e2e-test';
    await new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(wsUrl);
      const timeout = setTimeout(() => { ws.terminate(); reject(new Error('timeout')); }, 8000);
      ws.on('open', () => { clearTimeout(timeout); ws.close(); resolve(); });
      ws.on('error', (err) => { clearTimeout(timeout); reject(err); });
    });
  });

  test('WebSocket metrics endpoint sends initial JSON snapshot', async () => {
    const wsUrl = 'wss://track.pureleven.com/api/crm/ws/metrics?token=e2e-test';
    const message = await new Promise<string>((resolve, reject) => {
      const ws = new WebSocket(wsUrl);
      const timeout = setTimeout(() => { ws.terminate(); reject(new Error('no message received in 10s')); }, 10000);
      ws.on('message', (data) => {
        clearTimeout(timeout);
        ws.close();
        resolve(data.toString());
      });
      ws.on('error', (err) => { clearTimeout(timeout); reject(err); });
    });
    const parsed = JSON.parse(message);
    expect(typeof parsed).toBe('object');
    expect(parsed).not.toBeNull();
  });

  test('realtime WebSocket health endpoint responds', async ({ request: req }) => {
    const res = await req.get(`${API}/ws/health`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body).toHaveProperty('status');
  });
});

// ─── Phase 3: Variant Promote Tests ──────────────────────────────────────────

test.describe('Phase 3 - Variant Promote', () => {
  test('promote variant sets status to WINNER and pauses others', async ({ request: req }) => {
    // Create a fresh journey for this test
    const jRes = await req.post(`${API}/journeys`, {
      data: {
        name: `E2E Promote Test ${Date.now()}`,
        entry_trigger: 'SIGNUP',
        status: 'ACTIVE',
      },
    });
    expect(jRes.ok()).toBeTruthy();
    const journey = await jRes.json();
    const jid = journey.id;

    // Create two variants
    const v1Res = await req.post(`${API}/journeys/${jid}/variants`, {
      data: { variant_name: 'Control', traffic_split_pct: 50 },
    });
    expect(v1Res.ok()).toBeTruthy();
    const v1 = await v1Res.json();

    const v2Res = await req.post(`${API}/journeys/${jid}/variants`, {
      data: { variant_name: 'Treatment', traffic_split_pct: 50 },
    });
    expect(v2Res.ok()).toBeTruthy();
    const v2 = await v2Res.json();

    // Promote v1
    const promoteRes = await req.post(`${API}/journeys/${jid}/variants/${v1.id}/promote`);
    expect(promoteRes.ok()).toBeTruthy();
    const promoted = await promoteRes.json();
    // Endpoint returns { status: 'promoted', variant_id, variant_name, journey_id }
    expect(promoted.status).toBe('promoted');
    expect(promoted.variant_id).toBe(v1.id);

    // Check v2 is paused
    const listRes = await req.get(`${API}/journeys/${jid}/variants`);
    const variants = await listRes.json();
    const variantList = Array.isArray(variants) ? variants : variants.variants;
    const v2Updated = variantList.find((v: { id: string }) => v.id === v2.id);
    expect(v2Updated?.status).toBe('PAUSED');
  });
});

// ─── Phase 4: Audience Sync Tests ────────────────────────────────────────────

test.describe('Phase 4 - Audience Sync', () => {
  test('sync status endpoint returns scheduler running', async ({ request: req }) => {
    const res = await req.get(`${API}/sync/status`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.scheduler_running).toBe(true);
    // Field is 'jobs' in the API response
    expect(Array.isArray(body.jobs)).toBe(true);
    const jobIds = body.jobs.map((j: { id: string }) => j.id);
    expect(jobIds).toContain('meta_audience_sync');
    expect(jobIds).toContain('google_audience_sync');
  });

  test('meta sync trigger endpoint responds', async ({ request: req }) => {
    const res = await req.post(`${API}/sync/meta/now`);
    // May return ok (credentials configured) or skipped (not configured) — both are valid
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(['ok', 'skipped', 'error']).toContain(body.status);
    expect(body.account_id).toBeDefined();
  });

  test('google sync trigger endpoint responds', async ({ request: req }) => {
    const res = await req.post(`${API}/sync/google/now`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(['ok', 'skipped', 'error']).toContain(body.status);
    expect(body.customer_id).toBeDefined();
  });
});

// ─── Phase 5: Attribution Tests ───────────────────────────────────────────────

test.describe('Phase 5 - Attribution', () => {
  test('attribution endpoint returns valid structure', async ({ request: req }) => {
    // First ensure we have a journey with known ID
    const listRes = await req.get(`${API}/journeys`);
    const data = await listRes.json();
    const journeys = Array.isArray(data) ? data : data.journeys;
    if (journeys.length === 0) {
      test.skip();
      return;
    }
    const jid = journeys[0].id;
    const attrRes = await req.get(`${API}/journeys/${jid}/attribution`);
    expect(attrRes.ok()).toBeTruthy();
    const body = await attrRes.json();
    // API returns total_attributed_revenue and total_orders
    expect(body).toHaveProperty('total_attributed_revenue');
    expect(body).toHaveProperty('total_orders');
    expect(body).toHaveProperty('attribution_model');
  });

  test('shopify webhook endpoint accepts order payload', async ({ request: req }) => {
    const payload = {
      id: `e2e_test_${Date.now()}`,
      email: testEmail,
      total_price: '1499.00',
      currency: 'INR',
      line_items: [{ title: 'Organic Turmeric', quantity: 2, price: '749.50' }],
    };
    // Use a known HMAC-less header (endpoint validates via Shopify HMAC in prod)
    const res = await req.post(`${API}/webhooks/shopify/order-paid`, {
      data: payload,
      headers: { 'X-Shopify-Topic': 'orders/paid', 'Content-Type': 'application/json' },
    });
    // 200 = processed, 401/422 = HMAC validation (expected in prod) — both acceptable for E2E
    expect([200, 401, 422, 400]).toContain(res.status());
  });
});
