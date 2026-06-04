# Pureleven Unified Growth Infrastructure: 5-Phase Execution

Date: 2026-05-16

## Current Live Findings

### Storefront

- `GTM-TFHBWPLM` is not currently active on `pureleven.com`
- `transport_url` to `https://track.pureleven.com` is not currently present in the page tracking config
- `window.gtag` exists from the Shopify-managed stack, not from the intended theme-controlled GTM server-side setup
- direct Meta scripts from `connect.facebook.net` are still loading on the storefront
- Shopify-side GA4/customer-event output is still present on the page

### Shopify Customer Events

- current connected app pixels in Shopify Customer Events:
  - `Facebook & Instagram`
  - `Google & YouTube`
  - `GoPixel`
  - `SendWILL Email Popups`
- `Google & YouTube` is currently connected on both `Server` and `Web`
- Customer Events exposes access-mode controls and test actions for these pixels, but not a clean direct disconnect flow from the table itself

### GTM / Google

- The currently open GTM workspace is `GTM-MDNS2FFP`, not the intended `GTM-TFHBWPLM`
- Several tags in that container are paused after Google malware scanning flags, so it is not a clean foundation for the new rollout
- The remote GTM guide expects:
  - web container: `GTM-TFHBWPLM`
  - GA4 property: `pureleven_shopify2025` / property `499681124`
  - measurement ID: `G-3FRSK7TEN2`
  - Google Ads account: `AW-10965185406`

### Meta

- Browser-side Meta pixel is active for Pixel `609256704464862`
- Meta CAPI is not yet validated end to end through the server-side GTM path

### Growth Server / First-Party Tracking

- `track.pureleven.com` is correctly proxied through nginx to the GTM Server Cloud Run service
- direct browser access returns HTTP `400`, which is expected for this endpoint without GTM event parameters
- Google Cloud project binding is present as `pure-leven`

## 5 Phases

## Phase 1: Tracking Foundation

Goal: make the storefront send trusted first-party data to the server-side tracking stack.

Scope:

- install `GTM-TFHBWPLM` in the Shopify theme
- route GA4 config through `https://track.pureleven.com`
- remove legacy dependence on the current Shopify-managed Google path for primary tracking
- disable duplicate GA4 and Meta browser-side sources in Shopify apps/settings, including Shopify Customer Events and any overlapping app pixels such as GoPixel
- verify `/g/collect` traffic reaches GTM Server / Cloud Run

Exit gate:

- storefront shows `GTM-TFHBWPLM`
- `transport_url` is `https://track.pureleven.com`
- direct Meta duplication is removed
- Shopify GA4 duplication is removed

## Phase 2: Google + Meta Conversion Reliability

Goal: make channel optimization trustworthy.

Scope:

- confirm GA4 property mapping
- import GA4 conversions into Google Ads
- validate conversion labels in Google Ads
- enable Enhanced Conversions
- complete Meta CAPI token + dataset setup in the server container
- validate deduplication with `event_id`

Exit gate:

- Google Ads shows recording conversions
- Meta shows `Server` or `Server+Browser`
- purchase / add_to_cart / begin_checkout / view_item are consistent across platforms

## Phase 3: CRM + Data Backbone

Goal: create the operational and analytical source of truth.

Scope:

- establish CRM core on `172.105.48.142`
- unify customers, leads, orders, notes, and lifecycle stages
- export GA4 to BigQuery
- normalize identity keys across Shopify, CRM, and ad platforms
- create attribution-ready warehouse tables

Exit gate:

- customer, lead, and order history can be joined reliably
- channel and revenue views are queryable from a single data model

## Phase 4: Dashboard + Orchestration

Goal: create a usable control center before advanced automation.

Scope:

- build `dashboard.pureleven.com`
- expose infrastructure health, tracking health, ads health, workflows, alerts, and CRM summaries
- standardize n8n workflows for scheduling, retries, approvals, and alerts
- centralize workflow logs and failures

Exit gate:

- the team can see system status and diagnose failures from one dashboard
- automation runs are observable and auditable

## Phase 5: AI Recommendations + Controlled Automation

Goal: layer intelligence on top of clean data and controlled operations.

Scope:

- deploy recommendation agents for ads, CRM, tracking, and ops
- surface findings with confidence and rationale
- introduce approval-based automations first
- add low-risk write actions only after recommendation quality is proven

Exit gate:

- recommendations are explainable and logged
- write actions are gated, auditable, and reversible

## Development Started Today

### Completed in local theme code

- updated [layout/theme.liquid](/Users/bthomas/Documents/pureleven_dev/layout/theme.liquid) to:
  - bootstrap `dataLayer`
  - define a fallback `window.gtag` bridge
  - load `GTM-TFHBWPLM`
  - send GA4 config with `transport_url: https://track.pureleven.com`
  - add the GTM noscript iframe

### Not deployed live yet

This change is intentionally not pushed live yet because the current Shopify-managed GA4 path and direct Meta pixel path are still active. Pushing the new theme bootstrap first would create duplicate tracking until those sources are disabled.

## Immediate Next Steps

1. Disable Shopify Customer Events / Google-managed duplicate GA4 path
2. Disable Shopify Facebook & Instagram direct Meta pixel path
3. Publish the new theme-controlled GTM bootstrap
4. Validate storefront with the GTM verification script
5. Confirm Cloud Run `/g/collect` traffic and platform-side event visibility