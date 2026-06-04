# Pureleven Growth Intelligence Platform Phase Plan

Date: 2026-05-16
Scope: CRM + Tracking + Attribution + AI + Automation + Dashboard + Analytics

## Objective

Build Pureleven as a unified growth operating system, not a set of disconnected tools.

The platform should separate responsibilities clearly:

- CRM stores business truth.
- GTM + GA4 + server-side tagging handle event capture and attribution.
- BigQuery stores raw analytical truth.
- AI Engine scores, analyzes, and recommends.
- n8n orchestrates workflows and notifications.
- Dashboard exposes visibility, controls, and approvals.

## Planning Principles

1. Do not build AI before data quality is trustworthy.
2. Do not put business logic in n8n.
3. Do not overload one domain or one service with multiple responsibilities.
4. Keep operational data and analytical data separate.
5. Use event-driven contracts across systems.
6. Launch read-only visibility before write-back automation.

## Current Architecture Anchors

### Server 1: CRM Core

- Host: `172.105.48.142`
- Target responsibility: customer data, lead pipeline, operational APIs, order intelligence, lifecycle management

### Server 2: Growth Node

- Host: `192.46.213.140`
- Current confirmed responsibilities: nginx, Docker, Postgres, Redis, n8n, AI engine, ads/tracking support services
- Confirmed live services:
  - `ai.pureleven.com`
  - `automations.pureleven.com`
  - `adsapi.pureleven.com`

### Cloud Run Tracking Layer

- `track.pureleven.com` should remain dedicated to GTM Server / event forwarding only
- It should not host dashboard, CRM, or business application traffic

### Current Tracking Gate From GTM Guide

The GTM guide establishes a hard dependency sequence:

1. Install `GTM-TFHBWPLM` on the storefront
2. Disable Shopify Customer Events GA4 pixel
3. Disable Shopify Facebook & Instagram pixel duplication
4. Set GTM Server container URL
5. Add GA4 client in Server container
6. Add Meta CAPI token and dataset configuration
7. Link GA4 to Google Ads
8. Publish and verify

The same guide explicitly notes that all downstream verification is blocked until the correct GTM container is live on site.

## Critical Architecture Decision

Before feature work expands, Pureleven needs one agreed platform map:

| Domain | Role | Recommended Owner |
|---|---|---|
| `dashboard.pureleven.com` | Control center UI | Dashboard app |
| `api.pureleven.com` | CRM and operational APIs | CRM core on `172.105.48.142` |
| `adsapi.pureleven.com` | Growth-side support APIs / current deployed lead API | Growth node on `192.46.213.140` |
| `track.pureleven.com` | GTM Server only | Cloud Run proxy |
| `ai.pureleven.com` | AI engine | Growth node |
| `automations.pureleven.com` | n8n | Growth node |
| `analytics.pureleven.com` | internal analytics / Grafana / warehouse views | Growth node or separate analytics tier |

If `api.pureleven.com` is intended to become the long-term CRM API host, then `adsapi.pureleven.com` should be treated as a transitional or specialized growth endpoint, not the permanent home for all business APIs.

## Recommended Phase Structure

## Phase 0: Source Of Truth Freeze

Timeline: 3 to 5 days

### Goal

Remove ambiguity before building on top of inconsistent identifiers, domains, and event flows.

### Deliverables

- Final domain ownership map
- Final system ownership map by server/service
- Canonical tracking source-of-truth sheet for:
  - GTM container IDs
  - GA4 property ID and measurement ID
  - Meta Pixel ID
  - Google Ads conversion account and labels
  - Merchant Center ID
- Event taxonomy contract for:
  - `page_view`
  - `view_item`
  - `add_to_cart`
  - `begin_checkout`
  - `purchase`
  - customer identity fields
  - order / transaction IDs
  - event IDs for deduplication
- Data ownership contract across:
  - Shopify
  - CRM
  - GA4
  - BigQuery
  - AI engine
  - n8n

### Exit Criteria

- One approved architecture document exists
- One approved event contract exists
- One approved domain map exists

## Phase 1: Measurement And Tracking Foundation

Timeline: 1 to 2 weeks

### Goal

Make tracking trustworthy before any CRM intelligence or AI automation consumes it.

### Work

- Install `GTM-TFHBWPLM` on the storefront
- Remove dependency on inert or legacy web containers
- Disable duplicate GA4 browser tracking from Shopify Customer Events
- Disable duplicate Meta browser tracking from Shopify Facebook integration if GTM becomes primary
- Set `track.pureleven.com` as the GTM Server endpoint in GTM configuration
- Ensure GA4 config uses `transport_url`
- Add GA4 client in Server container
- Add Meta CAPI tag with token and dataset
- Validate Google Ads event mapping and import path from GA4
- Enable enhanced conversions

### Acceptance Criteria

- Browser verification script passes for container, transport URL, and duplicate suppression
- Cloud Run logs show real `/g/collect` traffic
- GA4 realtime shows the canonical events from the right property
- Meta shows `Server` or `Server+Browser` event sources
- Google Ads conversions move to `Recording conversions`

### Important Constraint

Do not start AI optimization agents in production until this phase is complete.

## Phase 2: Data Platform MVP

Timeline: 2 to 3 weeks

### Goal

Create a shared intelligence backbone with clean operational and analytical layers.

### Recommended Split

- PostgreSQL on the CRM side or shared operations layer for business objects
- BigQuery for raw analytical events and cross-channel reporting
- Redis for queueing, caching, async job state, and orchestration support

### Core Operational Schemas

- `customers`
- `customer_addresses`
- `orders`
- `order_items`
- `leads`
- `lead_status_history`
- `customer_notes`
- `customer_interests`
- `customer_scores`
- `campaign_scores`
- `alerts`
- `agent_runs`
- `workflow_logs`
- `integration_credentials` or secret references only if securely managed

### Core Event Schemas

- `events`
- `tracking_events`
- `identity_links`
- `attribution_touchpoints`

### Work

- Build CRM data model on `172.105.48.142`
- Define ingestion APIs for storefront, order sync, and manual lead updates
- Export GA4 to BigQuery
- Pull ad metrics into warehouse tables on schedule
- Normalize identity keys:
  - `shopify_customer_id`
  - email
  - phone
  - order ID
  - event ID

### Exit Criteria

- Customer profile can join to orders and lead history
- GA4 raw events are present in BigQuery
- Core attribution tables can connect channel traffic to customer outcomes

## Phase 3: CRM And Customer Intelligence MVP

Timeline: 2 weeks

### Goal

Stand up the operational CRM before advanced AI scoring.

### MVP Features

- customer record view
- lead pipeline
- call / note logging
- lead stage transitions
- manual tagging and segmentation
- order history summary
- payment mode tracking
- city / pincode risk flags

### Derived Metrics

- LTV
- repeat rate
- purchase frequency
- COD ratio
- refund ratio
- RTO exposure

### Exit Criteria

- Sales and support teams can manage lead stages
- Customer records show joined operational history
- Basic scorecards are visible even before predictive AI

## Phase 4: Integration And Orchestration Layer

Timeline: 2 weeks

### Goal

Use n8n as orchestrator, not as the intelligence engine.

### n8n Responsibilities

- schedules
- retries
- workflow routing
- alerts
- webhook intake
- integrations with ads, CRM, Slack/WhatsApp, and warehouse jobs

### Work

- Create standard workflow patterns:
  - scheduled metric pull
  - alert dispatch
  - AI recommendation request
  - approval request
  - sync completion logging
- Push workflow run metadata into `workflow_logs`
- Add health monitoring for failed or stuck workflows

### Exit Criteria

- Each core workflow is retryable and observable
- Workflow errors appear in a central log or alert feed

## Phase 5: Dashboard MVP

Timeline: 2 to 3 weeks

### Goal

Launch a read-first control center before enabling widespread write actions.

### Recommended Stack

- Next.js
- Tailwind
- shadcn/ui
- Recharts
- FastAPI aggregation backend where needed

### MVP Modules

1. Infrastructure status
2. Tracking health
3. n8n workflows and failures
4. AI agent registry
5. Ads metrics overview
6. Alert center
7. CRM summary cards

### Phase 5 Scope Rule

Keep this version mostly read-only.

### Exit Criteria

- One authenticated dashboard shows health, alerts, workflows, agents, and top-line metrics
- Team can diagnose failures without opening five separate tools

## Phase 6: AI Intelligence Layer V1

Timeline: 3 weeks

### Goal

Deploy analyzer and recommender agents before execution agents.

### First Agent Set

#### Ads

- Negative keyword agent
- spend anomaly agent
- traffic quality agent
- creative fatigue agent

#### CRM

- lead scoring agent
- repeat purchase probability model
- churn risk agent

#### Ops

- geo risk / RTO scoring agent
- tracking anomaly detector
- workflow failure summarizer

### Output Style

Each agent should return:

- finding
- confidence
- explanation
- recommended action
- recommended owner
- audit log entry

### Exit Criteria

- Recommendations are visible in dashboard
- Recommendations are explainable and logged
- No automatic bid or audience changes yet without approval

## Phase 7: Controlled Automation

Timeline: 2 to 3 weeks

### Goal

Move from recommendations to guarded write actions.

### First Safe Automations

- alert-only ROAS anomalies
- alert-only spend spikes
- negative keyword suggestion queue with approval
- high-risk geo alert for COD review
- workflow restart / retry tooling
- Merchant Center feed error alerts

### Second-Wave Automations

- approved negative keyword push
- campaign budget throttle suggestions with approval
- customer audience sync to Meta / Google
- CRM tagging based on behavior thresholds

### Rules

- Every write action needs audit logging
- High-risk actions need manual approval first
- Rollback path must exist for budget and audience changes

### Exit Criteria

- Low-risk automations run stably
- Approval-based automations are auditable and reversible

## Phase 8: SEO, GEO, And Content Intelligence

Timeline: after dashboard + data backbone are stable

### Goal

Add content and search intelligence without distracting from attribution and customer quality.

### Features

- blog opportunity detection
- schema generation
- internal linking suggestions
- GEO targeting insights
- AEO content gap analysis

### Exit Criteria

- SEO output is measurable against rankings, indexing, and assisted conversions

## Phase 9: Growth OS Hardening

Timeline: ongoing

### Goal

Stabilize for continuous operation and future productization.

### Work

- secrets management
- RBAC and audit trails
- observability and logs
- rate limiting and job isolation
- queue backpressure handling
- deployment pipelines
- staging vs production environment separation

## 90-Day Build Sequence

## Days 1-14

- Phase 0 complete
- Phase 1 complete or near-complete
- tracking verification script passing
- GTM Server receiving real events

## Days 15-30

- Phase 2 underway
- CRM schema and ingestion online
- BigQuery export operational
- first operational joins working

## Days 31-45

- Phase 3 complete
- Phase 4 underway
- n8n workflow standards live

## Days 46-60

- Phase 5 MVP dashboard live
- first alert center and workflow visibility live

## Days 61-75

- Phase 6 analyzer agents live
- recommendations visible in dashboard

## Days 76-90

- Phase 7 limited automation live
- approval workflows and audit logging active

## Team Structure Recommendation

### Track A: Measurement And Data

- GTM Web
- GTM Server
- GA4
- Meta CAPI
- Google Ads import
- BigQuery

### Track B: CRM And APIs

- CRM schema
- customer data APIs
- order and lead integrations
- lifecycle views

### Track C: Dashboard And AI

- dashboard UI
- AI engine endpoints
- agent runtime
- recommendation UX

### Track D: Automation And Ops

- n8n workflows
- alerts
- infrastructure monitoring
- deployment pipelines

## Biggest Risks

1. Building dashboard and AI on top of inconsistent tracking IDs or duplicate event flows
2. Letting n8n become the place where business logic is hidden
3. Mixing CRM operational data and analytics warehouse responsibilities in one schema
4. Allowing write automation before recommendation quality is proven
5. Reusing `track.pureleven.com` or other infra domains for unrelated app traffic

## Final Recommendation

The right build order is:

1. Source of truth freeze
2. Tracking and attribution foundation
3. Data platform
4. CRM MVP
5. n8n orchestration standards
6. Dashboard MVP
7. AI recommendation layer
8. Controlled automation
9. SEO and advanced intelligence

That order keeps the platform composable, auditable, and materially useful from the first phase instead of producing an impressive-looking but unreliable control center.