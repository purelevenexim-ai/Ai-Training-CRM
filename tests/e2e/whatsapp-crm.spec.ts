import { expect, test, type APIResponse } from '@playwright/test';

const API_BASE = process.env.CRM_API_BASE || 'https://track.pureleven.com/api';
const APP_BASE = process.env.CRM_DASHBOARD_URL || 'https://ai.pureleven.com';
const SHOP_DOMAIN = process.env.E2E_SHOP_DOMAIN || 'rwxtic-gz.myshopify.com';

async function expectJsonResponse(response: APIResponse) {
  expect(response.ok(), `${response.url()} returned ${response.status()}`).toBeTruthy();
  return response.json();
}

test.describe('WhatsApp CRM today-forward automation', () => {
  test('Sales OS exposes today-forward guard and audience segments', async ({ request }) => {
    const response = await request.get(`${API_BASE}/crm/whatsapp/sales-os`);
    const body = await expectJsonResponse(response);

    expect(body.ok).toBe(true);
    expect(body.automation).toMatchObject({
      mode: 'today_forward',
      old_manual_orders_ignored: true,
    });
    expect(body.automation.start_at).toBeTruthy();
    expect(body.lifecycle.pending_total).toBeGreaterThanOrEqual(0);

    const audienceKeys = (body.retargeting?.audiences || []).map((audience: { key: string }) => audience.key);
    expect(audienceKeys).toEqual(expect.arrayContaining(['purchased', 'interested', 'non_purchased']));
  });

  test('lifecycle retry dry-run is send-safe and scoped to the automation start', async ({ request }) => {
    const response = await request.post(`${API_BASE}/crm/whatsapp/orders/retry-lifecycle`, {
      data: { event_type: 'all', limit: 25, dry_run: true },
    });
    const body = await expectJsonResponse(response);

    expect(body.ok).toBe(true);
    expect(body.automation_start).toBeTruthy();
    expect(body.results).toHaveLength(3);

    for (const result of body.results) {
      expect(['order_created', 'tracking_added', 'delivered']).toContain(result.event_type);
      expect(result.from_start_at).toBe(body.automation_start);
      expect(result.sent).toBe(0);
      expect(result.failed).toBe(0);
      expect(result.dry_run).toBe(result.eligible);
    }
  });

  test('Journey pipeline is filtered to the same today-forward automation window', async ({ request }) => {
    const response = await request.get(`${API_BASE}/journey/orchestrate/pipeline?shop_domain=${encodeURIComponent(SHOP_DOMAIN)}`);
    const body = await expectJsonResponse(response);

    expect(body.shop_domain).toBe(SHOP_DOMAIN);
    expect(body.automation_start).toBeTruthy();
    expect(body.total_journey_customers).toBeGreaterThanOrEqual(0);
    expect(body.send_flags).toHaveProperty('day2_sent');
    expect(body.pipeline.map((stage: { stage_name: string }) => stage.stage_name)).toEqual(
      expect.arrayContaining(['in_transit', 'delivered', 'review']),
    );
  });
});

test.describe('WhatsApp CRM custom audience builder', () => {
  const cases = [
    {
      name: 'interested omnichannel audience',
      payload: {
        lead_types: ['interested'],
        labels: ['interested'],
        statuses: ['interested'],
        score_min: 50,
        score_max: 100,
        delivery_channels: ['whatsapp', 'email'],
      },
    },
    {
      name: 'purchased omnichannel audience',
      payload: {
        lead_types: ['purchased'],
        labels: ['purchased'],
        statuses: ['purchased'],
        score_min: 0,
        score_max: 100,
        delivery_channels: ['whatsapp', 'email'],
      },
    },
    {
      name: 'custom score and date-filtered email audience',
      payload: {
        lead_types: ['all'],
        score_min: 70,
        score_max: 100,
        date_field: 'updated_at',
        date_from: '2026-05-23',
        delivery_channels: ['email'],
      },
    },
  ];

  for (const item of cases) {
    test(`estimates ${item.name}`, async ({ request }) => {
      const response = await request.post(`${API_BASE}/crm/whatsapp/campaigns/estimate-cost`, { data: item.payload });
      const body = await expectJsonResponse(response);

      expect(body.ok).toBe(true);
      expect(body.matched).toBeGreaterThanOrEqual(0);
      expect(body.whatsapp_sendable).toBeGreaterThanOrEqual(0);
      expect(body.email_sendable).toBeGreaterThanOrEqual(0);
      expect(body.delivery_channels).toEqual(expect.arrayContaining(item.payload.delivery_channels));
      expect(body.filters.delivery_channels).toEqual(expect.arrayContaining(item.payload.delivery_channels));
      expect(body.cost).toHaveProperty('inr');
    });
  }
});

test.describe('WhatsApp CRM templates and dashboard UI', () => {
  test('templates API returns live Wabis/Meta templates with preview bodies', async ({ request }) => {
    const response = await request.get(`${API_BASE}/crm/whatsapp/templates`);
    const body = await expectJsonResponse(response);

    const templates = [...(body.wabis || []), ...(body.meta || [])];
    expect(templates.length).toBeGreaterThan(0);
    expect(body.meta_configured).toBe(true);
    expect(body.meta_waba_id).toBeTruthy();

    const previewable = templates.find((template: any) => template.name && template.body?.text);
    expect(previewable, 'Expected at least one template with a previewable body').toBeTruthy();
    expect(typeof previewable.total_vars).toBe('number');
  });

  test('dashboard exposes WhatsApp workspace, custom audiences, journeys, and editable templates', async ({ page }) => {
    await page.goto(APP_BASE, { waitUntil: 'domcontentloaded' });
    await expect(page.getByText(/Pure Leven CRM Dashboard/i)).toBeVisible();

    await page.getByRole('button', { name: /WhatsApp/i }).click();
    await expect(page.getByRole('heading', { name: /WhatsApp Workspace/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/Sales Command Center/i)).toBeVisible();

    await page.getByRole('button', { name: /^Customers$/ }).click();
    await expect(page.getByText(/Custom Audience Builder/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /^Interested$/ }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: /^Email$/ })).toBeVisible();

    await page.getByRole('button', { name: /^Journey$/ }).click();
    await expect(page.getByText(/When Does a Journey Start\?/i)).toBeVisible();
    await expect(page.getByText(/New Shopify order/i)).toBeVisible();
    await expect(page.getByText(/Interested\/custom audience/i)).toBeVisible();
    await expect(page.getByText(/Automatic Order Journey Monitor/i)).toBeVisible();
    await page.getByRole('button', { name: /Day 1 — Order Confirmed/i }).click();
    await expect(page.getByText(/Stage Template Studio/i)).toBeVisible();
    await expect(page.getByText(/Choose Different Template/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Create New Template for This Stage/i })).toBeVisible();
    await expect(page.getByText(/Purchased Customer Journey/i)).toBeVisible();
    await expect(page.getByText(/Interested Non-purchased Journey/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Custom AI Journey/i })).toBeVisible();

    await page.getByRole('button', { name: /^Templates$/ }).click();
    await expect(page.getByText(/Composer/i)).toBeVisible();
    await page.getByRole('button', { name: /^Create Template$/ }).click();
    await expect(page.getByText(/Create Meta Template/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /Order Confirmed/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Tracking Added/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Delivered/i })).toBeVisible();

    await page.locator('nav').getByRole('button', { name: /Email/i }).click();
    await expect(page.getByRole('heading', { name: /Email Workspace/i })).toBeVisible();
    await expect(page.getByText(/Lifecycle, transactional, and promotional email aligned with the WhatsApp journey/i)).toBeVisible();
    await page.getByRole('button', { name: /Lifecycle Journey/i }).click();
    await expect(page.getByText(/Email journey is now synced to the WhatsApp lifecycle/i)).toBeVisible();
    await expect(page.getByText(/Order Confirmed/i)).toBeVisible();
    await expect(page.getByText(/Tracking \/ In Transit/i)).toBeVisible();
    await expect(page.getByText(/internal aliases only/i)).toBeVisible();
  });
});
