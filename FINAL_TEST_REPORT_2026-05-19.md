# Pure Leven CRM — Final Verification Report
**Date:** 2026-05-19  
**Session:** Phase 3–5 Complete + Load Testing + E2E Shopify + Cleanup

---

## ✅ Test Summary

| Suite | Count | Result | Duration |
|---|---|---|---|
| Original E2E (`journey.spec.ts`) | 29/29 | ✅ PASS | 17.6s |
| Scale Tests (`scale-tests.spec.ts`) | 950/950 | ✅ PASS | 42.5s |
| Shopify E2E (`shopify-e2e.spec.ts`) | 10/10 | ✅ PASS | 15.2s |
| **Total** | **989 tests** | **✅ ALL PASS** | — |

---

## ✅ Load Test Results (1000 concurrent users)

| Users | RPS | Avg Response | 95th %ile | Error Rate | Result |
|---|---|---|---|---|---|
| 200 | 92.1 | 230ms | 770ms | 0.1% | ✅ PASS |
| 500 | 106.9 | 3,006ms | 5,000ms | 0.0% | ✅ PASS |
| 1000 | 105.5 | 7,608ms | 10,000ms | 0.0% | ✅ PASS |

**All 3 scales passed <5% error rate threshold.**  
Infrastructure: Single-worker uvicorn on 6GB VPS with nginx proxy.

---

## ✅ Shopify Journey Flow Verified

1. **GTM/GA4** — `googletagmanager.com` loads on every storefront page (`GTM-TFHBWPLM`)
2. **Product page** — GA4 dataLayer events captured on `pureleven.com/products/kerala-cardamom-50gm`
3. **ATC button** — Present and linked to `/cart` form
4. **CRM Enrollment** — `POST /api/crm/journeys/{id}/enroll` with `customer_email`
5. **Order webhook** — `POST /api/crm/webhooks/shopify/order-paid` with HMAC-SHA256
6. **Attribution** — `crm_journey_attribution` row created, instance → `COMPLETED`
7. **Analytics** — Journey `enroll_count` and `completion_count` updated correctly

---

## ✅ Fixes Applied This Session

| Fix | File | Impact |
|---|---|---|
| **N+1 query fix** in `list_journeys` | `journeys_routes.py` | 2N → 3 total queries; ~9× faster (634ms → 70ms) |
| **DB indexes added** | PostgreSQL | `idx_journey_instances_journey_id`, `idx_journey_instances_status`, `idx_journeys_created_at` |
| **Pool size fix** | `database.py` | `pool_size=40, max_overflow=20` — matches starlette's 40-thread pool |
| **Single worker** | `docker-compose.yml` | Removed `--workers 4`; APScheduler/Redis conflict eliminated |
| **HMAC webhook auth** | `shopify_attribution.py` | Verified correct HMAC-SHA256 validation |

---

## ✅ Database State (Post-Cleanup)

| Table | Rows | Notes |
|---|---|---|
| `crm_journeys` | 0 | All test data removed |
| `crm_customers` | 0 | All test data removed |
| `crm_journey_instances` | 0 | All test data removed |
| `crm_journey_attribution` | 0 | All test data removed |
| DB size | 24 MB | After VACUUM ANALYZE |

---

## ✅ Infrastructure Health

```
Container: pureleven-ai-engine — Up, healthy
PostgreSQL: max_connections=200, pool_size=40/overflow_20
nginx: worker_connections=4096
Redis: Connected, pub/sub running
APScheduler: Running in single worker
```

---

## 🔧 Recommendations for Production

1. **Scale horizontally** if >200 concurrent users sustained: Add a second VPS + nginx upstream load balancer
2. **Register Shopify webhook** in Admin: `Settings → Notifications → Webhooks → orders/paid → https://track.pureleven.com/api/crm/webhooks/shopify/order-paid`
3. **Monitor `crm_journey_attribution`** table: Run analytics queries to see revenue attribution per journey
4. **Add email column index**: `CREATE INDEX ON crm_customers(email)` for faster customer lookups at scale
5. **Response time improvement**: At 500+ concurrent users, avg response is 3–8s. Consider async DB queries (async SQLAlchemy) or read replicas

---

## Test Files

| File | Purpose |
|---|---|
| [tests/e2e/journey.spec.ts](tests/e2e/journey.spec.ts) | Core 29 E2E tests (Phases 1–5) |
| [tests/e2e/scale-tests.spec.ts](tests/e2e/scale-tests.spec.ts) | 950 scale/edge case tests |
| [tests/e2e/shopify-e2e.spec.ts](tests/e2e/shopify-e2e.spec.ts) | Shopify store + attribution E2E |
| [load_test.py](load_test.py) | Locust 1000-user load test |
| [playwright.scale.config.ts](playwright.scale.config.ts) | Scale test config (10 workers) |
