# Tracking Code Changes

Date: 2026-05-24

## Pre-Fix State

No conversion tracking fixes had been applied when the audit artifacts were first created.

## Planned Changes

| Priority | Area | Planned change | Reason |
| --- | --- | --- | --- |
| P0 | Shopify webhooks | Re-register order webhooks from `api.pureleven.com` to `track.pureleven.com` or route the existing API host paths to the root CRM | Restore `orders/paid` delivery to purchase fan-out code |
| P0 | Shopify webhooks | Fix cart, checkout, customer, and cancelled-order webhook paths or add compatibility routes | Stop 404s on currently registered suffixed paths |
| P0 | Storefront attribution | Deploy `crm-attribution.js` to the active Shopify theme | Capture `gclid`, `fbclid`, UTMs, session ID, page views, and identity events |
| P1 | Fraud scoring | Normalize Shopify payload identity/address fields and relax suppression for missing optional data | Prevent valid orders from being blocked with score 65 |
| P1 | Conversion retry/logging | Add durable queue/logging for Meta, Google Ads, and GA4 responses | Make delivery provable and replay-safe |
| P1 | Meta CAPI payload | Add `fbp`, canonical `fbc`, `external_id`, `event_source_url`, and test-event support | Improve match quality and diagnostics |
| P1 | Google Ads payload | Add conversion action mapping and partial-failure logging | Separate purchase/delivery conversions and catch API errors |
| P1 | GA4 MP payload | Use GA client/session identifiers instead of email as `client_id` | Correct session stitching and avoid PII-like identifiers |
| P2 | anu-login backend | Migrate or retire inactive tracking DB path | Avoid maintaining a dead parallel tracking stack |
| P2 | GA4 duplicate | Resolve or document service-backed `G-3JXJPCDV72` | Reduce duplicate/confusing analytics data |

## Applied Changes

| Time | File/config | Change | Verification |
| --- | --- | --- | --- |
| 2026-05-24 pre-fix | Documentation | Created audit artifacts only | No application behavior changed |
| 2026-05-24 | `tests/test_tracking_core.py` | Added focused pytest coverage for fraud gating, Meta CAPI payload handoff, Google Ads payload handoff, and GA4 MP client ID behavior | `7 passed`, 1 Pydantic deprecation warning |
| 2026-05-24 | `crm_routes.py` | GA4 MP purchase now prefers `ga_client_id`, `_ga_client_id`, `client_id`, or `session_id` instead of email as `client_id`; includes `session_id` when present | Unit test added and passed |
| 2026-05-24 | `crm_routes.py` | Fraud score now gives reduced penalties for missing optional identity/address fields when click attribution exists; order webhook scores enriched order data | Unit test added and passed |
| 2026-05-24 | `crm_routes.py` | Page-view schema and storage now preserve `fbp`, `fbc`, `ga_client_id`, `ga_session_id`, `page_url`, and `page_title`; attribution lookup returns those fields | Enriched public page_view probe stored all fields in Postgres |
| 2026-05-24 | `crm_routes.py` on VPS | Applied only the tested tracking hunks to `/opt/pureleven/ai-engine/app/crm_routes.py`; created timestamped backup before write | `python -m py_compile` passed; container restarted; `/api/crm/tracking/status` returned 200 |
| 2026-05-24 | `assets/crm-attribution.js` | Added duplicate-load guard, `_fbp` capture, canonical `_fbc` persistence, GA client ID capture, and enriched identify/page_view payloads | Shopify source asset upserted; CDN unversioned/new-query URL serves updated markers |
| 2026-05-24 | `layout/theme.liquid` | Added version-controlled CRM attribution script include near the end of the layout | Local repo updated; live layout touched through Shopify Admin GraphQL |
| 2026-05-24 | Shopify theme config | Upserted `layout/theme.liquid`, `templates/index.json`, and `assets/crm-attribution.js` on active theme `188150120741` | GraphQL userErrors empty; product page contains attribution script; homepage cache propagation still monitored |
| 2026-05-24 | Shopify webhook config | Updated broken webhook addresses from `api.pureleven.com` and suffixed CRM paths to reachable `track.pureleven.com` endpoints; added root CRM order webhooks alongside direct order/journey webhooks | Shopify readback: 13 webhooks, `BROKEN_ADDRESS_COUNT=0` |
