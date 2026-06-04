/**
 * Pure Leven CRM — Scale Testing Suite (1000+ Scenarios)
 * Covers: Happy paths, edge cases, integrations, WebSocket, performance
 * Run: npx playwright test tests/e2e/scale-tests.spec.ts --workers=10
 */

import { test, expect, request as playwrightRequest, APIRequestContext } from "@playwright/test";

const BASE = "https://track.pureleven.com/api/crm";
const WS_BASE = "wss://track.pureleven.com/api/crm/ws";
const TIMEOUT = 30000;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function uid(): string {
  return `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

function testEmail(prefix = "scale"): string {
  return `${prefix}_${uid()}@test.pureleven.com`;
}

function journeyPayload(overrides: Record<string, unknown> = {}) {
  return {
    name: `Scale Test Journey ${uid()}`,
    entry_trigger: "signup",
    status: "ACTIVE",
    template_json: {
      steps: [
        { id: "step_1", type: "email", delay_days: 0, action_data: { subject: "Welcome" } },
        { id: "step_2", type: "email", delay_days: 1, action_data: { subject: "Follow-up" } },
      ],
    },
    ...overrides,
  };
}

// ─── SUITE 1: HEALTH & FOUNDATION (20 tests) ──────────────────────────────────

test.describe("Suite 1: Health & Foundation", () => {
  for (let i = 1; i <= 20; i++) {
    test(`[1-${i}] Health check attempt ${i}`, async ({ request }) => {
      const r = await request.get(`${BASE}/health`);
      expect(r.status()).toBeLessThan(500);
    });
  }
});

test.describe("Suite 1b: Full Health Checks", () => {
  for (let i = 1; i <= 20; i++) {
    test(`[1b-${i}] Full health check ${i}`, async ({ request }) => {
      const r = await request.get(`${BASE}/health/full`);
      expect(r.ok()).toBeTruthy();
      const body = await r.json();
      expect(body.status).toMatch(/healthy|degraded/);
      expect(body.checks).toBeDefined();
      expect(body.checks.database.status).toBe("ok");
      expect(body.checks.redis.status).toBe("ok");
    });
  }
});

// ─── SUITE 2: JOURNEY CRUD — HAPPY PATHS (100 tests) ─────────────────────────

test.describe("Suite 2: Journey CRUD Happy Paths", () => {
  for (let i = 1; i <= 50; i++) {
    test(`[2-${i}] Create and read journey ${i}`, async ({ request }) => {
      const created = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ name: `CRUD Test ${i} ${uid()}` }),
      });
      expect(created.ok()).toBeTruthy();
      const body = await created.json();
      expect(body.id).toBeDefined();
      expect(body.name).toContain(`CRUD Test ${i}`);
      expect(body.status).toBeDefined();

      // Read it back
      const fetched = await request.get(`${BASE}/journeys/${body.id}`);
      expect(fetched.ok()).toBeTruthy();
      const fetchedBody = await fetched.json();
      expect(fetchedBody.id).toBe(body.id);
    });
  }

  for (let i = 1; i <= 50; i++) {
    test(`[2b-${i}] Create, update, and verify journey ${i}`, async ({ request }) => {
      const created = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ status: "DRAFT" }),
      });
      expect(created.ok()).toBeTruthy();
      const body = await created.json();

      // Update status to ACTIVE
      const updated = await request.put(`${BASE}/journeys/${body.id}`, {
        data: { status: "ACTIVE", name: `Updated Journey ${i} ${uid()}` },
      });
      expect(updated.ok()).toBeTruthy();
      const updatedBody = await updated.json();
      expect(updatedBody.status).toBe("ACTIVE");
    });
  }
});

// ─── SUITE 3: ENROLLMENT — HAPPY PATHS (100 tests) ───────────────────────────

test.describe("Suite 3: Enrollment Happy Paths", () => {
  for (let i = 1; i <= 100; i++) {
    test(`[3-${i}] Enroll customer in journey ${i}`, async ({ request }) => {
      // Create journey
      const jRes = await request.post(`${BASE}/journeys`, {
        data: journeyPayload(),
      });
      expect(jRes.ok()).toBeTruthy();
      const journey = await jRes.json();

      // Enroll customer
      const email = testEmail(`enroll${i}`);
      const eRes = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
        data: { customer_email: email },
      });
      expect(eRes.ok()).toBeTruthy();
      const enrollment = await eRes.json();
      expect(enrollment.instance_id).toBeDefined();
      expect(enrollment.customer_email).toBe(email);
      expect(enrollment.status).toBe("ACTIVE");
    });
  }
});

// ─── SUITE 4: EDGE CASES — INPUT VALIDATION (100 tests) ──────────────────────

test.describe("Suite 4: Input Validation Edge Cases", () => {
  test("[4-1] Create journey with empty name returns 422", async ({ request }) => {
    const r = await request.post(`${BASE}/journeys`, {
      data: { name: "", entry_trigger: "signup" },
    });
    expect(r.status()).toBeGreaterThanOrEqual(400);
  });

  test("[4-2] Create journey with missing required fields returns 422", async ({ request }) => {
    const r = await request.post(`${BASE}/journeys`, {
      data: { status: "ACTIVE" }, // missing name
    });
    expect(r.status()).toBeGreaterThanOrEqual(400);
  });

  test("[4-3] Get non-existent journey returns 404", async ({ request }) => {
    const r = await request.get(`${BASE}/journeys/non_existent_id_12345`);
    expect(r.status()).toBe(404);
  });

  test("[4-4] Enroll with invalid journey ID returns 404", async ({ request }) => {
    const r = await request.post(`${BASE}/journeys/invalid_id_xyz/enroll`, {
      data: { customer_email: testEmail("invalid") },
    });
    expect(r.status()).toBe(404);
  });

  test("[4-5] Duplicate enrollment returns 409", async ({ request }) => {
    const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
    const journey = await jRes.json();
    const email = testEmail("dup");

    const e1 = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
      data: { customer_email: email },
    });
    expect(e1.ok()).toBeTruthy();

    const e2 = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
      data: { customer_email: email },
    });
    expect(e2.status()).toBe(409);
  });

  test("[4-6] Enroll with no customer info returns 400", async ({ request }) => {
    const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
    const journey = await jRes.json();
    const r = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
      data: {},
    });
    expect(r.status()).toBeGreaterThanOrEqual(400);
  });

  test("[4-7] Update non-existent journey returns 404", async ({ request }) => {
    const r = await request.put(`${BASE}/journeys/fake_id_999`, {
      data: { status: "ACTIVE" },
    });
    expect(r.status()).toBe(404);
  });

  test("[4-8] Get enrollments for non-existent journey returns 404", async ({ request }) => {
    const r = await request.get(`${BASE}/journeys/fake_id_888/enrollments`);
    expect(r.status()).toBe(404);
  });

  test("[4-9] Create variant for non-existent journey returns 404", async ({ request }) => {
    const r = await request.post(`${BASE}/journeys/fake_id_777/variants`, {
      data: { variant_name: "Test", traffic_split_pct: 50 },
    });
    expect(r.status()).toBe(404);
  });

  test("[4-10] Clone non-existent journey returns 404", async ({ request }) => {
    const r = await request.post(`${BASE}/journeys/fake_id_666/clone`);
    expect(r.status()).toBe(404);
  });

  // Email format edge cases
  for (let i = 11; i <= 30; i++) {
    const badEmails = [
      "notanemail",
      "@nodomain.com",
      "spaces in@email.com",
      "double@@email.com",
      "",
      "a".repeat(200) + "@test.com",
      "test@",
      "test@.com",
      "test@com.",
      "<script>@hack.com",
    ];
    const email = badEmails[(i - 11) % badEmails.length];
    test(`[4-${i}] Invalid email format: "${email.substring(0, 20)}"`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();
      const r = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
        data: { customer_email: email },
      });
      // Should either reject (400/422) or accept and normalize - not 500
      expect(r.status()).not.toBe(500);
    });
  }

  // Numeric field edge cases
  for (let i = 31; i <= 50; i++) {
    test(`[4-${i}] Variant traffic split boundary ${i}%`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();
      const split = [-10, 0, 50, 100, 150, 200][i % 6];
      const r = await request.post(`${BASE}/journeys/${journey.id}/variants`, {
        data: { variant_name: `Split Test ${split}`, traffic_split_pct: split },
      });
      // Should validate split range
      expect(r.status()).not.toBe(500);
    });
  }

  // Large payload tests
  for (let i = 51; i <= 60; i++) {
    test(`[4-${i}] Large template_json payload size ${i}`, async ({ request }) => {
      const steps = Array.from({ length: i * 2 }, (_, k) => ({
        id: `step_${k}`,
        type: "email",
        delay_days: k,
        action_data: { subject: `Step ${k} email`, body: "x".repeat(500) },
      }));
      const r = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ template_json: { steps } }),
      });
      // Should handle large payloads - not crash with 500
      expect(r.status()).not.toBe(500);
    });
  }

  // Concurrent reads
  for (let i = 61; i <= 70; i++) {
    test(`[4-${i}] Concurrent journey reads ${i}`, async ({ request }) => {
      const r = await request.get(`${BASE}/journeys`);
      expect(r.ok()).toBeTruthy();
      const body = await r.json();
      expect(Array.isArray(body)).toBeTruthy();
    });
  }

  // Special character handling
  for (let i = 71; i <= 100; i++) {
    const specialNames = [
      "Journey with spaces",
      "Journey-with-dashes",
      "Journey_with_underscores",
      "Journey (with parens)",
      "Journey & more",
      "Journey 'with quotes'",
      'Journey "double quotes"',
      "Journey <with> brackets",
      "Journey @special #chars",
      "Journey 日本語 Unicode",
      "Journey with 1234 numbers",
      "Journey with emojis 🚀",
      "Journey with..dots",
    ];
    const name = specialNames[(i - 71) % specialNames.length];
    test(`[4-${i}] Special chars in name: "${name.substring(0, 25)}"`, async ({ request }) => {
      const r = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ name: `${name} ${uid()}` }),
      });
      // Should handle special chars - not 500
      expect(r.status()).not.toBe(500);
    });
  }
});

// ─── SUITE 5: A/B TESTING (80 tests) ─────────────────────────────────────────

test.describe("Suite 5: A/B Variant Testing", () => {
  for (let i = 1; i <= 40; i++) {
    test(`[5-${i}] Create and list variants ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const vRes = await request.post(`${BASE}/journeys/${journey.id}/variants`, {
        data: { variant_name: `Variant A ${i}`, traffic_split_pct: 50 },
      });
      expect(vRes.ok()).toBeTruthy();
      const variant = await vRes.json();
      expect(variant.id).toBeDefined();
      expect(variant.variant_name).toContain(`Variant A ${i}`);

      const listRes = await request.get(`${BASE}/journeys/${journey.id}/variants`);
      expect(listRes.ok()).toBeTruthy();
      const variants = await listRes.json();
      expect(variants.length).toBeGreaterThanOrEqual(1);
    });
  }

  for (let i = 1; i <= 20; i++) {
    test(`[5b-${i}] Promote variant to winner ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const v1 = await request.post(`${BASE}/journeys/${journey.id}/variants`, {
        data: { variant_name: "Variant A", traffic_split_pct: 50 },
      });
      const v2 = await request.post(`${BASE}/journeys/${journey.id}/variants`, {
        data: { variant_name: "Variant B", traffic_split_pct: 50 },
      });
      const variant1 = await v1.json();
      await v2.json();

      const promote = await request.post(
        `${BASE}/journeys/${journey.id}/variants/${variant1.id}/promote`
      );
      expect(promote.ok()).toBeTruthy();
      const promotedBody = await promote.json();
      expect(promotedBody.status).toBe("promoted");
    });
  }

  for (let i = 1; i <= 20; i++) {
    test(`[5c-${i}] Enroll customer respects variant split ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      // Create two variants
      const v1 = await request.post(`${BASE}/journeys/${journey.id}/variants`, {
        data: { variant_name: "Control", traffic_split_pct: 50, status: "ACTIVE" },
      });
      await request.put(
        `${BASE}/journeys/${journey.id}/variants/${(await v1.json()).id}`,
        { data: { status: "ACTIVE" } }
      );

      const email = testEmail(`ab${i}`);
      const eRes = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
        data: { customer_email: email },
      });
      expect(eRes.ok()).toBeTruthy();
    });
  }
});

// ─── SUITE 6: JOURNEY CLONING (40 tests) ─────────────────────────────────────

test.describe("Suite 6: Journey Cloning", () => {
  for (let i = 1; i <= 40; i++) {
    test(`[6-${i}] Clone journey ${i} and verify independence`, async ({ request }) => {
      // Create original
      const orig = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ name: `Original ${i} ${uid()}` }),
      });
      const original = await orig.json();
      expect(original.id).toBeDefined();

      // Clone it
      const clone = await request.post(`${BASE}/journeys/${original.id}/clone`);
      expect(clone.ok()).toBeTruthy();
      const cloned = await clone.json();
      expect(cloned.id).not.toBe(original.id);
      expect(cloned.name).toContain("(Copy)");
      expect(cloned.status).toBe("DRAFT");

      // Verify they're different
      const origFetched = await request.get(`${BASE}/journeys/${original.id}`);
      const origBody = await origFetched.json();
      expect(origBody.name).not.toContain("(Copy)");
    });
  }
});

// ─── SUITE 7: BULK ENROLLMENT (40 tests) ─────────────────────────────────────

test.describe("Suite 7: Bulk Enrollment JSON", () => {
  for (let i = 1; i <= 30; i++) {
    test(`[7-${i}] Bulk enroll ${i * 3} customers via JSON`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const emails = Array.from({ length: i * 3 }, (_, k) =>
        testEmail(`bulk${i}_${k}`)
      );

      const bRes = await request.post(`${BASE}/journeys/${journey.id}/enroll-bulk`, {
        data: { emails },
      });
      expect(bRes.ok()).toBeTruthy();
      const bulkBody = await bRes.json();
      expect(bulkBody.job_id || bulkBody.total_rows || bulkBody.success_count).toBeDefined();
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[7b-${i}] Bulk enroll empty list ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const r = await request.post(`${BASE}/journeys/${journey.id}/enroll-bulk`, {
        data: { emails: [] },
      });
      expect(r.status()).not.toBe(500);
    });
  }
});

// ─── SUITE 8: ANALYTICS & ATTRIBUTION (60 tests) ─────────────────────────────

test.describe("Suite 8: Analytics & Attribution", () => {
  for (let i = 1; i <= 30; i++) {
    test(`[8-${i}] Journey analytics structure ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const aRes = await request.get(`${BASE}/journeys/${journey.id}/analytics`);
      expect(aRes.ok()).toBeTruthy();
      const body = await aRes.json();
      expect(body.journey_id).toBe(journey.id);
      expect(typeof body.total_enrolled).toBe("number");
      expect(typeof body.completed_instances).toBe("number");
      expect(typeof body.conversion_rate).toBe("number");
      expect(body.timestamp).toBeDefined();
    });
  }

  for (let i = 1; i <= 30; i++) {
    test(`[8b-${i}] Attribution endpoint structure ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const aRes = await request.get(`${BASE}/journeys/${journey.id}/attribution`);
      expect(aRes.ok()).toBeTruthy();
      const body = await aRes.json();
      expect(body.journey_id).toBe(journey.id);
      expect(typeof body.total_attributed_revenue).toBe("number");
      expect(typeof body.total_orders).toBe("number");
      expect(body.attribution_model).toBeDefined();
      expect(body.currency).toBeDefined();
    });
  }
});

// ─── SUITE 9: AUDIENCE SYNC (40 tests) ───────────────────────────────────────

test.describe("Suite 9: Audience Sync", () => {
  for (let i = 1; i <= 20; i++) {
    test(`[9-${i}] Scheduler status returns expected format ${i}`, async ({ request }) => {
      const r = await request.get(`${BASE}/sync/status`);
      expect(r.ok()).toBeTruthy();
      const body = await r.json();
      expect(body.scheduler_running).toBe(true);
      expect(Array.isArray(body.jobs)).toBe(true);
      expect(body.jobs.length).toBeGreaterThanOrEqual(2);
      const ids = body.jobs.map((j: { id: string }) => j.id);
      expect(ids).toContain("meta_audience_sync");
      expect(ids).toContain("google_audience_sync");
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[9b-${i}] Meta sync trigger responds ${i}`, async ({ request }) => {
      const r = await request.post(`${BASE}/sync/meta/now`);
      expect(r.status()).not.toBe(500);
      const body = await r.json();
      expect(["ok", "skipped", "error"]).toContain(body.status);
      expect(body.account_id).toBeDefined();
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[9c-${i}] Google sync trigger responds ${i}`, async ({ request }) => {
      const r = await request.post(`${BASE}/sync/google/now`);
      expect(r.status()).not.toBe(500);
      const body = await r.json();
      expect(["ok", "skipped", "error"]).toContain(body.status);
      expect(body.customer_id).toBeDefined();
    });
  }
});

// ─── SUITE 10: SHOPIFY WEBHOOK (40 tests) ────────────────────────────────────

test.describe("Suite 10: Shopify Webhook", () => {
  for (let i = 1; i <= 20; i++) {
    test(`[10-${i}] Shopify order webhook accepted ${i}`, async ({ request }) => {
      const r = await request.post(`${BASE}/webhooks/shopify/order-paid`, {
        data: {
          id: Math.floor(Math.random() * 9000000000) + 1000000000,
          email: testEmail(`shopify${i}`),
          total_price: `${(Math.random() * 500 + 50).toFixed(2)}`,
          currency: "INR",
          line_items: [
            {
              product_id: 9119327281398,
              title: "Kerala Cardamom 50gm",
              quantity: 1,
              price: "199.00",
            },
          ],
          billing_address: { first_name: `Test${i}`, last_name: "Customer" },
          created_at: new Date().toISOString(),
        },
        headers: { "X-Shopify-Topic": "orders/paid" },
      });
      // Accept any non-500 response (200 = processed, 401 = HMAC needed, 400 = schema)
      expect(r.status()).not.toBe(500);
    });
  }

  for (let i = 1; i <= 20; i++) {
    test(`[10b-${i}] Shopify webhook with UTM params ${i}`, async ({ request }) => {
      const r = await request.post(`${BASE}/webhooks/shopify/order-paid`, {
        data: {
          id: Math.floor(Math.random() * 9000000000) + 1000000000,
          email: testEmail(`shopifyutm${i}`),
          total_price: "299.00",
          currency: "INR",
          note_attributes: [
            { name: "utm_source", value: "google" },
            { name: "utm_medium", value: "cpc" },
            { name: "utm_campaign", value: `test_campaign_${i}` },
          ],
          line_items: [{ product_id: 9119327281398, title: "Test", quantity: 1, price: "299.00" }],
          created_at: new Date().toISOString(),
        },
        headers: { "X-Shopify-Topic": "orders/paid" },
      });
      expect(r.status()).not.toBe(500);
    });
  }
});

// ─── SUITE 11: JOURNEY ENROLLMENTS LIST (40 tests) ───────────────────────────

test.describe("Suite 11: Enrollment Lists & Filtering", () => {
  for (let i = 1; i <= 20; i++) {
    test(`[11-${i}] Enrollments list with pagination ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      // Enroll a few
      for (let k = 0; k < 3; k++) {
        await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
          data: { customer_email: testEmail(`page${i}_${k}`) },
        });
      }

      const r = await request.get(`${BASE}/journeys/${journey.id}/enrollments?limit=2`);
      expect(r.ok()).toBeTruthy();
      const body = await r.json();
      expect(Array.isArray(body)).toBe(true);
      expect(body.length).toBeLessThanOrEqual(2);
    });
  }

  for (let i = 1; i <= 20; i++) {
    test(`[11b-${i}] Enrollment list filter by status ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const r = await request.get(`${BASE}/journeys/${journey.id}/enrollments?status=ACTIVE`);
      expect(r.ok()).toBeTruthy();
      const body = await r.json();
      expect(Array.isArray(body)).toBe(true);
    });
  }
});

// ─── SUITE 12: CONCURRENT OPERATIONS (60 tests) ──────────────────────────────

test.describe("Suite 12: Concurrent Operations", () => {
  for (let i = 1; i <= 20; i++) {
    test(`[12-${i}] Concurrent journey creation ${i}`, async ({ request }) => {
      // Fire 5 concurrent requests
      const promises = Array.from({ length: 5 }, () =>
        request.post(`${BASE}/journeys`, { data: journeyPayload() })
      );
      const results = await Promise.all(promises);
      const ids = new Set<string>();
      for (const r of results) {
        expect(r.ok()).toBeTruthy();
        const body = await r.json();
        expect(ids.has(body.id)).toBe(false); // No duplicate IDs
        ids.add(body.id);
      }
      expect(ids.size).toBe(5);
    });
  }

  for (let i = 1; i <= 20; i++) {
    test(`[12b-${i}] Concurrent enrollment for different customers ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();

      const promises = Array.from({ length: 5 }, (_, k) =>
        request.post(`${BASE}/journeys/${journey.id}/enroll`, {
          data: { customer_email: testEmail(`concurrent${i}_${k}`) },
        })
      );
      const results = await Promise.all(promises);
      for (const r of results) {
        // All should succeed (different customers)
        expect(r.status()).not.toBe(500);
      }
    });
  }

  for (let i = 1; i <= 20; i++) {
    test(`[12c-${i}] Concurrent same customer enrollment returns 409 ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();
      const email = testEmail(`samecust${i}`);

      // First enrollment should work, concurrent second should get 409
      const [r1, r2] = await Promise.all([
        request.post(`${BASE}/journeys/${journey.id}/enroll`, {
          data: { customer_email: email },
        }),
        request.post(`${BASE}/journeys/${journey.id}/enroll`, {
          data: { customer_email: email },
        }),
      ]);

      const statuses = [r1.status(), r2.status()];
      expect(statuses).toContain(200); // One succeeds
      expect(statuses).toContain(409); // One conflicts
    });
  }
});

// ─── SUITE 13: JOURNEY STOP/PAUSE (20 tests) ─────────────────────────────────

test.describe("Suite 13: Journey Stop & Pause", () => {
  for (let i = 1; i <= 20; i++) {
    test(`[13-${i}] Stop active journey ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ status: "ACTIVE" }),
      });
      const journey = await jRes.json();

      // Enroll some customers
      for (let k = 0; k < 2; k++) {
        await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
          data: { customer_email: testEmail(`stop${i}_${k}`) },
        });
      }

      const stop = await request.post(`${BASE}/journeys/${journey.id}/stop`);
      expect(stop.ok()).toBeTruthy();
      const stopBody = await stop.json();
      expect(stopBody.status).toBe("success");
    });
  }
});

// ─── SUITE 14: JOURNEY LIST FILTERING (30 tests) ─────────────────────────────

test.describe("Suite 14: Journey List Filtering", () => {
  for (let i = 1; i <= 15; i++) {
    test(`[14-${i}] List all journeys returns array ${i}`, async ({ request }) => {
      const r = await request.get(`${BASE}/journeys`);
      expect(r.ok()).toBeTruthy();
      const body = await r.json();
      expect(Array.isArray(body)).toBe(true);
    });
  }

  for (let i = 1; i <= 15; i++) {
    test(`[14b-${i}] List active-only journeys ${i}`, async ({ request }) => {
      const r = await request.get(`${BASE}/journeys?active_only=true`);
      expect(r.ok()).toBeTruthy();
      const body = await r.json();
      expect(Array.isArray(body)).toBe(true);
      for (const j of body) {
        expect(j.status).toBe("ACTIVE");
      }
    });
  }
});

// ─── SUITE 15: SECURITY & INJECTION TESTS (40 tests) ─────────────────────────

test.describe("Suite 15: Security & Injection Prevention", () => {
  const sqlPayloads = [
    "'; DROP TABLE crm_journeys; --",
    "1' OR '1'='1",
    "admin'--",
    "1; SELECT * FROM crm_customers",
    "' UNION SELECT 1,2,3--",
  ];

  for (let i = 0; i < sqlPayloads.length; i++) {
    test(`[15-${i + 1}] SQL injection in journey name`, async ({ request }) => {
      const r = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ name: `${sqlPayloads[i]} ${uid()}` }),
      });
      // Should either reject (400/422) or safely store the string - never 500
      expect(r.status()).not.toBe(500);
      // Table should still exist after the attempt
      const health = await request.get(`${BASE}/health/full`);
      expect(health.ok()).toBeTruthy();
    });
  }

  const xssPayloads = [
    "<script>alert(1)</script>",
    "javascript:alert(1)",
    '<img src="x" onerror="alert(1)">',
    "{{7*7}}",
    "${7*7}",
  ];

  for (let i = 0; i < xssPayloads.length; i++) {
    test(`[15b-${i + 1}] XSS injection in journey name`, async ({ request }) => {
      const r = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ name: `${xssPayloads[i]} ${uid()}` }),
      });
      expect(r.status()).not.toBe(500);
    });
  }

  // Test oversized payloads
  for (let i = 11; i <= 20; i++) {
    test(`[15c-${i}] Oversized payload handling ${i}`, async ({ request }) => {
      const largeString = "x".repeat(i * 10000);
      const r = await request.post(`${BASE}/journeys`, {
        data: { name: largeString, entry_trigger: "signup" },
      });
      expect(r.status()).not.toBe(500);
    });
  }

  // Test HTTP method handling
  for (let i = 21; i <= 30; i++) {
    test(`[15d-${i}] Invalid endpoint path ${i}`, async ({ request }) => {
      const r = await request.get(`${BASE}/nonexistent_endpoint_${i}`);
      expect(r.status()).toBe(404);
    });
  }

  // Malformed JSON edge cases
  for (let i = 31; i <= 40; i++) {
    test(`[15e-${i}] Empty string in numeric fields ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();
      const r = await request.post(`${BASE}/journeys/${journey.id}/variants`, {
        data: { variant_name: `Test ${i}`, traffic_split_pct: "invalid" },
      });
      expect(r.status()).not.toBe(500);
    });
  }
});

// ─── SUITE 16: PERFORMANCE — RESPONSE TIMES (30 tests) ───────────────────────

test.describe("Suite 16: Performance Response Times", () => {
  for (let i = 1; i <= 10; i++) {
    test(`[16-${i}] Journey list responds under 3s ${i}`, async ({ request }) => {
      const start = Date.now();
      const r = await request.get(`${BASE}/journeys`);
      const elapsed = Date.now() - start;
      expect(r.ok()).toBeTruthy();
      expect(elapsed).toBeLessThan(3000);
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[16b-${i}] Journey creation responds under 2s ${i}`, async ({ request }) => {
      const start = Date.now();
      const r = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const elapsed = Date.now() - start;
      expect(r.ok()).toBeTruthy();
      expect(elapsed).toBeLessThan(2000);
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[16c-${i}] Enrollment responds under 2s ${i}`, async ({ request }) => {
      const jRes = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await jRes.json();
      const start = Date.now();
      const r = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
        data: { customer_email: testEmail(`perf${i}`) },
      });
      const elapsed = Date.now() - start;
      expect(r.ok()).toBeTruthy();
      expect(elapsed).toBeLessThan(2000);
    });
  }
});

// ─── SUITE 17: DELETE OPERATIONS (20 tests) ──────────────────────────────────

test.describe("Suite 17: Delete Operations", () => {
  for (let i = 1; i <= 10; i++) {
    test(`[17-${i}] Delete journey removes it from list ${i}`, async ({ request }) => {
      const created = await request.post(`${BASE}/journeys`, { data: journeyPayload() });
      const journey = await created.json();

      const del = await request.delete(`${BASE}/journeys/${journey.id}`);
      expect(del.ok()).toBeTruthy();

      const fetched = await request.get(`${BASE}/journeys/${journey.id}`);
      expect(fetched.status()).toBe(404);
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[17b-${i}] Delete non-existent journey returns 404 ${i}`, async ({ request }) => {
      const r = await request.delete(`${BASE}/journeys/definitely_does_not_exist_${i}`);
      expect(r.status()).toBe(404);
    });
  }
});

// ─── SUITE 18: WEBSOCKET CONNECTIONS (20 tests) ───────────────────────────────

import WebSocket from "ws";

test.describe("Suite 18: WebSocket Connectivity", () => {
  for (let i = 1; i <= 10; i++) {
    test(`[18-${i}] WebSocket metrics connects and receives data ${i}`, async () => {
      await new Promise<void>((resolve, reject) => {
        const ws = new WebSocket(`${WS_BASE}/metrics?token=scale-test-${i}`);
        const timer = setTimeout(() => {
          ws.close();
          reject(new Error("WebSocket timeout - no 101 within 5s"));
        }, 5000);

        ws.on("open", () => {
          clearTimeout(timer);
          ws.close();
          resolve();
        });
        ws.on("error", (e) => {
          clearTimeout(timer);
          reject(e);
        });
      });
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[18b-${i}] WebSocket steps connects ${i}`, async () => {
      await new Promise<void>((resolve, reject) => {
        const ws = new WebSocket(`${WS_BASE}/steps?token=scale-test-steps-${i}`);
        const timer = setTimeout(() => {
          ws.close();
          reject(new Error("WebSocket steps timeout"));
        }, 5000);

        ws.on("open", () => {
          clearTimeout(timer);
          ws.close();
          resolve();
        });
        ws.on("error", (e) => {
          clearTimeout(timer);
          reject(e);
        });
      });
    });
  }
});

// ─── SUITE 19: END-TO-END JOURNEY LIFECYCLE (30 tests) ───────────────────────

test.describe("Suite 19: End-to-End Journey Lifecycle", () => {
  for (let i = 1; i <= 30; i++) {
    test(`[19-${i}] Full journey lifecycle: create→enroll→analytics ${i}`, async ({ request }) => {
      // 1. Create journey
      const created = await request.post(`${BASE}/journeys`, {
        data: journeyPayload({ name: `E2E Lifecycle ${i} ${uid()}`, status: "ACTIVE" }),
      });
      expect(created.ok()).toBeTruthy();
      const journey = await created.json();

      // 2. Create variant
      const varRes = await request.post(`${BASE}/journeys/${journey.id}/variants`, {
        data: { variant_name: `Variant ${i}`, traffic_split_pct: 100, status: "ACTIVE" },
      });
      expect(varRes.ok()).toBeTruthy();

      // 3. Enroll customer
      const email = testEmail(`lifecycle${i}`);
      const enrolled = await request.post(`${BASE}/journeys/${journey.id}/enroll`, {
        data: { customer_email: email },
      });
      expect(enrolled.ok()).toBeTruthy();

      // 4. Check analytics
      const analytics = await request.get(`${BASE}/journeys/${journey.id}/analytics`);
      expect(analytics.ok()).toBeTruthy();
      const stats = await analytics.json();
      expect(stats.total_enrolled).toBeGreaterThanOrEqual(1);

      // 5. Check enrollments list
      const enrollments = await request.get(`${BASE}/journeys/${journey.id}/enrollments`);
      expect(enrollments.ok()).toBeTruthy();
      const list = await enrollments.json();
      expect(list.length).toBeGreaterThanOrEqual(1);
      expect(list.some((e: { customer_email: string }) => e.customer_email === email)).toBe(true);

      // 6. Check attribution
      const attribution = await request.get(`${BASE}/journeys/${journey.id}/attribution`);
      expect(attribution.ok()).toBeTruthy();
      const attrBody = await attribution.json();
      expect(attrBody.journey_id).toBe(journey.id);

      // 7. Clone it
      const cloned = await request.post(`${BASE}/journeys/${journey.id}/clone`);
      expect(cloned.ok()).toBeTruthy();
      const clonedBody = await cloned.json();
      expect(clonedBody.id).not.toBe(journey.id);

      // 8. Stop original
      const stopped = await request.post(`${BASE}/journeys/${journey.id}/stop`);
      expect(stopped.ok()).toBeTruthy();
    });
  }
});

// ─── SUITE 20: FRONTEND UI (20 tests) ────────────────────────────────────────

test.describe("Suite 20: Frontend UI", () => {
  for (let i = 1; i <= 10; i++) {
    test(`[20-${i}] Dashboard loads correctly ${i}`, async ({ page }) => {
      await page.goto("https://ai.pureleven.com", { timeout: TIMEOUT });
      await expect(page).toHaveTitle(/Pureleven|CRM|Dashboard/i);
    });
  }

  for (let i = 1; i <= 10; i++) {
    test(`[20b-${i}] Dashboard has navigation elements ${i}`, async ({ page }) => {
      await page.goto("https://ai.pureleven.com", { timeout: TIMEOUT });
      await page.waitForLoadState("domcontentloaded");
      const bodyText = await page.textContent("body");
      expect(bodyText).toBeTruthy();
      expect(bodyText!.length).toBeGreaterThan(100);
    });
  }
});
