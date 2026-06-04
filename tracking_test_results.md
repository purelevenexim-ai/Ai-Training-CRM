# Tracking Test Results

Date: 2026-05-24

This file records pre-fix validation results. No conversion fixes had been applied when these tests were run.

## Runtime Baseline

| Check | Result |
| --- | --- |
| Root CRM container | `pureleven-ai-engine` running on `127.0.0.1:8000` |
| Postgres container | `pureleven-postgres` running database `pureleven` |
| Active WhatsApp/anu-login service | `anu-login-backend.service` running uvicorn on `127.0.0.1:8010` |
| Conflicting legacy service | `pureleven-whatsapp-crm.service` failing/restarting and also attempting 8010 |
| `track.pureleven.com/api/` | Proxies to root CRM on 8000 |
| `track.pureleven.com/` | Proxies to GTM Cloud Run root |
| `api.pureleven.com/` | Proxies to Plunk on 8080 |

## Route Probes

| Probe | Result | Interpretation |
| --- | --- | --- |
| `GET http://127.0.0.1:8000/api/shopify/webhook/order-created` | 405 | Route exists and is POST-only |
| `GET http://127.0.0.1:8000/api/shopify/webhook/order-paid` | 405 | Route exists and is POST-only |
| `GET http://127.0.0.1:8000/api/shopify/webhook/order-fulfilled` | 405 | Route exists and is POST-only |
| `GET http://127.0.0.1:8000/api/shopify/webhooks/customers/create` | 405 | Route exists and is POST-only |
| `GET http://127.0.0.1:8000/api/shopify/webhooks/customers/update` | 405 | Route exists and is POST-only |
| `GET http://127.0.0.1:8000/api/shopify/webhooks/orders/create` | 405 | Route exists and is POST-only |
| `GET http://127.0.0.1:8000/api/shopify/webhooks/orders/fulfilled` | 405 | Route exists and is POST-only |
| `GET http://127.0.0.1:8000/api/shopify/webhooks/fulfillments/create` | 404 | Candidate route not present |
| `GET http://127.0.0.1:8000/api/crm/webhooks/shopify` | 405 | Unified CRM Shopify webhook route exists |
| Public `api.pureleven.com/api/shopify/webhook/order-*` | 404 | Public host reaches Plunk, not tracking app |

## Shopify Webhook Registration Snapshot

| Topic | Address | Result |
| --- | --- | --- |
| `orders/create` | `https://api.pureleven.com/api/shopify/webhook/order-created` | Misrouted to Plunk |
| `orders/paid` | `https://api.pureleven.com/api/shopify/webhook/order-paid` | Misrouted to Plunk |
| `orders/fulfilled` | `https://api.pureleven.com/api/shopify/webhook/order-fulfilled` | Misrouted to Plunk |
| `orders/cancelled` | `https://track.pureleven.com/api/crm/webhooks/shopify/order-cancelled` | Wrong route shape |
| `carts/create` | `https://track.pureleven.com/api/crm/webhooks/shopify/cart-create` | Wrong route shape |
| `carts/update` | `https://track.pureleven.com/api/crm/webhooks/shopify/cart-update` | Wrong route shape |
| `checkouts/create` | `https://track.pureleven.com/api/crm/webhooks/shopify/checkout-create` | Wrong route shape |
| `checkouts/update` | `https://track.pureleven.com/api/crm/webhooks/shopify/checkout-update` | Wrong route shape |
| `customers/create` | `https://track.pureleven.com/api/crm/webhooks/shopify/customer-create` | Wrong route shape |
| `customers/update` | `https://track.pureleven.com/api/crm/webhooks/shopify/customer-update` | Wrong route shape |

## Postgres Tracking Health

Recent root CRM query results for the last 7 days:

| Metric | Result |
| --- | --- |
| Orders | 253 |
| Orders with `gclid` | 0 |
| Orders with `fbclid` | 0 |
| Orders with `utm_source` | 0 |
| Orders marked `offline_conversion_sent` | 0 |
| Orders marked `capi_suppressed` | 250 |
| Recent `page_view` events | 1 |
| Recent GA4/audience events | 50 |
| Recent conversion feed rows | 0 |
| `crm_offline_conversions` table | Missing |

Fraud score distribution:

| Fraud score | Orders |
| --- | --- |
| 65 | 250 |
| 30 | 1 |
| 0 | 2 |

## Storefront HTML Checks

| Marker | Live storefront result |
| --- | --- |
| `G-3FRSK7TEN2` | Present |
| `G-3JXJPCDV72` | Present |
| `audience-tracking` | Present on product page |
| `pl_product_interest` | Present on product page |
| `pl_add_to_cart_interest` | Present on product page |
| `track.pureleven.com/api/crm/events/ga4` | Present on product page |
| `crm-attribution.js` | Missing from live HTML |
| `track.pureleven.com/api/crm/events/page_view` | Missing from live HTML |
| `track.pureleven.com/api/crm/identify` | Missing from live HTML |

Active Shopify main theme found via Admin API:

- Theme ID: `188150120741`
- Name: `Production (Quick Checkout) v1`
- Role: `main`

The Admin asset fetch for `layout/theme.liquid` returned 404 during the audit, so direct raw storefront HTML remains the strongest evidence for live marker presence/absence.

## Anu-Login SQLite Checks

Active DB path: `/opt/anu-login-backend/backend/data/anu_login.sqlite3`.

Tables present include:

- `event_logs`
- `journey_customers`
- `journey_engagement_events`
- `journey_messages`
- `whatsapp_message_status_events`
- supporting CRM/journey tables

Live row counts:

| Table | Rows |
| --- | --- |
| `journey_customers` | 0 |
| `event_logs` | 0 |
| `journey_messages` | 0 |
| `journey_engagement_events` | 0 |

Schema drift found:

- Code expects attribution columns such as `meta_lead_id`, `google_gclid`, and `fbc`.
- The live `journey_customers` schema does not contain those columns.

## Production Sender Module Checks

| Module | Production status | Notes |
| --- | --- | --- |
| `/opt/pureleven/ai-engine/app/meta_capi.py` | Present | Uses Graph v20.0; sends purchase; missing `fbp`, `external_id`, `event_source_url` |
| `/opt/pureleven/ai-engine/app/gads_conversion.py` | Present | Uses Google Ads API v20 `uploadClickConversions`; no clear event-name-to-conversion-action mapping |

## Pre-Fix Conclusion

The system cannot currently prove successful server-side purchase conversion delivery to Meta, Google Ads, or GA4. The highest-confidence blocker is webhook routing: Shopify purchase webhooks are pointed at a public host that reaches Plunk and returns 404. The second blocker is missing browser attribution capture, which explains the complete absence of recent click IDs and UTMs on orders.

Automated tests should be added around webhook route compatibility, order fan-out gating, fraud suppression, and destination payload construction before or alongside fixes.

## Post-Fix Validation

### Automated Tests

Command run from the repo root with a temporary Python 3.11 venv under `/tmp`:

```bash
/tmp/pureleven-tracking-test-venv/bin/python -m pytest tests/test_tracking_core.py -q
```

Result:

- `7 passed`
- `1 warning`: Pydantic V2 deprecation warning for class-based `Config` in existing schemas.

### Shopify Webhook Readback

Post-fix Shopify Admin API readback:

- Webhooks registered: 13
- `BROKEN_ADDRESS_COUNT`: 0
- No webhook address remains on `api.pureleven.com`.
- No webhook address remains on suffixed `/api/crm/webhooks/shopify/...` paths.

Corrected order state:

| Topic | CRM endpoint | Direct/journey endpoint |
| --- | --- | --- |
| `orders/create` | `https://track.pureleven.com/api/crm/webhooks/shopify` | `https://track.pureleven.com/api/shopify/webhook/order-created` |
| `orders/paid` | `https://track.pureleven.com/api/crm/webhooks/shopify` | `https://track.pureleven.com/api/shopify/webhook/order-paid` |
| `orders/fulfilled` | `https://track.pureleven.com/api/crm/webhooks/shopify` | `https://track.pureleven.com/api/shopify/webhook/order-fulfilled` |

### Backend Health

After targeted live patch and `pureleven-ai-engine` restart:

- `/api/health`: 200
- `/api/crm/tracking/status`: 200
- `docker exec pureleven-ai-engine python -m py_compile /app/app/crm_routes.py`: passed

### Enriched Page View Probe

Public endpoint test:

```bash
POST https://track.pureleven.com/api/crm/events/page_view
```

Probe result:

- API response: `{"status":"recorded"}`
- Postgres stored: `gclid`, `fbclid`, `fbp`, `fbc`, `ga_client_id`, `ga_session_id`, and `page_url`.

Recent page_view check after the fix:

- `page_views_1h`: 7
- `non_audit_page_views_1h`: 5
- `with_gclid_1h`: 4
- `with_fbclid_1h`: 2

### Storefront Asset Propagation

- Product page HTML contains `crm-attribution.js`.
- Homepage raw HTML still showed an older cached render during verification, but Postgres received non-audit homepage `page_view` events after the fix.
- Shopify source asset `assets/crm-attribution.js` was updated through Admin GraphQL.
- CDN unversioned/new-query asset URLs served the updated JavaScript markers: `__PL_CRM_ATTRIBUTION_LOADED__`, `captureGaClientId`, `pl_fbc`, and `ga_client_id`.
- Cached product HTML still referenced an older versioned CDN URL during verification; monitor Shopify cache propagation.

### Remaining Validation Gap

No new real paid order was forced during this implementation pass. Meta CAPI, Google Ads, and GA4 MP purchase delivery must be validated on the next real `orders/paid` webhook or via a controlled Shopify test order.
