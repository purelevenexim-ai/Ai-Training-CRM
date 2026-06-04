# Server-Side Conversion Tracking Audit

Date: 2026-05-24

Scope: Pure Leven root CRM/AI Engine, Shopify storefront, Shopify webhooks, Meta Conversions API, Google Ads Enhanced/Offline Conversions, GA4 Measurement Protocol, GTM Server-Side host, and the `anu-login`/WhatsApp backend.

This report was created before applying fixes. It documents the live production state observed on `root@192.46.213.140` and the current workspace code.

## Executive Verdict

Server-side ecommerce conversion tracking is broken for purchases and materially incomplete for attribution.

Only the product audience relay is partially working: product-page interest events reach `/api/crm/events/ga4` and are stored in `crm_events` as GA4/audience events. Purchase fan-out to Meta CAPI, Google Ads, and GA4 Measurement Protocol is not functioning in production because Shopify order webhooks are registered to the wrong public host and recent orders lack captured attribution identifiers.

Post-fix note: the critical webhook routing and browser attribution entry points have now been repaired. Purchase destination delivery still needs validation on the next real `orders/paid` event because the audit began with 0 recent successful server-side purchase sends.

## Post-Fix Implementation Status

Implemented on 2026-05-24:

- Updated Shopify webhook registrations: no remaining `api.pureleven.com` webhook addresses and no remaining suffixed `/api/crm/webhooks/shopify/...` addresses.
- Added root CRM webhooks for `orders/create`, `orders/paid`, and `orders/fulfilled` at `https://track.pureleven.com/api/crm/webhooks/shopify` while retaining direct order/journey webhooks at `https://track.pureleven.com/api/shopify/webhook/order-*`.
- Deployed the CRM attribution source asset to the active Shopify theme and touched the active theme layout/template through Admin GraphQL.
- Patched live root CRM tracking code so GA4 MP purchase payloads prefer GA client/session identifiers instead of email.
- Patched live fraud scoring so attributed orders with missing optional PII/address data are not automatically suppressed at score 65.
- Extended page-view storage to preserve `fbp`, `fbc`, `ga_client_id`, `ga_session_id`, `page_url`, and `page_title`.
- Added focused automated tests for fraud gating, Meta fan-out payloads, Google Ads fan-out payloads, and GA4 MP client ID behavior.

Post-fix validation:

- Focused pytest suite: 7 passed, 1 Pydantic deprecation warning.
- Shopify webhook readback: 13 webhooks, `BROKEN_ADDRESS_COUNT=0`.
- Public `/api/crm/events/page_view` accepted enriched attribution and stored `gclid`, `fbclid`, `fbp`, `fbc`, `ga_client_id`, and `ga_session_id` in Postgres.
- Recent Postgres window showed non-audit homepage page_view traffic after the attribution fix.
- Shopify source asset is updated; some cached storefront HTML may temporarily reference an older versioned CDN asset URL until Shopify cache propagation completes.

## Destination Status

| Destination | Status | What is working | What is broken or unproven |
| --- | --- | --- | --- |
| Meta CAPI | Broken for purchases | Production has `meta_capi.py` and purchase sender code | Shopify `orders/paid` does not reach the app; 0 of 253 recent orders marked sent; payload lacks `fbp`, `external_id`, and `event_source_url`; `fbc` is synthesized from current time instead of original click time |
| Google Ads conversions | Broken for purchases | Production has `gads_conversion.py` using Google Ads API v20 | Shopify order webhooks miss the app; no recent orders have `gclid`; event name is accepted by caller but not mapped to multiple conversion actions |
| GA4 Measurement Protocol | Broken for purchases; partial for audience events | `/api/crm/events/ga4` stores product interest events | Purchase MP uses email as `client_id`; order webhook path is not firing; duplicate storefront GA4 IDs remain visible |
| GTM Server-Side | Inconclusive as conversion destination | `track.pureleven.com/` proxies root traffic to the Cloud Run GTM server | CRM API routes bypass GTM and go straight to FastAPI; no proof that purchase events reach GTM server-side |
| CRM event storage | Partial | Product audience events are stored | Broad page-view attribution is absent from storefront; only a manual/test page_view appeared in the recent window |
| WhatsApp/anu-login event gateway | Inert in live DB | Service runs on 8010 for selected nginx routes | Active SQLite DB has 0 `event_logs`, 0 `journey_customers`, 0 `journey_messages`, and 0 `journey_engagement_events`; schema lacks attribution columns expected by code |

Updated after implementation: Meta, Google Ads, and GA4 purchase routes are now reachable from Shopify, but destination delivery remains pending until a real paid order triggers the fan-out and response logs can be inspected.

## Live Architecture Observed

### Services

- Root AI/CRM container: `pureleven-ai-engine`, bound as `127.0.0.1:8000 -> container:8000`.
- Root database: `pureleven-postgres`, database `pureleven`, user `pureleven`.
- Anu-login backend: `anu-login-backend.service`, running uvicorn on `127.0.0.1:8010` from `/opt/anu-login-backend/backend`.
- Legacy/conflicting service: `pureleven-whatsapp-crm.service`, failing and attempting to use the same 8010 port.
- Plunk service: `pureleven-plunk`, bound to port 8080.

### Public routing

| Public host/path | Live upstream | Tracking impact |
| --- | --- | --- |
| `track.pureleven.com/api/crm/meta-wa/send` and selected WhatsApp paths | `127.0.0.1:8010` | Reaches anu-login backend |
| `track.pureleven.com/api/` | `127.0.0.1:8000` | Reaches root CRM/AI Engine |
| `track.pureleven.com/` | GTM Cloud Run server | Root host is GTM server-side, but API routes bypass it |
| `api.pureleven.com/` | `127.0.0.1:8080` | Points to Plunk, not the tracking app |

## Critical Findings

### 1. Shopify order webhooks are misrouted

Severity: Critical

Current Shopify webhook registrations route order events to `api.pureleven.com`, which nginx sends to Plunk on port 8080. Route probes showed these URLs return 404 from the wrong service.

Observed registrations:

- `orders/create -> https://api.pureleven.com/api/shopify/webhook/order-created`
- `orders/paid -> https://api.pureleven.com/api/shopify/webhook/order-paid`
- `orders/fulfilled -> https://api.pureleven.com/api/shopify/webhook/order-fulfilled`

The same paths exist on the root tracking app at `track.pureleven.com` via the 8000 upstream; GET probes returned 405, confirming route existence for POST-only handlers:

- `/api/shopify/webhook/order-created`
- `/api/shopify/webhook/order-paid`
- `/api/shopify/webhook/order-fulfilled`

Impact: `orders/paid` is the trigger for Meta CAPI, Google Ads, and GA4 purchase fan-out. Because Shopify sends it to Plunk, purchase conversions do not reach the conversion senders.

Required fix: update Shopify order webhook addresses to `https://track.pureleven.com/api/shopify/webhook/order-created`, `https://track.pureleven.com/api/shopify/webhook/order-paid`, and `https://track.pureleven.com/api/shopify/webhook/order-fulfilled`, or change nginx so `api.pureleven.com/api/shopify/webhook/*` reaches the tracking app.

### 2. Shopify cart, checkout, and customer webhooks are registered to non-existent suffixed CRM paths

Severity: Critical

Observed registrations include:

- `carts/create -> https://track.pureleven.com/api/crm/webhooks/shopify/cart-create`
- `carts/update -> https://track.pureleven.com/api/crm/webhooks/shopify/cart-update`
- `checkouts/create -> https://track.pureleven.com/api/crm/webhooks/shopify/checkout-create`
- `checkouts/update -> https://track.pureleven.com/api/crm/webhooks/shopify/checkout-update`
- `customers/create -> https://track.pureleven.com/api/crm/webhooks/shopify/customer-create`
- `customers/update -> https://track.pureleven.com/api/crm/webhooks/shopify/customer-update`

The live root CRM exposes `/api/crm/webhooks/shopify` as a single endpoint, not those suffixed paths. Probes and logs show 404 for the suffixed routes.

Impact: cart, checkout, and customer events do not reliably enter the CRM. This prevents early identity and attribution collection, weakens abandon-cart tracking, and limits purchase matching.

Required fix: either re-register webhooks to the unified endpoint with topic handling, or add compatibility routes for the currently registered suffixed paths.

### 3. Storefront page-view attribution capture is missing from live HTML

Severity: Critical

The workspace has `assets/crm-attribution.js`, which captures `gclid`, `fbclid`, UTMs, session ID, page view, and identify calls. Live storefront HTML does not show:

- `crm-attribution.js`
- `/api/crm/events/page_view`
- `/api/crm/identify`

Recent root Postgres data confirms this absence: only 1 `page_view` event existed in the recent window, and it was from a curl/manual test rather than normal storefront traffic.

Impact: orders cannot be matched to `gclid`, `fbclid`, UTMs, `fbp`, or session context. Enhanced Conversions can sometimes use hashed email/phone, but click-based Google and Meta attribution is effectively absent.

Required fix: deploy/inject the CRM attribution script into the active live theme and verify raw storefront HTML plus database inserts.

### 4. Recent order attribution fields are empty

Severity: Critical

Root Postgres last 7 days:

- `crm_orders`: 253 orders
- Orders with `gclid`: 0
- Orders with `fbclid`: 0
- Orders with `utm_source`: 0
- `conversion_feeds`: 0
- `crm_offline_conversions`: table missing

Impact: Google click conversion uploads have no click ID source. Meta CAPI lacks original click/browser identifiers. Marketing channel analysis and ROAS attribution cannot be trusted.

Required fix: restore browser-side attribution capture, link attribution to customer/session/order records, and add a durable conversion feed or offline conversion queue table.

### 5. Purchase fan-out has not marked any recent order as sent

Severity: Critical

Root Postgres last 7 days:

- `offline_conversion_sent = true`: 0 of 253 orders
- `capi_suppressed = true`: 250 of 253 orders
- 3 eligible paid orders still had `offline_conversion_sent = false`

Impact: there is no production evidence that recent purchases reached Meta, Google Ads, or GA4 MP through the server-side path.

Required fix: repair webhook routing first, then add retry/backfill tooling with response logging and idempotent sent-state updates.

### 6. Fraud scoring suppresses nearly all recent orders

Severity: High

Fraud score distribution for recent orders:

- 250 orders scored 65
- 1 order scored 30
- 2 orders scored 0

The suppression gate blocks scores above 50. The scoring logic adds large penalties for missing email, phone, and shipping data. The high volume of score 65 orders strongly suggests webhook ingestion or backfill data is incomplete, not that almost all orders are fraudulent.

Impact: even after webhook routing is fixed, valid orders may still be suppressed from CAPI and Google if payload normalization remains incomplete.

Required fix: distinguish missing optional webhook fields from fraud signals, normalize Shopify payload fields before scoring, and suppress only high-confidence invalid orders.

### 7. Meta CAPI payload quality is incomplete

Severity: High

Production `meta_capi.py` sends purchase events with hashed email/phone and `event_id = purchase_{order_id}`. It does not include `fbp`, `external_id`, or `event_source_url`. It also builds `fbc` from the current send timestamp plus `fbclid`, rather than the original click timestamp.

Impact: lower Event Match Quality, weaker attribution, and avoidable dedup/matching loss.

Required fix: capture and persist `_fbp`, canonical `_fbc`, client IP, user agent, source URL, and stable customer external ID at the browser/session layer and pass them into CAPI.

### 8. Google Ads conversion upload is incomplete for conversion-action mapping

Severity: High

Production `gads_conversion.py` uploads to one configured conversion action using either `gclid` or hashed email/phone. The caller passes `event_name`, but the upload helper does not map event names such as `purchase`, `cod_delivered`, or lifecycle milestones to separate conversion actions.

Impact: Google Ads may receive the wrong conversion category once sending works. COD delivered or fulfilled conversions cannot be separated from order-paid intent.

Required fix: add explicit conversion-action mapping, partial-failure logging, and replay-safe status tracking.

### 9. GA4 Measurement Protocol purchase payload uses email as client_id

Severity: High

The GA4 purchase sender uses email as `client_id`. GA4 MP expects a web client ID or app instance ID. Email is PII-like and does not stitch cleanly to web sessions.

Impact: server purchase events will not join correctly with web sessions and may violate data handling expectations.

Required fix: capture and persist GA client ID/session ID from browser tags, and send those identifiers with purchase MP events.

### 10. Duplicate GA4 IDs are still visible on the storefront

Severity: Medium

Live pages show both `G-3FRSK7TEN2` and `G-3JXJPCDV72`. Repository memory indicates `G-3JXJPCDV72` is service-backed by Shopify Google Ads integration and can reappear when Google Ads is connected.

Impact: page and ecommerce activity can be split or duplicated. Debugging server-side GA4 becomes harder.

Required fix: clean up Shopify Google & YouTube app configuration or document the unavoidable service-backed tag while ensuring the canonical property `G-3FRSK7TEN2` receives all intended events.

### 11. The anu-login/WhatsApp tracking backend is deployed but not recording events

Severity: High

The active SQLite database at `/opt/anu-login-backend/backend/data/anu_login.sqlite3` has the expected tables, but live row counts are all zero:

- `event_logs`: 0
- `journey_customers`: 0
- `journey_messages`: 0
- `journey_engagement_events`: 0

The active `journey_customers` schema also lacks code-expected attribution columns such as `meta_lead_id`, `google_gclid`, and `fbc`.

Impact: WhatsApp journey and engagement events are not providing useful conversion or attribution data in production.

Required fix: either migrate the live SQLite schema and route real events to it, or retire the inactive path and centralize tracking in the root CRM.

### 12. Server-only production modules are not in the local workspace

Severity: Medium

Production has `/opt/pureleven/ai-engine/app/meta_capi.py` and `/opt/pureleven/ai-engine/app/gads_conversion.py`, but these files are not present in the local workspace root where related CRM code lives.

Impact: conversion-critical production logic is not version controlled locally, making review, tests, and repeatable deployment risky.

Required fix: bring the live modules into version control before editing them, or explicitly replace them with reviewed repo-owned implementations.

## Root Cause Summary

The current failure is not a single API credential problem. The tracking stack fails across four layers:

1. Public routing: Shopify purchase webhooks are sent to `api.pureleven.com`, which reaches Plunk instead of the tracking app.
2. Storefront instrumentation: the live theme is missing the broad CRM attribution script, so click IDs and UTMs are not captured.
3. Data model and ingestion: recent orders contain no `gclid`, `fbclid`, or UTM values, and most are suppressed by fraud scoring because key identity/address fields are missing.
4. Destination payloads: Meta, Google Ads, and GA4 sender implementations need identifier, dedup, mapping, and logging improvements before they can be considered production-grade.

## Fix Priority

1. Re-register Shopify order webhooks to the live tracking host or change nginx routing for the existing `api.pureleven.com/api/shopify/webhook/*` paths.
2. Fix cart, checkout, and customer webhook registrations or add compatibility routes for the currently registered suffixed paths.
3. Deploy the CRM attribution script to the active Shopify theme and confirm page-view and identify events insert into Postgres.
4. Adjust order ingestion and fraud scoring so valid Shopify paid orders are not suppressed because of missing optional fields.
5. Add durable conversion queue/retry state with response bodies and partial failure details.
6. Improve Meta CAPI payloads with `fbp`, canonical `fbc`, `external_id`, `event_source_url`, stable event IDs, and test-event support.
7. Improve Google Ads conversion uploads with conversion-action mapping, enhanced-conversion-only behavior, and partial-failure reporting.
8. Fix GA4 MP purchase identifiers to use GA client/session identifiers instead of email.
9. Decide whether the inactive anu-login tracking DB should be migrated and used, or decommissioned for tracking purposes.
10. Resolve duplicate GA4 storefront configuration or document the unavoidable service-backed tag and validate no duplicate purchase events are emitted.

## Confidence

High confidence that purchase server-side tracking is currently broken, because the live Shopify `orders/paid` webhook is registered to a host that routes to Plunk and returns 404, and Postgres shows no recent order fan-out success.

Medium confidence on downstream API credentials because the code and environment exist but live fan-out is not being reached. Credential validity still needs a controlled test event after webhook routing and retry logging are repaired.
