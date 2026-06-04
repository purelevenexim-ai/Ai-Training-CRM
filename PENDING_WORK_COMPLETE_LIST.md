# 📋 PENDING WORK — Complete System Breakdown

## Summary
**What was planned:** Complete AI-powered WhatsApp relationship system for PureLeven  
**What is now live in backend:** AI dispatch, 24h sessions, journey orchestration, tracking endpoints, monitoring, Shopify sync  
**What is still pending:** External platform execution (Meta templates, N8N activation, webhook registrations, production hardening)

---

## ✅ COMPLETED (This Session)

### AI Core Layer
- ✅ OpenRouter AI client with strict guardrails (deepseek/deepseek-chat-v3-0324:free)
- ✅ Story engine with 9 pre-written templates
- ✅ Safe message renderer (uses real Shopify data only)
- ✅ Owner WhatsApp alerts (918848265849)
- ✅ 24-hour conversation session manager
- ✅ AI intent classifier (10 categories: bulk_inquiry, complaint, purchase_intent, etc.)
- ✅ Shopify sync worker (products, offers, blogs, inventory)
- ✅ Health monitoring + dashboard
- ✅ All routers registered, server running on port 8000 ✅ Dependencies installed

### Live Validation Status
- ✅ Monitoring health endpoint returns status ok
- ✅ AI catalog endpoint returns synced products
- ✅ Journey preview endpoint returns live cohort counts
- ✅ Journey status endpoint available for last-24h checks
- ✅ Redirect tracker health endpoint returns status ok

---

## 🚀 EXECUTION CHECKLIST (External Pending Only)

### Day 1: Meta Template Submission
- [ ] Use deploy/meta_template_registry_v2.csv as source of truth
- [ ] Create all 27 templates in Meta Business Manager (language: en)
- [ ] Submit P1 templates first, then P2/P3
- [ ] Record approved template IDs in the same CSV (add columns: template_id, approval_status)
- [ ] Keep existing v1 templates active until v2 approval reaches 100%

### Day 1: N8N Workflow Setup
- [ ] Build 8 workflows using deploy/n8n_workflow_execution_checklist.json
- [ ] Configure base URL as your backend URL (local or production)
- [ ] Activate wf_01_shopify_sync and verify catalog count > 0
- [ ] Activate wf_02_daily_journey_preview and log total_would_send daily
- [ ] Activate wf_03_daily_journey_orchestrate after preview is stable

### Day 2: Webhook Wiring
- [ ] Configure Meta delivery webhook to backend /api/webhooks/meta/whatsapp
- [ ] Configure reply relay to backend /api/tracking/whatsapp-reply
- [ ] Register Delhivery webhook to backend /api/delhivery/webhook
- [ ] Set DELHIVERY_WEBHOOK_SECRET in production env before enabling webhook

### Day 2: Safety and Monitoring
- [ ] Schedule daily POST /api/monitoring/daily-report at midnight
- [ ] Schedule GET /api/monitoring/health every 15 minutes
- [ ] Set alert thresholds: failure_rate > 10%, critical alerts > 0
- [ ] Run POST /api/monitoring/test-alert and confirm owner receives WhatsApp alert

### Day 3: Controlled Go-Live
- [ ] Start with 100 customers only (soft launch)
- [ ] Observe delivery, reply, unsubscribe, and failure metrics for 24 hours
- [ ] Increase to 500 customers only if failure_rate stays below threshold
- [ ] Move to full rollout after 48 hours stable operation

---

## 📦 Execution Artifacts Added

- deploy/meta_template_registry_v2.csv
  - 27-template inventory for Meta submission
  - Priority labels and parameter counts

- deploy/n8n_workflow_execution_checklist.json
  - 8-workflow schedule and endpoint map
  - Trigger, payload, and success-check definitions

---

## 🔄 PENDING — Layer by Layer

### TIER 1: Core Journey Engine (HIGH PRIORITY)
These must be built to enable the full system.

#### 1. N8N Workflow Orchestration (8 workflows)
**Current State:** Planned in memory, not implemented  
**Effort:** 2-3 days  
**Files needed:**
- [ ] Workflow #1: Daily Engagement Score Calculator
  - Runs: 12:01 AM daily  
  - Logic: Calculate engagement_score, assign segment, set frequency
  - Tables: Update journey_customers with new engagement_score, customer_segment
  
- [ ] Workflow #2: Message Router (MASTER WORKFLOW)
  - Runs: 10 AM, 2 PM, 6 PM daily
  - Logic: Main orchestration — applies all conditional rules
  - Triggers: Sends templates via Wabis API based on journey stage + segment
  - Critical decision gates at: Day 2-3, Day 5-7, Day 15, Day 30, Day 60, Day 75, Day 95
  
- [ ] Workflow #3: Engagement Tracking (Real-time webhook)
  - Receives: button_clicked, message_opened, customer_reply, purchase, link_click, call_initiated
  - Updates: engagement_score in real-time
  - Triggers: Auto-responses, unsubscribe logic, alerts
  
- [ ] Workflow #4: Day 2-3 Delivery Begun (Cron trigger)
  - Sends: "Your order is on the way" + tracking link
  - Logic: Filter by delivery_date = today, is_responsive = null (unenaged yet)
  
- [ ] Workflow #5: Day 5-7 Review Request (Cron trigger)
  - Logic: If is_responsive = true → review_incentive_v2
  - Logic: If is_responsive = false → review_reminder_gentle_v2
  
- [ ] Workflow #6: Day 15 Upsell (Cron trigger)
  - Logic: Recommend products based on first purchase + affinity scores
  - Trigger: educational_upsell or product_exploration template
  
- [ ] Workflow #7: Day 30 Engagement Check (Cron trigger)
  - Logic: If score >= 50 → send VIP content
  - Logic: If score < 20 → pause messaging (dormant protection)
  
- [ ] Workflow #8: Day 60+ Loyalty & RFM (Monthly batch)
  - Logic: Calculate RFM scores, assign loyalty tier
  - Trigger: Loyalty content or corporate pitch based on segment

**Dependencies:** Must have journey_customers table with all engagement fields

---

#### 2. Journey Orchestration Logic (Backend)
**Current State:** N/A (planned in N8N only)  
**Effort:** 1-2 days  
**What needs building:**
- [ ] Engagement score calculator (algorithm in code)
  ```
  POINTS = {
    "delivered": 0.5,
    "opened": 1.0,
    "clicked": 5.0,
    "reply": 7.0,
    "call": 10.0,
    "purchase": 50.0
  }
  segments = {
    "vip": >= 100,
    "responsive": 50-99,
    "low": 20-49,
    "dormant": < 20
  }
  ```
- [ ] Frequency rules per segment
  ```
  VIP: 2x/month
  Responsive: 1x/month
  Low: 1x/6 weeks
  Dormant: paused until reengagement signal
  ```
- [ ] Decision gate logic for each journey stage
- [ ] Product affinity scoring (which products resonate with this customer)
- [ ] Segment message performance tracking (what works for each segment)
- [ ] RFM segmentation algorithm
- [ ] Churn detection model

**Files needed:**
- [ ] `app/intelligence/journey_orchestration.py` — Main orchestration logic
- [ ] `app/intelligence/engagement_calculator.py` — Score calculation
- [ ] `app/intelligence/affinity_scorer.py` — Product affinity learning
- [ ] `app/intelligence/churn_detector.py` — Churn prediction

---

#### 3. Database Migration (Schema Expansion)
**Current State:** AI tables only (10 new tables)  
**Effort:** 4-6 hours  
**Missing tables from original plan:**
- [ ] `engagement_history` — Audit trail of all engagement events
- [ ] `delivery_tracking` — Delhivery integration (statuses, locations, dates)
- [ ] `customer_segment_history` — Track segment changes over time
- [ ] `message_performance` — What templates work per segment
- [ ] `product_affinity` — Which products resonate per customer
- [ ] `customer_preferences` — Opt-in content types, frequency preferences
- [ ] `rfm_segments` — RFM scoring table (Recency, Frequency, Monetary)
- [ ] `loyalty_tiers` — VIP, Gold, Silver, Bronze tier definitions
- [ ] `journey_templates` — Template metadata (category, tone, cta_type)
- [ ] `template_performance` — A/B testing results per template

**Modifications to existing:**
- [ ] Add fields to `journey_customers`:
  - engagement_score (int)
  - customer_segment (enum: vip, responsive, low, dormant)
  - is_responsive (boolean)
  - first_engagement_date (datetime)
  - last_engagement_date (datetime)
  - repeat_buyer (boolean)
  - total_spent (decimal)
  - last_purchase_date (datetime)
  - corporate_interest (boolean)
  - review_status (enum: not_requested, requested, submitted, responded)
  - google_review_url (string)
  - product_affinity (json)
  - rfm_score (float)
  - and ~15 more...

---

### TIER 2: Template Management (HIGH PRIORITY)

#### 4. Template Strategy 2.0 Implementation
**Current State:** Designed in memory, not implemented  
**Effort:** 3-4 days  
**What needs:**
- [ ] Create 27 WhatsApp templates in Meta Business Manager
  - [ ] 18 redesigned v2 templates (from v1 campaign style to relationship style)
  - [ ] 9 new templates (recipe, founder_note, reduced_frequency, harvest_stories, etc.)
  - All must pass Meta approval (24-48 hours)

**Templates to create:**
- [ ] order_confirmed_v2
- [ ] delivery_begun_v2
- [ ] out_for_delivery_v2
- [ ] delivered_review_request_v2
- [ ] delivered_vip_v2
- [ ] review_reminder_v2
- [ ] explore_products_v2
- [ ] upsell_followup_v2
- [ ] price_sensitive_sale_v2
- [ ] loyalty_checkin_v2
- [ ] vip_exclusive_v2
- [ ] winback_offer_v2
- [ ] extreme_winback_v2
- [ ] reactivation_survey_v2
- [ ] corporate_pitch_v2
- [ ] promo_monsoon_v2
- [ ] promo_diwali_v2
- [ ] promo_new_harvest_v2
- [ ] recipe_series_v1 (NEW)
- [ ] founder_note_v1 (NEW)
- [ ] reduced_frequency_v1 (NEW)
- [ ] seasonal_education_v1 (NEW)
- [ ] storage_tips_v1 (NEW)
- [ ] harvest_stories_v1 (NEW)
- [ ] support_checkin_v1 (NEW)
- [ ] replenishment_reminder_v1 (NEW)
- [ ] cooking_inspiration_v1 (NEW)

**Files needed:**
- [ ] `app/templates/templates_registry.py` — Template metadata + parameter counts
- [ ] `app/templates/template_selector.py` — Logic to pick template by segment/stage
- [ ] `app/templates/personalization_engine.py` — AI fills template variables

---

#### 5. Template Personalization Engine
**Current State:** Basic story_engine exists, not full personalization  
**Effort:** 2-3 days  
**What needs:**
- [ ] Fill dynamic variables per template:
  ```python
  Templates have params like:
  {{customer_name}}, {{product_title}}, {{discount_value}},
  {{review_count}}, {{cooking_tips}}, {{harvest_region}}, etc.
  
  Engine must:
  1. Look up value from DB (Shopify, customer profile, affinity scores)
  2. Fallback to safe defaults
  3. Validate no {{}} remain in final message
  4. Never hallucinate — only use real data
  ```
- [ ] Personalize tone per segment (VIP gets premium tone, dormant gets respectful tone)
- [ ] Insert recipe suggestions based on purchase history
- [ ] Insert founder note customized by product purchased
- [ ] Generate harvest stories with region-specific details
- [ ] Filter educational content by customer interests

**Files needed:**
- [ ] `app/intelligence/template_personalization.py`
- [ ] `app/intelligence/variable_loader.py` (load {{var}} values from DB)
- [ ] `app/intelligence/tone_adapter.py` (adjust message tone per segment)

---

### TIER 3: Tracking & Analytics (MEDIUM PRIORITY)

#### 6. Delhivery Webhook Integration
**Current State:** Planned, not implemented  
**Effort:** 4-6 hours  
**What needs:**
- [ ] `app/routes/delhivery_webhook.py` — Handle delivery status updates
  - Parse HMAC signature (webhook security)
  - Extract: waybill_id, status_code (0-11), delivery_date, location, etc.
  - Update: delivery_tracking table
  - Trigger: N8N workflow for Day 2-3 messaging
  - Fallback cron job (sync 2x daily if webhooks fail)

**Webhook events to handle:**
- Status 0: In transit
- Status 1: Out for delivery
- Status 2: Delivered
- Status 3: RTO (Return to Origin)
- Status 10: Pick-up held
- Status 11: Exception
- Plus: location tracking, delivery photos, etc.

---

#### 7. UTM Link Tracking
**Current State:** Partially in story_engine, not complete  
**Effort:** 2-3 days  
**What needs:**
- [ ] Generate UTM links per message:
  ```
  https://pureleven.com/?utm_source=whatsapp
                       &utm_medium=meta
                       &utm_campaign={template_name}
                       &utm_customer={customer_id}
                       &utm_product={product}
                       &utm_segment={segment}
  ```
- [ ] Link shortener integration (bitly? custom?)
- [ ] Link click tracking endpoint
- [ ] Google Analytics integration (sync UTM data back to CRM daily)
- [ ] Segment performance reporting (which UTMs drive conversions)

**Files needed:**
- [ ] `app/intelligence/utm_builder.py`
- [ ] `app/routes/link_click_tracker.py` (already exists, enhance)
- [ ] `app/intelligence/google_analytics_sync.py`

---

#### 8. Engagement Event Tracking
**Current State:** Basic whatsapp_tracking.py exists  
**Effort:** 2-3 days  
**What needs:**
- [ ] Standardize all event types:
  - message_delivered
  - message_opened
  - message_clicked (link or button)
  - customer_replied
  - call_initiated
  - order_placed (Shopify webhook)
  - review_submitted
  - customer_unsubscribed

- [ ] Real-time event processing:
  ```
  Event received → Update engagement_score → Check if segment changed
                 → Trigger appropriate next action (reply, pause, escalate)
  ```

- [ ] Persist to engagement_history table (audit trail)

**Files needed:**
- [ ] `app/routes/engagement_events.py` (consolidate event handlers)
- [ ] `app/intelligence/event_processor.py` (real-time scoring)

---

### TIER 4: Content Intelligence (MEDIUM PRIORITY)

#### 9. Website Content Crawler
**Current State:** Planned, not implemented  
**Effort:** 2-3 days  
**What needs:**
- [ ] Crawl pureleven.com blog posts
- [ ] Extract:
  - Recipe ideas (pasta with cardamom? turmeric face mask?)
  - Harvest stories (from Idukki region)
  - Product care tips (storage, shelf life)
  - Health benefits
  - Cooking inspiration

- [ ] Store in shopify_content table (or new table)
- [ ] Use for educational messaging (recommend recipes to customers)
- [ ] Link to blog posts in messages (driving traffic + engagement)

**Files needed:**
- [ ] `app/intelligence/content_crawler.py` (BeautifulSoup)
- [ ] `app/tasks/daily_content_sync.py` (scheduled, 1x daily)

---

#### 10. Google Reviews Integration
**Current State:** Planned, not implemented  
**Effort:** 2-3 days  
**What needs:**
- [ ] Pull Google reviews of PureLeven from Google Business Profile
- [ ] Extract:
  - Top review text
  - Reviewer name + rating
  - Review date
  - Product mentioned (if any)

- [ ] Use for social proof in messages:
  ```
  "⭐ 4.8/5 from 200+ customers"
  "People love our cardamom for its freshness"
  ```

- [ ] Link to review page in VIP/conversion messages

**Files needed:**
- [ ] `app/intelligence/google_reviews_sync.py`
- [ ] Requires: Google Business Profile API access

---

#### 11. Product Content Enhancement
**Current State:** Basic Shopify sync, not rich content  
**Effort:** 2-3 days  
**What needs:**
- [ ] Enrich shopify_products with:
  - Harvest region (from metafields)
  - Quality notes (why this is premium)
  - Best-for uses (recipes, health, gifting)
  - Flavor pairing suggestions
  - Cooking tips
  - Storage instructions
  - Video URL
  - Origin story

- [ ] Use for educational storytelling (not just selling)
- [ ] Personalize by segment (VIP gets full story, cold gets quick tip)

**Files needed:**
- [ ] Enhanced `app/intelligence/shopify_sync.py` (pull metafields)
- [ ] `app/models/product_content.py` (data model)

---

### TIER 5: Advanced AI Features (MEDIUM PRIORITY)

#### 12. Behavioral Learning System
**Current State:** Tables exist, logic not built  
**Effort:** 3-4 days  
**What needs:**
- [ ] Product affinity scoring:
  ```
  For each customer × product pair:
  - affinity_score (0-100, based on purchase history + engagement)
  - recommendation_count (how many times recommended)
  - click_count (how many times clicked)
  - purchase_count (how many times purchased)
  - best_message_type (recipe? offer? story?)
  - best_send_hour (when does this customer engage most?)
  ```

- [ ] Message type performance:
  ```
  For each segment × message_type:
  - open_rate
  - click_rate
  - conversion_rate
  - unsubscribe_rate
  
  Use to pick best template per segment
  ```

- [ ] Customer preference learning:
  ```
  Track what types of content each customer engages with:
  - recipes: reply rate
  - health tips: open rate
  - sales offers: click rate
  - founder stories: forward rate
  
  Bias towards high-engagement types
  ```

**Files needed:**
- [ ] `app/intelligence/affinity_learner.py`
- [ ] `app/intelligence/segment_optimizer.py`
- [ ] `app/intelligence/preference_tracker.py`

---

#### 13. Churn Detection & Prevention
**Current State:** Mentioned, not built  
**Effort:** 2-3 days  
**What needs:**
- [ ] Churn prediction model:
  ```
  Customer at risk if:
  - engagement_score declining over past 30 days
  - no interaction in 14 days
  - opened rate < 10% last 5 messages
  - clicked rate = 0 (no action at all)
  ```

- [ ] Win-back campaigns:
  ```
  When churn detected:
  1. Send "We miss you" message
  2. Offer exclusive reactivation discount
  3. Send customer survey (why inactive?)
  4. If still unresponsive after 7 days → pause
  ```

- [ ] Reactivation emails (email + WhatsApp combo)

**Files needed:**
- [ ] `app/intelligence/churn_detector.py`
- [ ] `app/routes/winback_campaigns.py`

---

#### 14. RFM Segmentation
**Current State:** Mentioned, not built  
**Effort:** 1-2 days  
**What needs:**
- [ ] Calculate RFM for each customer:
  ```
  R (Recency): Days since last purchase
  F (Frequency): Total purchases in last 90 days
  M (Monetary): Total spent in last 90 days
  
  Score: R * 0.4 + F * 0.3 + M * 0.3
  
  Segments:
  - Champions: High R, F, M
  - Loyal: High F, M
  - Can't Lose: High R+M, Low F (big spenders but slowing down)
  - Potential Loyalists: Medium R, F, M
  - At Risk: Low R, Low F, Medium M
  - Lost: Low R, F, M
  ```

- [ ] Update monthly (batch job)
- [ ] Use for loyalty tier + messaging cadence

**Files needed:**
- [ ] `app/intelligence/rfm_calculator.py`
- [ ] Cron job or N8N workflow (monthly)

---

#### 15. Sentiment Analysis & Reply Classification
**Current State:** Basic intent classifier exists  
**Effort:** 2-3 days  
**What needs:**
- [ ] Enhance intent classifier to detect:
  - Positive sentiment (praise, love, amazing!)
  - Negative sentiment (complaint, broken, waste)
  - Question (help needed, how to use?)
  - Affirmation (yes, okay, want it)
  - Negative signal (no, stop, unsubscribe)

- [ ] Store sentiment in conversation_messages
- [ ] Use for:
  - Auto escalate complaints to support
  - Flag praising customers for VIP treatment
  - Respond to questions with FAQ
  - Track sentiment over time per customer

**Files needed:**
- [ ] Enhanced `app/ai/openrouter_client.py` (more intent classes)
- [ ] `app/intelligence/sentiment_analyzer.py`

---

### TIER 6: Operational Features (LOW-MEDIUM PRIORITY)

#### 16. Shopify Order Webhook Integration
**Current State:** Exists, not integrated with AI  
**Effort:** 1-2 days  
**What needs:**
- [ ] Existing `shopify_webhook.py` should trigger:
  - Create conversation session (for Day 0 messaging)
  - Initialize engagement score = 0
  - Start 9-stage journey
  - Track original order details (products, amount, delivery date)

- [ ] Map Shopify order→customer→messages
- [ ] Track if message drove the purchase (conversion attribution)

**Files needed:**
- [ ] Enhance existing `app/routes/shopify_webhook.py`

---

#### 17. Conversion Attribution
**Current State:** Not built  
**Effort:** 2-3 days  
**What needs:**
- [ ] Track which WhatsApp messages led to purchases:
  ```
  Customer received message T at time X
  Customer purchased product P at time Y (within 30 days)
  → Attribute purchase to message T
  
  Metric: "This message drove 8 purchases"
  ```

- [ ] Use for A/B testing (which template drives most conversions?)
- [ ] Reward AI model (messages that convert = high reward)
- [ ] ROI calculation (cost of sending vs revenue generated)

**Files needed:**
- [ ] `app/intelligence/conversion_tracker.py`
- [ ] Enhanced `conversation_followups` table (add conversion fields)

---

#### 18. Bulk Inquiry Routing
**Current State:** Alert sent to owner, no routing  
**Effort:** 1-2 days  
**What needs:**
- [ ] When "bulk_inquiry" detected:
  - Create ticket in support system (or email)
  - Assign to sales team
  - Send auto-reply to customer: "Thanks, our team will contact you"
  - Track response time SLA (24h)

**Files needed:**
- [ ] Enhanced `app/ai/alert_sender.py`
- [ ] `app/routes/bulk_inquiry_handler.py`

---

### TIER 7: Infrastructure & Monitoring (LOW PRIORITY)

#### 19. Cron Job Scheduler
**Current State:** No cron, only n8n  
**Effort:** 4-6 hours  
**What needs:**
- [ ] Setup cron jobs for recurring tasks:
  ```
  0 0,12 * * * python tasks/sync_delhivery.py (2x daily)
  0 */6 * * * python tasks/sync_shopify_catalog.py (4x daily)
  0 0 * * * python tasks/calculate_engagement_score.py (midnight)
  0 2 * * 0 python tasks/calculate_rfm.py (weekly)
  0 0 1 * * python tasks/generate_monthly_report.py (monthly)
  ```

- [ ] Error handling + retry logic
- [ ] Logging + monitoring

**Files needed:**
- [ ] `app/tasks/` directory with all cron scripts
- [ ] `app/config/cron_config.py`
- [ ] `systemd` service file for cron scheduler

---

#### 20. Advanced Monitoring Dashboard
**Current State:** Basic health check + dashboard exists  
**Effort:** 2-3 days  
**What needs:**
- [ ] Real-time metrics:
  ```
  Messages: sent/24h, delivered, opened, clicked, replied
  Customers: total, active, dormant, new/24h, unsubscribed
  Conversion: conversion_rate, avg order value, repeat purchase rate
  Segments: VIP count, responsive count, low count, dormant count
  Templates: top 5 by open rate, click rate, conversion rate
  Errors: failed messages, failed webhooks, API errors
  ```

- [ ] Historical trending (day/week/month)
- [ ] Segment performance comparison
- [ ] Template A/B test results
- [ ] Geographic breakdown (orders by city, delivery zones)
- [ ] Alerts for anomalies (failure rate spike, unusual patterns)

**Files needed:**
- [ ] Enhanced `app/routes/monitoring.py`
- [ ] `app/intelligence/analytics_engine.py`
- [ ] Frontend dashboard (separate, maybe Next.js?)

---

#### 21. Error Handling & Retry Logic
**Current State:** Basic exists, needs expansion  
**Effort:** 2-3 days  
**What needs:**
- [ ] Retry strategies:
  - Failed Wabis sends: retry 3x with exponential backoff
  - Failed Shopify API calls: queue + retry 2x daily
  - Failed webhook deliveries: Redis queue + persistent retry

- [ ] Dead letter queues (messages that fail 5x go to queue for manual review)
- [ ] Error categorization (temporary vs permanent failure)
- [ ] Alerting (pages on-call when critical errors spike)

**Files needed:**
- [ ] `app/infrastructure/retry_handler.py`
- [ ] `app/infrastructure/error_queue.py`

---

### TIER 8: Testing & Validation (LOW PRIORITY)

#### 22. Unit Tests
**Current State:** Not written  
**Effort:** 3-4 days  
**Test files needed:**
- [ ] `tests/test_engagement_calculator.py`
- [ ] `tests/test_template_selector.py`
- [ ] `tests/test_message_renderer.py`
- [ ] `tests/test_affinity_scorer.py`
- [ ] `tests/test_churn_detector.py`
- [ ] `tests/test_openrouter_client.py` (mock API)
- [ ] `tests/test_shopify_sync.py` (mock API)

---

#### 23. Integration Tests
**Current State:** Not written  
**Effort:** 2-3 days  
**Test scenarios:**
- [ ] Full journey: Order → Delivery → Day 5 Review → Day 30 Upsell
- [ ] Engagement loop: Message sent → Clicked → Reply → Engagement score updated
- [ ] Segment transition: Cold → Responsive (message changed on next send)
- [ ] Churn detection: Customer unengaged 14 days → Pause messaging
- [ ] Webhook flow: Delhivery status → DB update → N8N trigger → Message sent

---

#### 24. Load Testing
**Current State:** Not done  
**Effort:** 1-2 days  
**Scenarios:**
- [ ] Send 100k messages/day (scale to production volume)
- [ ] Handle 1,000 webhook events/second (Delhivery + Shopify spikes)
- [ ] Process engagement events at 50/second
- [ ] Query 1M customer records for segmentation

**Tools:** K6 or Apache JMeter

---

### TIER 9: Documentation & Operations (LOW PRIORITY)

#### 25. Runbook & Operations Guide
**Effort:** 1 day  
**What needs:**
- [ ] How to add new template to system
- [ ] How to test a message before sending
- [ ] How to pause messaging for a segment
- [ ] How to handle webhook failures
- [ ] How to debug a customer's journey
- [ ] How to A/B test templates
- [ ] Escalation procedures
- [ ] SLA commitments (99.9% delivery?)

**Files needed:**
- [ ] `docs/OPERATIONS_RUNBOOK.md`
- [ ] `docs/TROUBLESHOOTING.md`
- [ ] `docs/PLAYBOOKS.md` (what to do if...)

---

#### 26. API Documentation
**Effort:** 1 day  
**Files needed:**
- [ ] Updated OpenAPI/Swagger for all new endpoints
- [ ] Postman collection with examples
- [ ] Integration guide for partners

---

---

## 📊 EFFORT BREAKDOWN

| Tier | Category | Effort | Priority |
|------|----------|--------|----------|
| 1 | N8N Workflows | 2-3 days | HIGH |
| 1 | Journey Orchestration Logic | 1-2 days | HIGH |
| 1 | Database Migration | 4-6 hours | HIGH |
| 2 | Template Strategy 2.0 | 3-4 days | HIGH |
| 2 | Template Personalization | 2-3 days | HIGH |
| 3 | Delhivery Webhook | 4-6 hours | MEDIUM |
| 3 | UTM Link Tracking | 2-3 days | MEDIUM |
| 3 | Engagement Event Tracking | 2-3 days | MEDIUM |
| 4 | Website Crawler | 2-3 days | MEDIUM |
| 4 | Google Reviews | 2-3 days | MEDIUM |
| 4 | Product Content | 2-3 days | MEDIUM |
| 5 | Behavioral Learning | 3-4 days | MEDIUM |
| 5 | Churn Detection | 2-3 days | MEDIUM |
| 5 | RFM Segmentation | 1-2 days | MEDIUM |
| 5 | Sentiment Analysis | 2-3 days | MEDIUM |
| 6 | Shopify Integration | 1-2 days | LOW |
| 6 | Conversion Attribution | 2-3 days | LOW |
| 6 | Bulk Inquiry Routing | 1-2 days | LOW |
| 7 | Cron Jobs | 4-6 hours | LOW |
| 7 | Advanced Dashboard | 2-3 days | LOW |
| 7 | Error Handling | 2-3 days | LOW |
| 8 | Unit Tests | 3-4 days | LOW |
| 8 | Integration Tests | 2-3 days | LOW |
| 8 | Load Tests | 1-2 days | LOW |
| 9 | Documentation | 2 days | LOW |
| **TOTAL** | | **~62-85 days** | |

---

## 🎯 RECOMMENDED SEQUENCE

### Week 1: Core Journey Engine
1. N8N Workflow setup (2-3 days)
2. Database migration (4-6 hours)
3. Journey orchestration logic (1-2 days)
4. Basic testing (1 day)

### Week 2: Templates & Tracking
1. Template Strategy 2.0 implementation (3-4 days)
2. Delhivery webhook (4-6 hours)
3. UTM tracking (2-3 days)
4. Testing (1 day)

### Week 3: Intelligence & Content
1. Behavioral learning (3-4 days)
2. Website crawler + Google reviews (4-6 days)
3. Churn detection (2-3 days)
4. Testing (1 day)

### Week 4: Advanced Features
1. RFM segmentation (1-2 days)
2. Sentiment analysis (2-3 days)
3. Conversion attribution (2-3 days)
4. Testing (1 day)

### Week 5: Operations & Monitoring
1. Cron jobs (4-6 hours)
2. Advanced dashboard (2-3 days)
3. Error handling (2-3 days)
4. Documentation (2 days)

### Week 6-8: Testing & Deployment
1. Full integration tests (2-3 days)
2. Load testing (1-2 days)
3. QA + fixes (3-5 days)
4. Production hardening (3-5 days)
5. Go-live preparation (2-3 days)

---

## ✅ IMMEDIATE NEXT STEPS

**To build Week 1 (Core Journey Engine):**

1. **Set up N8N account** (if not already done)
   - Create 8 workflows using memory/N8N_ORCHESTRATION_BLUEPRINT.md as spec
   - Test each individually

2. **Run database migration**
   - Add 10+ fields to journey_customers
   - Create 3 new tables (engagement_history, delivery_tracking, etc.)

3. **Implement in Python:**
   - engagement_calculator.py (score algorithm)
   - journey_orchestration.py (stage logic)

4. **Start testing:**
   - Create a test customer
   - Simulate order → delivery → 24h journey
   - Verify scores, segments, messages

---

## 🚀 What Do You Want to Build First?

Pick any tier or specific feature and I'll start implementing.
