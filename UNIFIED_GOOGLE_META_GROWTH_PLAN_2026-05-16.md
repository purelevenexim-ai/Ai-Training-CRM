# Unified Google Ads + Meta Ads Growth Plan

Date: 2026-05-16
Brand: Pureleven
Store: pureleven.com

## Goal

Build a single paid-media system where:

- Meta creates demand.
- Google captures demand.
- GA4 is the analytics control plane.
- Server-side tracking improves match quality and attribution durability.
- BigQuery + CRM become the feedback loop for budget, audience, and creative optimization.

This plan is based on:

- Official Google Analytics, Google Ads, and Google Tag Manager documentation.
- Official Meta for Developers and Meta Business Help documentation.
- Current official YouTube channel surfaces from Google Ads and Meta Developers.
- Existing Pureleven workspace audits and implementation notes.

Note: no one can literally review every document and every video on the internet. This plan uses the current high-signal official sources plus your repo research and implementation state.

## Executive Summary

The high-conversion setup is not "Google Ads plus Meta Ads." It is one measurement and conversion system with different channel roles.

What the research consistently supports:

1. Measurement quality comes before budget scale.
2. Redundant browser + server event sharing is now the correct default for Meta and increasingly important for Google.
3. GA4 ecommerce event quality is the backbone for Google Search, Shopping, PMax, remarketing, and cross-channel analysis.
4. Meta Pixel without Conversions API is incomplete for modern ecommerce.
5. Google Ads without enhanced conversions, imported GA4 key events, and proper attribution settings underperforms.
6. Creative quality and landing-page alignment matter more than over-complicated audience slicing.
7. For a D2C spice brand, profit quality matters as much as conversion volume: prepaid rate, RTO risk, repeat purchase, and geography quality should eventually feed bidding and exclusions.

## Current Pureleven State

Verified from repo notes and live audits:

- GA4 primary property: G-3FRSK7TEN2
- GTM web container: GTM-MDNS2FFP
- Google Ads account linked to GA4: 149-516-3260
- Merchant Center linked to GA4: 5618477992
- Meta Pixel is active browser-side on the storefront
- Meta CAPI is not implemented yet
- Custom product-interest audience events are live on product pages
- GTM is clean of legacy GA4 IDs
- track.pureleven.com should be reserved for future server-side tracking, not application traffic
- Prior attempt to use track.pureleven.com for Google tracking failed; current Google tag load path was reverted to hosted Google endpoints

Implication:

You already have a usable Google foundation. The biggest gap is Meta server-side conversion resilience and a unified first-party tracking architecture that both platforms can trust.

## Research Findings That Matter Most

### Google

- GA4 ecommerce should use the recommended event model: view_item_list, select_item, view_item, add_to_cart, view_cart, begin_checkout, add_shipping_info, add_payment_info, purchase, refund.
- Google Ads dynamic remarketing depends on correct item-level data and matching feed identifiers.
- Google recommends linking Google Ads to GA4 so you can import GA4 key events and audiences.
- Enhanced conversions improve measurement by sending hashed first-party conversion data.
- Data-driven attribution is now the default recommendation for eligible accounts.
- Server-side tagging with a custom domain is the preferred path when you want more durable first-party cookies and higher-quality measurement.
- BigQuery export is the correct source for raw-event analysis and future AI automation.

### Meta

- Meta explicitly recommends a redundant setup: send the same core ecommerce events through both Pixel and Conversions API.
- Deduplication is mandatory when the same event is sent from browser and server; event_name and event_id must match.
- Event Match Quality matters. Meta scores it 0-10, and better matching improves reported conversions and delivery quality.
- Recommended customer information parameters include email, click ID, phone, external_id, browser ID, and user agent/IP for server events.
- Meta recommends monitoring server-to-browser event coverage and aiming for strong parity; a 75%+ CAPI-to-Pixel coverage ratio is a useful operational target.
- Aggregated Event Measurement still matters for prioritizing web events on verified domains.

### Practical Cross-Platform Conclusion

The winning stack is:

1. Browser events for immediacy and platform-native behavior.
2. Server events for resilience and match quality.
3. GA4 as the canonical event taxonomy.
4. One order ID / transaction ID / event ID strategy across systems.
5. A shared audience and reporting layer in BigQuery + CRM.

## Target Architecture

```text
Shopify Storefront
  -> GTM Web Container
  -> GA4 browser events
  -> Google Ads browser tags / linker
  -> Meta Pixel browser events

Browser events + first-party user data
  -> track.pureleven.com
  -> GTM Server Container
  -> GA4 / Measurement Protocol where needed
  -> Google Ads enhanced conversions / user-provided data
  -> Meta Conversions API

GA4 raw export
  -> BigQuery
  -> CRM / PostgreSQL / analytics layer
  -> AI automation and decisioning
  -> audience exclusions, negative keywords, geo controls, budget alerts
```

## Channel Roles in the Unified Funnel

### Meta Ads

Best use:

- Demand generation
- Emotional hooks
- UGC and founder-led storytelling
- Reels and short-form education
- Retargeting based on product interest and cart activity

Pureleven angles:

- Supermarket spices vs farm-origin spices
- Aroma and freshness demonstration
- Purity, sourcing, and adulteration education
- Founder and farm story
- Recipe-led discovery
- Gift boxes, bundles, and seasonal offers

### Google Ads

Best use:

- Existing demand capture
- Product and price comparison traffic
- Brand defense
- Shopping and feed-driven harvest
- High-intent remarketing

Pureleven angles:

- buy kerala spices online
- cardamom online india
- black pepper 8mm price
- ceylon cinnamon online
- farm fresh spices india
- brand and review queries

### YouTube

Best use:

- Mid-funnel trust building
- Educational product stories
- Review and usage content
- Lift for brand search and conversion intent

## Non-Negotiable System Rules

1. One primary purchase signal for bidding on each platform.
2. One consistent event taxonomy across GA4, Google Ads, Meta Pixel, and Meta CAPI.
3. One event_id per conversion instance for Meta deduplication.
4. One transaction_id / order_id standard across Shopify, GA4, and Google Ads imports.
5. No duplicate browser tags outside the chosen GTM / platform integrations.
6. No scaling before purchase value and attribution are trustworthy.
7. No AI automation before raw event quality is stable.

## Canonical Event Map

| Shopify action | GA4 | Meta Pixel/CAPI | Google Ads use |
|---|---|---|---|
| Page view | page_view | PageView | remarketing / diagnostics |
| Product view | view_item | ViewContent | audiences / dynamic remarketing |
| Add to cart | add_to_cart | AddToCart | micro-conversion / audience |
| Begin checkout | begin_checkout | InitiateCheckout | warm audience / conversion ladder |
| Payment step | add_payment_info | AddPaymentInfo | optional warm audience |
| Purchase | purchase | Purchase | primary optimization event |
| Search | view_search_results or search | Search | query intent analysis |
| WhatsApp click | custom GA4 event | Contact or custom event | lead-assist / audience |

Implementation note:

- Use standard events wherever possible.
- Add custom parameters instead of inventing custom conversion names unless needed.
- Keep item_id aligned with Merchant Center / catalog identifiers.

## Recommended Build Sequence

## Phase 1: Measurement Foundation

Timeline: Week 1

### Deliverables

- Confirm GA4 ecommerce events are firing once and with correct values.
- Mark purchase as the primary business conversion.
- Confirm Google Ads imports the correct GA4 purchase key event or uses a correctly configured purchase conversion with value.
- Verify enhanced conversions are active and validated in Google.
- Confirm Meta Pixel browser events fire for ViewContent, AddToCart, InitiateCheckout, AddPaymentInfo, and Purchase.
- Turn on Meta advanced matching where lawful and available.
- Define a UTM standard for Meta and Google.
- Verify domain ownership where required for Meta event configuration.
- Set Aggregated Event Measurement priorities.

### Acceptance Criteria

- Shopify orders and GA4 purchases are within 5-10% count parity over a clean test window.
- GA4 purchase value is within 5-8% of Shopify gross sales for the same window.
- Google Ads purchase conversion shows value, not zero.
- Meta Purchase fires with value and currency.

### Pureleven-Specific Notes

- You already have GA4, GTM, Ads, and Merchant Center in a much better state than most stores.
- The missing piece in this phase is Meta event hardening and event taxonomy cleanup for future server-side parity.

## Phase 2: Server-Side Tracking

Timeline: Weeks 2-3

### Deliverables

- Deploy GTM Server on Cloud Run.
- Map track.pureleven.com to the server container custom domain.
- Keep ai.pureleven.com, automations.pureleven.com, and api.pureleven.com separate from tracking.
- Route GTM Web to the server endpoint where appropriate.
- Send Meta Purchase, InitiateCheckout, AddToCart, and ViewContent server-side through Conversions API.
- Include event_id parity for browser/server duplicates.
- Include fbp, fbc, external_id, client_user_agent, and client_ip_address where permitted and available.
- Enable Google server-side enhancements where practical, especially for user-provided data / enhanced conversions.

### Acceptance Criteria

- Meta Events Manager shows browser + server event receipt.
- Deduplication is working for duplicate browser/server events.
- Event Match Quality for Purchase is consistently improving, target above 6/10 and trending upward.
- CAPI coverage reaches at least 75% of browser event volume for core ecommerce events.

### Recommended Infrastructure Choice

- Short term DNS can still point subdomains to Linode where needed.
- Long term tracking should live on track.pureleven.com backed by GTM Server on Cloud Run or equivalent.
- Do not keep application traffic on track.pureleven.com; it should be a first-party measurement domain.

## Phase 3: Audience Intelligence System

Timeline: Week 3

### Google Audiences

- All visitors 30d
- Product viewers 30d
- Add-to-cart no purchase 14d
- Checkout no purchase 7d
- Purchasers 30d and 180d
- High-intent product-category visitors from your custom audience tracking
- Customer Match from past buyers

### Meta Audiences

- Video viewers 25%, 50%, 75%
- Instagram engagers 30d
- Product viewers 30d
- AddToCart 14d
- InitiateCheckout 7d
- Purchasers 30d and 180d
- High AOV buyers
- WhatsApp click users

### Business-Quality Audiences

When CRM feedback is ready, create suppression and value audiences for:

- COD failed
- High RTO risk geography
- Repeat buyers
- High LTV buyers
- Bundle buyers
- Wholesale / non-core traffic

### Acceptance Criteria

- Prospecting excludes recent purchasers.
- Retargeting windows are separated and non-overlapping.
- Audience sizes are healthy enough for delivery.

## Phase 4: Creative Engine

Timeline: Weeks 3-4

### Meta Creative System

You need a testing grid, not random ad production.

Core angles:

- Aroma proof
- Purity proof
- Farm-origin story
- Kitchen transformation
- Customer review
- Founder story
- Recipe use case
- Gift / offer / bundle angle

Suggested creative matrix:

- 4 hooks
- 3 offers or messages
- 3 formats

That gives 36 testable combinations without inventing a new strategy every week.

Formats:

- Reels / short vertical video
- UGC-style testimonial
- Product demonstration
- Carousel for bundles or usage scenarios
- Static offer ad for retargeting

### Google Creative System

- Search RSAs grouped tightly by product intent
- Shopping feed titles and images optimized by product intent
- PMax asset groups by category, not one bucket for the entire catalog
- YouTube Shorts and longer trust videos for mid-funnel education

### Acceptance Criteria

- New creative batch every 2 weeks minimum.
- At least 20-30% of spend goes to fresh creative testing until stable winners emerge.

## Phase 5: Campaign Architecture

Timeline: Weeks 4-5

### If Total Budget Is Still Constrained

Do not run every channel at once.

If total daily spend is below roughly INR 3,000-5,000, start with only 3 buckets:

1. Meta prospecting
2. Google Search + Shopping capture
3. Retargeting across both platforms

Do not start with:

- too many Meta ad sets
- broad-match-heavy Google campaigns
- PMax as the first campaign
- YouTube before your tracking and creative cadence are stable

### Recommended Starting Allocation

Constrained budget:

- Meta prospecting: 40%
- Google Search: 30%
- Google Shopping / feed capture: 15%
- Meta + Google retargeting: 15%

Moderate budget with enough data:

- Meta prospecting: 35%
- Google Search: 25%
- Google Shopping: 15%
- PMax: 10%
- Retargeting: 10%
- YouTube trust: 5%

### Google Campaign Sequence

1. Brand Search
2. Non-brand exact and phrase purchase-intent search
3. Shopping / feed-based campaigns
4. PMax only after conversion quality is trusted
5. YouTube retargeting / education after core capture is stable

### Meta Campaign Sequence

1. Broad / Advantage+ style prospecting with strong creative diversity
2. Product-interest retargeting
3. Cart and checkout recovery
4. Purchaser upsell and bundle campaigns

## Phase 6: Landing and Offer Conversion Layer

Timeline: Parallel with campaigns

High-conversion paid media will fail if landing pages are weak.

Priority landing improvements for Pureleven:

- Strong first-screen trust on product pages
- Source-aligned messaging between ad and page
- Cleaner bundle offers and quantity ladders
- Review proof near the buy box
- Clear delivery, freshness, and return expectations
- Better WhatsApp and email capture for remarketing and retention
- Geo-aware prepaid nudges where RTO risk is high

For spices specifically, landing pages should answer:

- Why this is better than supermarket spice
- What aroma/purity/farm-origin means in practice
- How to use it
- What the pack size and value proposition are
- Why the buyer should trust the product enough to order now

## Phase 7: Reporting and AI Layer

Timeline: Weeks 6-12

### BigQuery and Reporting

Build one source of truth for:

- blended MER
- channel ROAS
- new customer vs repeat revenue
- SKU-level contribution
- geography-level profitability
- RTO and COD loss by source
- creative angle performance
- search term waste

### AI Automation Modules

Build these only after data quality is stable:

1. Negative keyword agent
2. Search term clustering and waste detection
3. Creative fatigue and winner detection
4. Audience quality scoring
5. Geo-risk bid suppression
6. Budget anomaly alerts
7. LTV-quality feedback loops into ads and CRM

## 30 / 60 / 90 Day Plan

## First 30 Days

Focus: measurement integrity and core campaign structure

- finalize GA4 and Google conversion setup
- verify Meta browser events
- implement Meta CAPI plan
- stand up GTM Server architecture
- define event_id / transaction_id standards
- finalize audience taxonomy
- launch only core campaigns

Success metrics:

- stable purchase tracking
- enhanced conversions active
- Meta deduplication working
- no obvious duplicate tagging

## Days 31-60

Focus: creative learning and audience refinement

- expand Meta creative testing
- refine Search queries and negatives
- activate Shopping and then PMax if data is stable
- build retargeting ladders by window and behavior
- export GA4 to BigQuery
- start blended reporting

Success metrics:

- predictable CPA by core campaign
- event match quality improving
- search term waste falling
- retargeting recovery rate measurable

## Days 61-90

Focus: quality-based scaling and automation

- integrate CRM quality signals
- suppress bad geographies / bad order-quality cohorts
- feed repeat buyer / high LTV segments into both ad platforms
- launch first automation alerts
- test budget allocation rules using channel contribution, not last click only

Success metrics:

- higher blended MER
- lower waste from poor geos / poor queries
- clear split between acquisition and retention spend
- usable dataset for AI optimizers

## KPIs That Actually Matter

Track these weekly:

- Shopify orders vs GA4 purchases parity
- Shopify revenue vs GA4 purchase value parity
- Google enhanced conversions status
- Meta Event Match Quality by event
- Meta browser/server event coverage ratio
- branded vs non-branded search efficiency
- retargeting recovery rate
- blended MER
- new customer CAC
- contribution margin after shipping, discount, and RTO
- repeat purchase rate from paid cohorts

## Biggest Mistakes To Avoid

### Google

- scaling PMax before conversion quality is trusted
- broad match without strong negatives
- optimizing to micro-conversions instead of purchase
- duplicate tags across Shopify, GTM, and app integrations

### Meta

- Pixel without CAPI
- browser and server events without deduplication
- weak Event Match Quality
- too many ad sets with tiny budgets
- refreshing audiences instead of refreshing creative

### Both Platforms

- trusting last-click platform reporting as the business truth
- optimizing to cheap purchases instead of profitable customers
- ignoring geography and payment-method quality in India
- trying to automate before data quality is fixed

## Recommended Next Actions For Pureleven

In order:

1. Freeze the event taxonomy and conversion hierarchy.
2. Confirm Meta Pixel event coverage and map the missing events.
3. Implement Meta CAPI using the same Purchase / Checkout / Cart / ViewContent events as browser Pixel.
4. Reserve track.pureleven.com exclusively for GTM Server and deploy the server container on Cloud Run.
5. Export GA4 to BigQuery.
6. Launch only the core campaign set, not the full AI roadmap yet.
7. Start creative production as a structured testing program.
8. Add CRM feedback loops only after the measurement layer is trusted.

## Decision

The correct strategy is not to treat Google Ads and Meta Ads as separate ad accounts.

The correct strategy is to build a unified growth operating system with:

- one tracking architecture
- one event taxonomy
- one first-party data layer
- two distinct channel roles
- one reporting truth layer
- one future AI optimization layer

That is the architecture most aligned with Pureleven's current storefront, your planned infrastructure, and your longer-term AI product direction.