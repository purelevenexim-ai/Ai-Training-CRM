# PureLeven WhatsApp CRM - Customer Scenarios and Journey Review

## 1) What is still pending

## Pending A - External platform execution (not code)
- Create and submit all 27 Meta templates from deploy/meta_template_registry_v2.csv
- Get approvals and fill template_id and approval_status in the same CSV
- Import and activate the 8 n8n workflow exports from deploy/n8n_exports/
- Wire production webhook sources to n8n webhook endpoints (Meta/Wabis/Delhivery)
- Register Delhivery webhook in Delhivery dashboard with production endpoint and secret
- Complete staged rollout gates: 100 customers -> 500 customers -> full

## Pending B - Production hardening and operations
- Set all required env vars in production (Meta, Shopify, OpenRouter, Delhivery)
- Execute server checklist from deploy/PRODUCTION_GO_LIVE_COMMAND_CHECKLIST.md
- Configure alert thresholds and on-call response for daily monitoring
- Review logs daily in first 7 days after go-live

## Pending C - Optional Phase 2 optimization
- Replace v1 template selection with v2/relationship routing once Meta approves 27 templates
- Add deeper personalization rules using content preferences and affinity scores
- Add weekly KPI review and A/B testing iteration loop

---

## 2) Current live architecture

## Day-based template journey engine
- Orchestrator endpoint: POST /api/journey/orchestrate
- Cohort preview endpoint: POST /api/journey/orchestrate/preview
- Status endpoint: GET /api/journey/orchestrate/status
- Core send path:
  1. Orchestrator selects eligible customers by stage window
  2. journey_engine applies suppression and idempotency
  3. whatsapp_templates builds template vars
  4. wabis_client sends approved Meta template
  5. journey_messages and journey_engagement_events are updated

## 24-hour AI conversation engine
- Session open endpoint: POST /api/ai/session/open
- Dispatch endpoint: POST /api/ai/dispatch
- Trigger:
  - Template delivered event from Meta webhook opens session
- Followup schedule per session:
  - T+10m story
  - T+1h social proof
  - T+4h offer
  - T+12h urgency
  - T+23h soft exit
- Guardrails:
  - AI chooses parameters only
  - Backend renders from verified Shopify data

## Engagement tracking
- Click: POST /api/tracking/whatsapp-click (+5)
- Reply: POST /api/tracking/whatsapp-reply (+7)
- Call: POST /api/tracking/whatsapp-call (+10)
- Unsubscribe: POST /api/tracking/whatsapp-unsubscribe
- Segment thresholds:
  - vip >= 80
  - responsive >= 40
  - low >= 5
  - dormant < 5

---

## 3) Journey flows and message count

## Flow family A - Delivery and onboarding (transactional)
- Stages: order_confirmed -> in_transit -> out_for_delivery
- Typical count: 2 to 3 messages
- Trigger basis: order creation and delivery progression

## Flow family B - Post-delivery review journey
- Stages: delivered (day5) -> review incentive (day15) -> optional reminder -> optional thank-you
- Typical count: 1 to 4 messages
- Trigger basis: delivered_at windows and responsiveness

## Flow family C - Upsell journey
- Stages: upsell (day30) -> optional upsell followup -> optional price-sensitive sale
- Typical count: 1 to 3 messages
- Trigger basis: responsive customers and recommendation availability

## Flow family D - Corporate/B2B journey
- Stages: corporate (day60) -> optional corporate followup
- Typical count: 1 to 2 messages
- Trigger basis: score and engagement quality

## Flow family E - Loyalty and RFM journey
- Stages: loyalty (day75) -> rfm/winback (day95)
- Typical count: 1 to 2 messages
- Trigger basis: segment and inactivity pattern

## Flow family F - 24-hour conversational conversion window
- Stages: story -> social_proof -> offer -> urgency -> soft_exit
- Typical count: 5 followups inside one 24h window
- Trigger basis: template delivery and active session

## Combined touches
- Standard customer (day-based only): 3 to 9 touches across journey timeline
- Standard customer + AI 24h sessions: day-based touches plus 5-message conversational bursts per triggered session

---

## 4) Customer scenario matrix

## Scenario 1 - Cold customer (low or dormant)
- Profile:
  - low: score 5-39
  - dormant: score < 5
- Strategy:
  - lower frequency
  - value-first, non-pushy copy
  - reactivation and support messaging
- Message behavior:
  - dormant suppression blocks most marketing stages except RFM/winback
  - review/upsell/loyalty are limited unless engagement improves

## Scenario 2 - Warm customer (responsive)
- Profile:
  - score 40-79
  - clicks/replies/calls present
- Strategy:
  - educational + trust + soft offer
  - normal cadence for review and upsell tracks
- Message behavior:
  - eligible for day15, day30, day75 tracks
  - receives 24h AI followups when session opens

## Scenario 3 - Hot customer (vip)
- Profile:
  - score >= 80
- Strategy:
  - premium tone
  - priority support and exclusive offers
  - shorter path to conversion asks
- Message behavior:
  - VIP variants in delivered/RFM paths
  - preferred for exclusive and high-intent campaigns

## Scenario 4 - Purchase-intent reply
- Signal:
  - AI classifies intent as purchase_intent
- Action:
  - owner alert sent
  - no uncontrolled autopush
  - sales follow-up can be prioritized

## Scenario 5 - Bulk inquiry reply
- Signal:
  - AI classifies bulk_inquiry
- Action:
  - critical owner alert sent
  - treated as B2B lead

## Scenario 6 - Complaint reply
- Signal:
  - AI classifies complaint
- Action:
  - owner alert sent
  - customer paused from marketing flow (do_not_message)

## Scenario 7 - Unsubscribe
- Signal:
  - unsubscribe intent or explicit unsubscribe endpoint
- Action:
  - subscription status set unsubscribed
  - session closed
  - no further marketing sends

---

## 5) Active template inventory in code (v1)

These are currently used by app/whatsapp_templates.py:
- order_confirmed_v1
- delivery_begun_v1
- delivery_out_for_delivery_v1
- delivered_review_request_v1
- delivered_vip_v1
- review_incentive_v1
- review_faq_response_v1
- review_reminder_v1
- review_thank_you_v1
- explore_products_v1
- upsell_followup_v1
- price_sensitive_sale_v1
- corporate_pitch_high_v1
- corporate_pitch_low_v1
- corporate_followup_v1
- loyalty_checkin_v1
- vip_exclusive_v1
- repeat_buyer_exclusive_v1
- winback_offer_v1
- extreme_winback_v1
- reactivation_survey_v1
- promo_monsoon_v1
- promo_diwali_v1
- promo_new_harvest_v1
- promo_bulk_sale_v1

Total active in code: 25

---

## 6) Planned relationship template inventory (27)

Reference file: deploy/meta_template_registry_v2.csv

- order_confirmed_v2
- delivery_begun_v2
- out_for_delivery_v2
- delivered_review_request_v2
- delivered_vip_v2
- review_reminder_v2
- explore_products_v2
- upsell_followup_v2
- price_sensitive_sale_v2
- loyalty_checkin_v2
- vip_exclusive_v2
- winback_offer_v2
- extreme_winback_v2
- reactivation_survey_v2
- corporate_pitch_v2
- promo_monsoon_v2
- promo_diwali_v2
- promo_new_harvest_v2
- recipe_series_v1
- founder_note_v1
- reduced_frequency_v1
- seasonal_education_v1
- storage_tips_v1
- harvest_stories_v1
- support_checkin_v1
- replenishment_reminder_v1
- cooking_inspiration_v1

Total planned for Meta submission: 27

Paste-ready copy source for review: deploy/meta_templates_prefilled_27.md

---

## 7) How to approach cold, warm, hot customers

## Cold (low + dormant)
- Objective: rebuild trust and re-engage without fatigue
- Mix:
  - 70% educational and support-oriented
  - 20% relationship/trust copy
  - 10% soft offers
- Cadence:
  - low: reduced cadence
  - dormant: mostly suppressed, winback only
- Templates to favor:
  - support_checkin_v1, reduced_frequency_v1, seasonal_education_v1, reactivation_survey_v2, winback_offer_v2

## Warm (responsive)
- Objective: nudge to review, repeat purchase, and cross-sell
- Mix:
  - 60% educational/value
  - 20% trust/founder/harvest
  - 20% conversion CTA
- Cadence:
  - normal day15/day30/day75 + session followups
- Templates to favor:
  - delivered_review_request_v2, explore_products_v2, recipe_series_v1, storage_tips_v1, replenishment_reminder_v1

## Hot (vip)
- Objective: maximize repeat and referrals while keeping premium experience
- Mix:
  - 40% value
  - 30% exclusives/trust
  - 30% conversion and VIP access
- Cadence:
  - fastest valid path with exclusives and personalized followups
- Templates to favor:
  - delivered_vip_v2, vip_exclusive_v2, founder_note_v1, promo_new_harvest_v2, corporate_pitch_v2 (if relevant)

---

## 8) Review links for you
- Template registry: deploy/meta_template_registry_v2.csv
- Template copy draft (27): deploy/meta_templates_prefilled_27.md
- n8n exports (8): deploy/n8n_exports/
- n8n import order: deploy/n8n_exports/IMPORT_ORDER.txt
- Go-live command runbook: deploy/PRODUCTION_GO_LIVE_COMMAND_CHECKLIST.md
