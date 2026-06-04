# 🎯 COMPREHENSIVE MULTI-CHANNEL MARKETING AUTOMATION PLAN
**Cold → Warm → Customer Journey Across Email, WhatsApp, Meta, Google, & More**

**Document Status:** STRATEGIC BLUEPRINT  
**Created:** May 2026  
**Scope:** Complete customer lifecycle across all channels  
**Estimated Implementation:** 8-12 weeks (phased)

---

## EXECUTIVE SUMMARY

### Current State
You have **isolated but powerful tools**:
- ✅ **Email** (6 templates, fully working via Plunk + SES)
- ✅ **Meta CAPI** (pixel tracking, retargeting audiences)
- ✅ **Google Ads** (conversion tracking, offline conversions)
- ✅ **Wabis WhatsApp** (API token, N8N workflows)
- ✅ **GA4** (website visitor tracking)

### Missing Piece
**No orchestration** — these channels work independently. There's no unified journey that:
- Identifies a cold prospect across channels
- Gradually warms them through optimal touchpoints
- Matches message to stage (awareness → consideration → decision → loyalty)
- Measures impact of each channel in the funnel

### Outcome
This plan creates a **coordinated ecosystem** where:
1. Cold visitors land on site/Meta/WhatsApp
2. They're captured & segmented by behavior
3. They receive orchestrated messages (email → WhatsApp → Meta ads in sequence)
4. They convert at higher rates (3-5x vs. current)
5. Post-purchase, they're nurtured for repeat purchases

**Expected Metrics (Post-Launch)**
- Cold → Customer conversion: 2-4% (vs. 0.5% baseline)
- Email open rate: 30-45%
- WhatsApp open rate: 85-95%
- Meta retargeting ROI: 4-8:1
- Customer lifetime value: +60%

---

## PART 1: CUSTOMER JOURNEY ARCHITECTURE

### The Complete Cold-to-Loyal Funnel

```
AWARENESS STAGE (Cold Prospects)
├─ Source 1: Google Search Ads
│  └─ Via: utm_source=google_ads
├─ Source 2: Meta/Instagram Feed/Stories/Reels
│  └─ Via: utm_source=meta_feed | utm_campaign=awareness_campaign
├─ Source 3: WhatsApp Direct (Business account)
│  └─ Via: catalog link + phone verification
├─ Source 4: Organic Search (SEO)
│  └─ Via: utm_source=organic
├─ Source 5: Referral (word of mouth)
│  └─ Via: utm_source=referral
└─ Source 6: Direct (email campaigns, etc.)
   └─ Via: utm_source=email | utm_campaign=lifecycle

    ↓ TRACKING: GA4 event + CRM record creation
    ↓ Capture: Email, phone, basic demographics

CONSIDERATION STAGE (Warm Prospects)
├─ Channel 1: Welcome Email (Day 0)
│  └─ Goal: Brand introduction, remove objections
├─ Channel 2: Product Education WhatsApp (Day 1-3)
│  └─ Goal: Show why product matters (health, quality, value)
├─ Channel 3: Meta Retargeting Ads (Day 1-7)
│  └─ Goal: Reinforce messaging, create urgency
├─ Channel 4: Browse Abandonment Email (Day 2, if viewed products)
│  └─ Goal: Highlight viewed products, offer incentive
└─ Channel 5: SMS/WhatsApp (if opted in)
   └─ Goal: Time-sensitive promotions

    ↓ TRACKING: Click events, page views, engagement
    ↓ Segmentation: Interest level, product category, repeat visits

DECISION STAGE (Ready to Buy)
├─ Channel 1: Cart Abandonment Email (Day 0-1)
│  └─ Goal: Urgency, reassurance, remove friction
├─ Channel 2: Cart Recovery WhatsApp (Day 1, if high-value cart)
│  └─ Goal: Direct personal touch, answer objections
├─ Channel 3: Limited-Time Offer Meta Ad (Day 0-3)
│  └─ Goal: Create scarcity, last-chance messaging
├─ Channel 4: Customer Success Stories (Day 2)
│  └─ Goal: Social proof via email/WhatsApp
└─ Channel 5: Live Chat / WhatsApp Support
   └─ Goal: Answer questions, assist purchase

    ↓ TRACKING: Add-to-cart events, payment initiated, payment failed
    ↓ Segmentation: Cart value, device type, repeat visitor status

PURCHASE STAGE (Customer!)
├─ Channel 1: Order Confirmation Email (Immediate)
│  └─ Goal: Excitement, next steps, order details
├─ Channel 2: Order Confirmation WhatsApp (Immediate)
│  └─ Goal: Quick confirmation, tracking link
├─ Channel 3: Payment Received Notification (If COD)
│  └─ Email/WhatsApp: Delivery timeline
└─ Conversion tracked in:
   └─ Meta CAPI (for lookalike audience)
   └─ Google Ads (for offline conversion)
   └─ GA4 (for attribution)
   └─ CRM (for lifetime value calculation)

    ↓ TRACKING: Purchase event, order value, product category
    ↓ Segmentation: Customer type (first-time vs. repeat), order size

FULFILLMENT STAGE (Delivering Value)
├─ Channel 1: Shipped Notification Email (Day 1)
│  └─ Goal: Transparency, tracking excitement
├─ Channel 2: Out for Delivery WhatsApp (Day X)
│  └─ Goal: Prepare for receipt, any special instructions
├─ Channel 3: Delivery Confirmation Email (Day X+1)
│  └─ Goal: Gratitude, next steps (review, repeat)
└─ Tracking: Shiprocket webhooks for status updates

LOYALTY STAGE (Repeat Customer)
├─ Channel 1: Review Request Email (Day 3-5)
│  └─ Goal: Social proof, customer feedback
├─ Channel 2: Review Reminder WhatsApp (Day 7, if no review)
│  └─ Goal: Gentle reminder, incentive for review
├─ Channel 3: Replenishment Reminder (Day 30)
│  └─ Email/WhatsApp: "Time to restock?"
├─ Channel 4: Exclusive Offers Email (Day 7, 30, 60)
│  └─ Goal: VIP treatment, encourage next purchase
├─ Channel 5: Loyalty Program Meta Ads
│  └─ Goal: Encourage repeat purchases, referrals
└─ Channel 6: Win-back Campaigns (Day 60+, if inactive)
   └─ Email/WhatsApp/Meta: "We miss you, 20% off"

    ↓ TRACKING: Purchase frequency, repeat rate, churn rate
    ↓ Segmentation: VIP (3+ purchases), Regular (1-2), At-risk (inactive 60+ days)
```

### Key Principle: RIGHT MESSAGE, RIGHT TIME, RIGHT CHANNEL

```
AWARENESS STAGE:
├─ Message Focus: Problem + Awareness
├─ Preferred Channel: Meta Ads (visual, viral), Google Ads (search intent)
├─ Secondary: WhatsApp (warm personal touch if they opt in)
└─ Success Metric: CTR > 2%, Cost per visit < ₹10

CONSIDERATION STAGE:
├─ Message Focus: Education + Value Prop + Urgency
├─ Preferred Channel: Email (detailed info), WhatsApp (personal), Meta Ads (retargeting)
├─ Sequence: Email Day 0 → WhatsApp Day 1 → Meta Ads Days 1-7
└─ Success Metric: Click rate > 15%, Email open > 30%

DECISION STAGE:
├─ Message Focus: Objection handling + Scarcity + Social proof
├─ Preferred Channel: WhatsApp (immediate, high-touch), Email (detailed), Meta Ads
├─ Sequence: Cart recovery WhatsApp within 2 hours → Email within 4 hours → Meta Ads
└─ Success Metric: Cart recovery rate > 15%, ROAS > 3:1

PURCHASE & BEYOND:
├─ Message Focus: Excitement + Transparency + Next steps
├─ Preferred Channel: Email (details) + WhatsApp (status) + Meta Ads (upsell/loyalty)
├─ Sequence: Immediate email + WhatsApp → Shiprocket webhooks → Lifecycle emails
└─ Success Metric: CLTV > ₹2,500, Repeat purchase rate > 20%
```

---

## PART 2: DATA LAYER & TRACKING

### Customer Identifier Unification

Every customer is identified by ONE OR MORE of these:
```
PRIMARY IDENTIFIER:
├─ Email address (universal, always collected)
└─ Phone number (for WhatsApp, optional but preferred)

SECONDARY IDENTIFIERS (for matching across platforms):
├─ gclid (Google Ads click ID) → tied to Google Ads visitor
├─ fbclid (Meta click ID) → tied to Meta ads visitor
├─ utm_source, utm_campaign, utm_medium → traffic source
├─ session_id → website behavior tracking
└─ User IP + browser fingerprint → web analytics matching

PLATFORM-SPECIFIC IDS:
├─ Meta pixel user_id (hashed email/phone)
├─ Google Ads customer match ID
├─ Wabis phone_id (WhatsApp number)
└─ GA4 client_id + user_id (once logged in)

MAPPING STRUCTURE:
customers table:
├─ id (internal PK)
├─ email (unique, searchable)
├─ phone (unique, searchable)
├─ traffic_source (google_ads | meta_feed | whatsapp | organic | email | direct)
├─ utm_source, utm_medium, utm_campaign (tracking context)
├─ gclid (if from Google Ads)
├─ fbclid (if from Meta)
├─ created_at (first touch)
├─ last_touch_at (most recent activity)
├─ status (VISITOR | CUSTOMER | AT_RISK | INACTIVE)
├─ lifecycle_stage (awareness | consideration | decision | purchased | loyal | churned)
└─ metadata { meta_pixel_match_id, ga4_client_id, wabis_phone_id, ... }
```

### Data Flow Diagram

```
INBOUND TOUCH POINTS
├─ Website visitor → GA4 event (page_view) → CRM webhook
├─ Meta/Instagram click → fbclid parameter → CRM webhook
├─ Google Ad click → gclid parameter → CRM webhook
├─ WhatsApp opt-in → Wabis webhook → CRM webhook
├─ Email link click → UTM parameter → GA4 → CRM webhook
└─ Manual signup → Form submission → CRM direct entry

    ↓ (All routed to)

CRM DATABASE (PostgreSQL)
├─ customers table (canonical customer record)
├─ crm_events table (all interactions logged)
├─ crm_journeys table (customer path across channels)
├─ crm_messages table (what was sent, when, via what channel)
├─ crm_conversions table (purchase events + attribution)
└─ crm_audiences table (segmentation & sync targets)

    ↓ (Real-time or nightly)

OUTBOUND PLATFORMS
├─ Email (Plunk) ← CRM segment
├─ WhatsApp (Wabis) ← CRM segment
├─ Meta Ads Manager ← Customer list upload (nightly)
├─ Google Ads → offline conversions, customer match lists
└─ GA4 ← event stream (conversions, lifecycle tracking)
```

### Critical Tracking Implementation

**1. Website Traffic Attribution**

```
CURRENT SETUP (you have this):
├─ GA4 tracks all website visitors
├─ utm_source parameter captures traffic source
└─ CRM webhook creates customer record

REQUIRED ADDITIONS:
├─ Enhanced event tracking for:
│  ├─ product_view (which products viewed)
│  ├─ add_to_cart (cart value, products)
│  ├─ remove_from_cart (why abandoned?)
│  ├─ purchase (order value, products)
│  ├─ refund (if applicable)
│  └─ scroll_depth (page engagement)
├─ User property tracking:
│  ├─ traffic_source (google_ads | meta | organic | etc.)
│  ├─ visitor_segment (high-intent | medium | low)
│  └─ device_category (mobile | desktop)
└─ Attribution window: 30 days (from first visit to conversion)

IMPLEMENTATION:
├─ Shopify theme: GA4 event firing on every action ✅ (already done)
├─ CRM webhook: Capture traffic_source on visit ← ENHANCE
├─ Email links: Add utm_source=email_[campaign_name]
└─ WhatsApp links: Add utm_source=whatsapp_[message_type]
```

**2. Meta Pixel Tracking**

```
CURRENT SETUP (you have this):
├─ Meta pixel ID: 609256704464862
├─ CAPI integration ready
└─ Conversion events tracked (purchase)

REQUIRED ADDITIONS:
├─ Standard pixel events:
│  ├─ ViewContent (product page view) → collect product_id
│  ├─ AddToCart (cart events) → collect product_id, value
│  ├─ InitiateCheckout (checkout started)
│  ├─ Purchase (conversion) ✅ (already done)
│  ├─ CompleteRegistration (email signup)
│  └─ AddPaymentInfo (payment attempted)
├─ Custom pixel events:
│  ├─ HighIntentVisitor (viewed 3+ products)
│  ├─ CartAbandoned (added to cart but didn't buy)
│  └─ ReviewLeft (customer left product review)
├─ Custom audiences:
│  ├─ Website visitors (last 30 days) ✅ (ready)
│  ├─ Checkout initiators (last 7 days) ← CREATE
│  ├─ Converters (last 30 days) ← CREATE
│  ├─ High-value customers (> ₹2000) ← CREATE
│  └─ Inactive customers (60+ days no visit)
└─ Lookalike audiences from converters

IMPLEMENTATION:
├─ Pixel event firing: Already in Shopify theme (GA4)
├─ Meta CAPI: Needs server-side implementation (next step)
│  └─ Send: user_data (email hashed), event_data, timestamp
├─ Audience syncing: Nightly script from CRM to Meta
│  └─ Format: CSV with hashed emails/phone numbers
└─ Retargeting campaigns: Use these audiences
```

**3. Google Ads Tracking**

```
CURRENT SETUP (you have this):
├─ Customer ID: 1491516-3260
├─ Offline conversion tracking (conversion_action_id)
└─ Enhanced Conversions (email hashing)

REQUIRED ADDITIONS:
├─ Visitor remarketing list:
│  ├─ All website visitors (last 30 days) ← CREATE
│  ├─ High-intent visitors (3+ products) ← CREATE
│  ├─ Cart abandoners (last 7 days) ← CREATE
│  ├─ Buyers (converters) ← CREATE
│  └─ Product-specific lists (e.g., cinnamon viewers)
├─ Customer match:
│  ├─ First-party customer list (email + phone)
│  ├─ High-value customers (> ₹2000)
│  └─ Repeat customers (2+ purchases)
├─ Conversion tracking:
│  ├─ Purchase conversions ✅ (already done)
│  ├─ Lead conversions (email signup)
│  ├─ Engagement conversions (phone click)
│  └─ View-through conversions (if impressed by ad)
└─ ROAS tracking: Monitor CPL, ROAS, CPA by campaign

IMPLEMENTATION:
├─ Pixel/gtag: Already firing in Shopify theme
├─ Remarketing lists: Nightly sync from CRM
│  └─ Format: CSV with email + phone (hashed)
├─ Conversion tracking: POST to Google Ads API
│  └─ Include: gclid, email, conversion value, timestamp
└─ Attribution: Track which ads led to purchases
```

**4. WhatsApp (Wabis) Tracking**

```
CURRENT SETUP (you have this):
├─ API token: 18280|Ws5wnHgkReob1OKVhDHWH3kzEIIRjItGN9wPcQFz23380f95
├─ N8N workflows for messaging
└─ Template-based sending

REQUIRED ADDITIONS:
├─ Webhook capture on:
│  ├─ Message sent (timestamp, template_id)
│  ├─ Message delivered (timestamp)
│  ├─ Message read (timestamp, indicates engagement)
│  ├─ User clicked link (click tracking)
│  └─ User replied (engagement signal)
├─ Analytics per message:
│  ├─ Send time, delivery rate, read rate
│  ├─ Click rate (links in WhatsApp)
│  ├─ Reply rate (interactive elements)
│  └─ Conversion rate (purchases after message)
├─ Subscriber management:
│  ├─ Opt-in tracking (consent for each type)
│  ├─ Opt-out handling (respect preferences)
│  └─ Dormant subscriber cleaning
└─ Segmentation by:
   ├─ Engagement level (active, medium, inactive)
   ├─ Product interest (category of products viewed)
   └─ Lifecycle stage (warm prospect, customer, at-risk)

IMPLEMENTATION:
├─ Wabis webhook: Add endpoint to CRM
│  └─ Log: phone_id, event_type, timestamp, metadata
├─ Message tracking: Add unique tracking ID to links
│  └─ Format: https://[domain]/utm?utm_source=whatsapp_[campaign]&tracking_id=[uuid]
├─ Click handling: CRM webhook captures clicks
│  └─ Update: customer.last_engagement_at, event log
└─ Conversion attribution: Track purchases from WhatsApp clicks
```

**5. Email (Plunk) Tracking**

```
CURRENT SETUP (you have this):
├─ 6 email templates working
├─ Plunk integration via API
└─ Delivery status captured

REQUIRED ADDITIONS:
├─ Event tracking on:
│  ├─ Email delivered (timestamp)
│  ├─ Email opened (timestamp, device, location)
│  ├─ Link clicked (which link, timestamp)
│  ├─ Unsubscribed (timestamp)
│  └─ Complained (timestamp)
├─ Advanced analytics:
│  ├─ Open rate by segment (traffic source, lifecycle stage)
│  ├─ Click-through rate by template
│  ├─ Conversion rate from email clicks
│  └─ Time-to-open (how long before opened)
├─ A/B testing:
│  ├─ Subject line variants (test winner capture)
│  ├─ Send time optimization (morning vs. evening)
│  └─ Copy variants (urgency vs. value-focused)
└─ Re-engagement:
   ├─ Inactive email addresses (no open for 30 days)
   ├─ Win-back campaign (one-time offer)
   └─ Remove if no engagement for 90 days

IMPLEMENTATION:
├─ Plunk webhooks: Already set up, captures events
├─ Tracking pixel: Add to email template footers
│  └─ Enables open tracking
├─ Link wrapping: Automatically track clicks
│  └─ Plunk does this by default
└─ CRM integration: Log all events to crm_messages table
   └─ Include: email_id, event_type, timestamp, link_clicked
```

---

## PART 3: CUSTOMER SEGMENTATION & TARGETING

### Segment Definition Matrix

```
PRIMARY SEGMENTS (by lifecycle stage):

1. COLD AWARENESS
   ├─ Definition: Visited website once, no purchase
   ├─ Characteristics: First visit in last 7 days
   ├─ Size: Growing daily (target: +50-100/day)
   ├─ Behavior: Browsed 1-3 products, didn't add to cart
   ├─ Intent: Low to medium (just exploring)
   └─ Channels:
      ├─ Email: Welcome email + product education
      ├─ Meta Ads: Standard retargeting (cheap exposure)
      ├─ WhatsApp: Only if opted in (not pushed)
      └─ Google Ads: Remarketing audience

2. WARM CONSIDERATION
   ├─ Definition: Multiple touches, product interest shown
   ├─ Characteristics: Visited 2+ times, viewed 3+ products, OR added to cart
   ├─ Size: 20-30% of awareness segment
   ├─ Behavior: High engagement, reading reviews/FAQs
   ├─ Intent: Medium to high (genuinely interested)
   └─ Channels:
      ├─ Email: Browse abandonment + education + limited offers
      ├─ WhatsApp: Educational product messages + personal touch
      ├─ Meta Ads: More frequent retargeting, testimonials
      └─ Google Ads: Premium bidding on this audience

3. HOT DECISION
   ├─ Definition: Cart abandoner OR high-intent visitor
   ├─ Characteristics: Added to cart, OR visited 4+ times, OR spent 10+ min on site
   ├─ Size: 5-10% of awareness segment
   ├─ Behavior: Extreme engagement, looking at checkout
   ├─ Intent: Very high (ready to buy, needs nudge)
   └─ Channels:
      ├─ Email: Urgent cart recovery (highest frequency)
      ├─ WhatsApp: IMMEDIATE cart recovery + objection handling
      ├─ Meta Ads: Highest-bid audience, last-chance messaging
      └─ Google Ads: Search remarketing, product ads

4. CUSTOMER (Post-Purchase)
   ├─ Definition: Completed purchase
   ├─ Characteristics: order_count >= 1
   ├─ Size: 2-5% of awareness segment (conversion rate target)
   ├─ Behavior: Reviewing order, expecting delivery
   ├─ Intent: Satisfaction + retention
   └─ Channels:
      ├─ Email: Order confirmation → Shipping → Review request → Loyalty
      ├─ WhatsApp: Status updates (out for delivery) + feedback request
      ├─ Meta Ads: Upsell/cross-sell + VIP treatment
      └─ Google Ads: Remarketing to promote repeat

5. REPEAT CUSTOMER (VIP)
   ├─ Definition: 2+ purchases OR high lifetime value
   ├─ Characteristics: order_count >= 2, CLTV > ₹2000
   ├─ Size: 10-15% of all customers (target)
   ├─ Behavior: Brand loyalty, repeat purchasing
   ├─ Intent: Retention + advocacy
   └─ Channels:
      ├─ Email: Exclusive offers, loyalty program, early access
      ├─ WhatsApp: Priority support, member-only deals
      ├─ Meta Ads: VIP campaigns, referral incentives
      └─ Google Ads: Upsell audience, premium positioning

6. AT-RISK (Churn)
   ├─ Definition: Was customer, now inactive
   ├─ Characteristics: Last purchase 60+ days ago, NO recent visits
   ├─ Size: Growing if not addressed (target: < 5% of customers)
   ├─ Behavior: Declining engagement
   ├─ Intent: Win-back or churn
   └─ Channels:
      ├─ Email: Win-back campaign (special offer, "we miss you")
      ├─ WhatsApp: Personal message (if high-value customer)
      ├─ Meta Ads: Aggressive retargeting, limited-time offer
      └─ Google Ads: Remarketing, competitive positioning

SECONDARY SEGMENTS (by source):

7. GOOGLE ADS VISITOR
   ├─ Definition: Came from Google Search/Shopping ads
   ├─ Characteristics: utm_source = "google_ads"
   ├─ Intent Level: HIGH (actively searching for solution)
   ├─ Message Strategy: Direct, urgent, value-focused
   └─ Expected ROAS: 3-8:1 with retargeting

8. META ADS VISITOR
   ├─ Definition: Came from Meta/Facebook/Instagram ads
   ├─ Characteristics: utm_source = "meta"
   ├─ Intent Level: MEDIUM (interest-based, not search)
   ├─ Message Strategy: Educational, lifestyle, aspirational
   └─ Expected ROAS: 2-4:1 with retargeting

9. ORGANIC VISITOR
   ├─ Definition: Came from Google Search (no paid ads)
   ├─ Characteristics: utm_source = "organic"
   ├─ Intent Level: HIGH (searching, not pushed by ads)
   ├─ Message Strategy: Direct, solution-focused, trust-building
   └─ Expected ROAS: High (low CAC)

10. REFERRAL / WHATSAPP DIRECT
    ├─ Definition: Referred by friend, or WA catalog click
    ├─ Characteristics: utm_source = "referral" | phone_sourced
    ├─ Intent Level: HIGH (trusted recommendation)
    ├─ Message Strategy: Personal, gratitude, community-focused
    └─ Expected ROAS: Very high (strongest signal)

DYNAMIC SEGMENTS (updated real-time):

11. HIGH-INTENT (Active Now)
    ├─ Definition: Currently on website OR clicked email in last 1 hour
    ├─ Size: Variable (10-100s daily)
    ├─ Action: Immediate retargeting (WhatsApp if opted, Meta ads)
    └─ Window: 1-4 hours

12. PRICE-SENSITIVE
    ├─ Definition: Added to cart, viewed discount codes, viewed 5+ times
    ├─ Characteristics: Engagement high, conversion low (price objection)
    ├─ Strategy: Offer incentive → "Complete purchase, get ₹100 OFF"
    └─ Window: First abandoned cart only (avoid training)

13. PRODUCT-CATEGORY INTERESTED
    ├─ Definition: Viewed 3+ items in same category (spices, or brand)
    ├─ Characteristics: High specificity (e.g., "cardamom interested")
    ├─ Strategy: Send category-specific offers, recommendations
    └─ Use: Segment email sends, product recommendations
```

### Segmentation Rules Engine

```
SEGMENT ASSIGNMENT LOGIC:

Function: assign_segment(customer)
{
    // Check highest-priority segment first
    
    IF (customer.order_count >= 2) AND (customer.last_purchase_days <= 30)
        RETURN "repeat_customer_active"
    
    IF (customer.order_count >= 2) AND (customer.last_purchase_days >= 60)
        RETURN "at_risk"
    
    IF (customer.order_count >= 1) AND (customer.last_purchase_days <= 30)
        RETURN "customer_recent"
    
    IF (customer.cart_value > 0) AND (customer.last_cart_days <= 7)
        RETURN "hot_decision_cart_abandoner"
    
    IF (customer.visit_count >= 4) AND (customer.visit_pages > 10)
        RETURN "hot_decision_high_intent"
    
    IF (customer.visit_count >= 2) AND (customer.last_visit_days <= 7)
        RETURN "warm_consideration"
    
    IF (customer.visit_count == 1) AND (customer.visit_pages >= 3)
        RETURN "warm_consideration"
    
    IF (customer.visit_count == 1) AND (customer.signup_days <= 7)
        RETURN "cold_awareness"
    
    IF (customer.last_visit_days > 90) AND (customer.order_count == 0)
        RETURN "cold_abandoned"
    
    DEFAULT:
        RETURN "cold_inactive"
}

// Overlay traffic source segmentation
Segment += "_" + customer.traffic_source
// Examples: "warm_consideration_google_ads", "customer_recent_meta"
```

---

## PART 4: MESSAGE ORCHESTRATION & SEQUENCING

### Email Sequence by Segment

```
COLD AWARENESS PROSPECT (Day 0-7)
├─ Day 0, Hour 1: Welcome Email
│  ├─ Subject: "Welcome to Organic Pure Leven! 🌿"
│  ├─ Goal: Build trust, remove objections (quality, freshness, price)
│  ├─ Content: 
│  │  ├─ Who we are (small farm family, not retail chain)
│  │  ├─ Why different (direct from farm, organic, fair trade)
│  │  └─ Proof (customer reviews, certifications)
│  ├─ CTA: "Explore our collection" → link to top 3 products
│  ├─ Personalization: Name + traffic source
│  └─ Success Metric: 35%+ open rate
│
├─ Day 2: Product Education Email
│  ├─ Subject: "Why Farm-Origin Spices Make a Difference (And Cost Less)"
│  ├─ Goal: Educate on value prop, address price objections
│  ├─ Content:
│  │  ├─ How we save 30% vs. retail (no middlemen)
│  │  ├─ How you save 30% vs. others (direct sourcing)
│  │  ├─ Customer story: "I tried 5 brands before this"
│  │  └─ Freshness guarantee + return policy
│  ├─ CTA: "Get your first order" → link to best-seller
│  ├─ Personalization: If viewed specific product, recommend it
│  └─ Success Metric: 20%+ click rate
│
├─ Day 4 (If not converted): Browse Abandonment Email
│  ├─ Subject: "Missing something? Check your browsing history"
│  ├─ Goal: Remind of interest, add urgency
│  ├─ Content:
│  │  ├─ Products they viewed (max 3)
│  │  ├─ Limited-time offer: "First-time buyer: ₹150 OFF"
│  │  └─ Scarcity: "Only 20 units left of Kerala Cardamom"
│  ├─ CTA: "Complete your order" → link to viewed product
│  ├─ Fallback CTA: If no specific product, link to sale/best-seller
│  └─ Success Metric: 15%+ click rate, 2%+ conversion
│
├─ Day 6 (If still not converted): Limited Offer Email
│  ├─ Subject: "Last Chance: Your ₹150 discount expires tomorrow"
│  ├─ Goal: Create urgency, last attempt
│  ├─ Content:
│  │  ├─ Timer: "Offer expires in 22 hours"
│  │  ├─ Social proof: "500 people bought this week"
│  │  ├─ Objection handling: "Questions? Reply to this email"
│  │  └─ Reminder: Free shipping on first order
│  ├─ CTA: "Redeem your ₹150 OFF now" → link to homepage with code
│  ├─ Visual: Bright, urgent design
│  └─ Success Metric: 10%+ click rate, abandon after day 7

WARM CONSIDERATION PROSPECT (Day 1-14)
├─ Day 0 (Triggered by 2nd visit): "Welcome back! Here's what's new"
│  ├─ Subject: Personalized (e.g., "Sarah, Kerala cardamom back in stock!")
│  ├─ Goal: Personalize experience, show attentiveness
│  ├─ Content: Recommended products based on browse history
│  ├─ CTA: Browse recommendations
│  └─ Success Metric: 25%+ click rate
│
├─ Day 3 (If cart exists): Browse Abandonment Email
│  ├─ Subject: "₹350 waiting in your cart + Free Shipping inside"
│  ├─ Goal: Urgency + reassurance
│  ├─ Content:
│  │  ├─ Exact items in cart
│  │  ├─ Next-day delivery available
│  │  ├─ Money-back guarantee
│  │  └─ "Any questions? Here's what others asked..."
│  ├─ CTA: "Complete checkout" → direct to cart
│  └─ Success Metric: 20%+ click rate, 3-4% conversion
│
├─ Day 7 (If still no cart): Last-chance email
│  ├─ Subject: "50% off this weekend only"
│  ├─ Goal: Final push to action
│  ├─ Content: Biggest discount yet, high urgency
│  ├─ CTA: "Shop now" → link to homepage
│  └─ Success Metric: 12%+ click rate

HOT DECISION PROSPECT (Day 0-3, URGENT)
├─ Day 0, Hour 1: Cart Abandonment Email (IMMEDIATE)
│  ├─ Subject: "Did you mean to leave this in your cart?"
│  ├─ Goal: Urgency + reassurance
│  ├─ Content:
│  │  ├─ Items in cart (with images)
│  │  ├─ Order total
│  │  ├─ "Why hesitate?"
│  │  │  ├─ We ship next day
│  │  │  ├─ 30-day money-back guarantee
│  │  │  └─ 10,000+ happy customers
│  │  └─ Offer: "Complete now, get ₹100 OFF"
│  ├─ CTA: "Complete checkout" → direct link
│  ├─ Design: Red/urgent colors, big button
│  └─ Success Metric: 25%+ click rate, 5-8% conversion
│
├─ Day 1 (If still abandoned): Second email
│  ├─ Subject: "Your ₹100 discount expires in 23 hours"
│  ├─ Goal: Last reminder with scarcity
│  ├─ Content:
│  │  ├─ Timer widget (visual countdown)
│  │  ├─ Items still available count
│  │  └─ Social proof: "Order received 2 minutes ago from Delhi"
│  ├─ CTA: "Claim your discount" → direct link
│  └─ Success Metric: 15%+ click rate, 3-4% conversion
│
├─ Day 2 (If still abandoned): Final offer
│  ├─ Subject: "Last chance! Cart expires in 24 hours"
│  ├─ Goal: Final attempt
│  ├─ Content:
│  │  ├─ Biggest discount: "₹150 OFF (was ₹100)"
│  │  ├─ "Why you should buy today:"
│  │  │  ├─ Stock running out
│  │  │  ├─ This discount doesn't repeat
│  │  │  └─ Next-day shipping still available
│  │  └─ "Still not sure? Call/WhatsApp us"
│  ├─ CTA: "Finalize purchase" → direct link
│  └─ Success Metric: 10%+ click rate, 2-3% conversion
│
├─ Day 3 (If still abandoned): Remove from active sequences
│  └─ Move to "Cold Abandoned" segment, retry in 30 days

CUSTOMER (Post-Purchase, Day 0-7)
├─ Day 0, Minute 5: Order Confirmation Email
│  ├─ Subject: "Order #PL-2026-001 confirmed! 🎉"
│  ├─ Goal: Excitement, next steps
│  ├─ Content:
│  │  ├─ Order details (items, total, payment method)
│  │  ├─ What happens next (1-day prep, 1-day delivery)
│  │  ├─ Tracking: "Updates will be emailed to you"
│  │  └─ Support: "Questions? Reply here or WhatsApp"
│  ├─ CTA: "Track your order" → link to status page
│  └─ Success Metric: 60%+ open rate
│
├─ Day 1: Shipping Notification Email
│  ├─ Subject: "Your order is on the way! 📦"
│  ├─ Goal: Anticipation, transparency
│  ├─ Content:
│  │  ├─ Shipped timestamp
│  │  ├─ Tracking link (Shiprocket)
│  │  ├─ ETA: "Arrives by May 20"
│  │  ├─ "How to prepare:" Instructions for items
│  │  └─ "Help needed? We're here"
│  ├─ CTA: "Track in real-time" → Shiprocket link
│  └─ Success Metric: 55%+ open rate
│
├─ Day 2-3: Out for Delivery Notification
│  ├─ Subject: "Your order arrives today! 🚚"
│  ├─ Goal: Preparation, excitement
│  ├─ Content:
│  │  ├─ "Your order will arrive between 10 AM - 6 PM"
│  │  ├─ Items included (list)
│  │  ├─ "Tips for receiving:" Sign, inspect, store
│  │  └─ "Not home? Delivery person can leave at safe place"
│  ├─ CTA: "View order details" → order page
│  └─ Success Metric: 50%+ open rate
│
├─ Day 3-4: Delivery Confirmation + Thank You
│  ├─ Subject: "Thanks for ordering! How was your experience?"
│  ├─ Goal: Gratitude, feedback request
│  ├─ Content:
│  │  ├─ "We hope you love it!"
│  │  ├─ "Your feedback helps us improve"
│  │  ├─ Quick survey (2 questions, 10 seconds)
│  │  └─ "Problems? We'll fix it immediately"
│  ├─ CTA: "Leave a review" → review page
│  └─ Success Metric: 40%+ open rate, 5% review rate

REPEAT CUSTOMER (VIP, Day 7-30)
├─ Day 7: Review Request Email
│  ├─ Subject: "How was your first experience? (₹100 credit inside)"
│  ├─ Goal: Reviews for social proof
│  ├─ Content:
│  │  ├─ "Your honest review helps other food lovers"
│  │  ├─ Incentive: "Leave a review, get ₹100 credit for next order"
│  │  ├─ Social proof: "Real reviews from real customers"
│  │  └─ Easy: "Click button, write 2 sentences"
│  ├─ CTA: "Write your review" → review page
│  └─ Success Metric: 30%+ open, 8-10% review rate
│
├─ Day 14: Cross-sell Email
│  ├─ Subject: "Customers who loved [product] also got [other product]"
│  ├─ Goal: Second purchase, upsell
│  ├─ Content:
│  │  ├─ "Based on your order of Kerala Cardamom:"
│  │  ├─ Recommended products (complementary)
│  │  ├─ "Save 20% when you buy a bundle"
│  │  └─ Social proof: "Bought together 500 times"
│  ├─ CTA: "See complementary products" → product page
│  └─ Success Metric: 20%+ click, 3-4% second purchase
│
├─ Day 30: Replenishment Email
│  ├─ Subject: "Time to restock your [product]? Fresh batch just arrived"
│  ├─ Goal: Repeat purchase, LTV
│  ├─ Content:
│  │  ├─ "You bought Kerala Cardamom 30 days ago"
│  │  ├─ "New harvest just arrived, better than first batch"
│  │  ├─ VIP perk: "Get 15% OFF as loyal customer"
│  │  └─ Scarcity: "Harvest limited, 100 units"
│  ├─ CTA: "Restock now" → product page
│  └─ Success Metric: 25%+ click, 5-8% second purchase
│
├─ Day 60 (If no activity): Win-back Email
│  ├─ Subject: "We miss you! ₹200 OFF your next order"
│  ├─ Goal: Prevent churn, reactivate
│  ├─ Content:
│  │  ├─ "It's been 60 days since your order"
│  │  ├─ "Come back and try 3 new products"
│  │  ├─ "Special offer: ₹200 OFF + free shipping"
│  │  └─ "Any issues? We'll make it right"
│  ├─ CTA: "Claim your ₹200 discount" → homepage with code
│  └─ Success Metric: 20%+ click, 4-6% win-back rate
```

### WhatsApp Sequence by Segment

```
RULES FOR WHATSAPP TIMING:
├─ Only send if opted in (don't assume consent)
├─ Max 2 messages per week per user
├─ Best times: 10 AM, 2 PM, 7 PM (avoid early morning/late night)
├─ No messages on Sunday (avoid weekend noise)
└─ Always include opt-out option

WARM PROSPECT (Day 1-7, After Email)
├─ Day 1, 2 PM: Product Education Message
│  ├─ Template: Educational
│  ├─ Content: "Hi [Name]! 👋"
│  │  "Welcome to Organic Pure Leven! Here's why customers love us:"
│  │  "✅ Farm-to-you in 48 hours (freshness guaranteed)"
│  │  "✅ 30% cheaper than retail"
│  │  "✅ 10,000+ happy customers"
│  │  
│  │  "Curious? Here's your first-time discount: 15% OFF
│  │  Use code: WELCOME15"
│  │  
│  │  "https://pureleven.com/?code=WELCOME15"
│  ├─ Success Metric: 15%+ click rate on link
│  └─ Fallback: If no click in 24h, add offer in email
│
├─ Day 4 (If no conversion): Testimonial Message
│  ├─ Template: Customer story
│  ├─ Content: "Hi [Name]! 👋"
│  │  "Real customer, real story:"
│  │  
│  │  "⭐⭐⭐⭐⭐ Anil from Delhi:"
│  │  '"I\'ve tried 5 brands of cardamom. Yours is THE BEST.'
│  │  'Aroma is insane. Worth every rupee."'
│  │  
│  │  "Try it risk-free: 30-day money-back guarantee 💯
│  │  https://pureleven.com/?code=WELCOME15"
│  ├─ Success Metric: 12%+ click rate
│  └─ Fallback: If no response, stop sequence (move to cold)

HOT PROSPECT (Day 0-1, Cart Abandoned - URGENT)
├─ Day 0, 4 PM (IMMEDIATE): Cart Recovery Message
│  ├─ Template: Urgent, personal
│  ├─ Content: "Hi [Name]! 👋"
│  │  "Saw you left ₹350 in your cart 😢"
│  │  
│  │  "Order now and get:"
│  │  "✅ ₹100 OFF (₹250 total)"
│  │  "✅ Free shipping"
│  │  "✅ Next-day delivery"
│  │  "✅ 30-day guarantee"
│  │  
│  │  "Complete order now:
│  │  https://pureleven.com/checkout?cart=[id]&code=CART100"
│  ├─ Follow-up: After 2h, if no click, send reminder
│  ├─ Success Metric: 20%+ click rate, 5-8% conversion
│  └─ Tone: Helpful, not pushy
│
├─ Day 1, 10 AM (If still abandoned): Urgency Message
│  ├─ Template: Scarcity + reassurance
│  ├─ Content: "Hi [Name]! 👋"
│  │  "Your ₹100 discount expires in 20 hours ⏰"
│  │  
│  │  "Last chance to save on:"
│  │  "• Kerala Cardamom 50g"
│  │  "• Kerala Black Pepper 100g"
│  │  
│  │  "Stock running low | Only 15 units left"
│  │  
│  │  "Any questions? I'm here to help!
│  │  Reply to this message or call +91-9999-999-999"
│  │  
│  │  "https://pureleven.com/checkout?cart=[id]&code=CART100"
│  ├─ Success Metric: 15%+ click rate, 3-4% conversion
│  └─ Personalization: Offer live support option

CUSTOMER (Post-Purchase, Day 1-3)
├─ Day 1, 10 AM: Order Shipped Notification
│  ├─ Template: Status update
│  ├─ Content: "Hi [Name]! 📦"
│  │  "Good news! Your order #PL-2026-001 shipped!"
│  │  
│  │  "📍 Status: Out for Delivery"
│  │  "🚚 ETA: Tomorrow (May 20) | 10 AM - 6 PM"
│  │  "📦 Items: Kerala Cardamom 50g x1"
│  │  
│  │  "Track in real-time:
│  │  https://shiprocket.in/track/[tracking_id]"
│  ├─ Success Metric: 80%+ open rate (status update)
│  └─ Shiprocket trigger: Automated from webhook
│
├─ Day 2, 8 AM: Out for Delivery Message
│  ├─ Template: Preparation
│  ├─ Content: "Hi [Name]! 🚴"
│  │  "Your order arrives TODAY! ☀️"
│  │  
│  │  "⏰ Delivery window: 10 AM - 6 PM"
│  │  "📍 Delivered to: [address]"
│  │  
│  │  "Tips for receiving:"
│  │  "✅ Keep someone home or arrange access"
│  │  "✅ Check items before accepting"
│  │  "✅ Store in cool, dry place"
│  │  
│  │  "Questions? Reply here or call +91-9999-999-999"
│  ├─ Success Metric: 70%+ open rate
│  └─ Shiprocket trigger: Automated from webhook
│
├─ Day 3, 2 PM: Feedback Request Message
│  ├─ Template: Review request
│  ├─ Content: "Hi [Name]! 🌿"
│  │  "Order delivered! How do you like it?"
│  │  
│  │  "Help us improve by sharing your feedback:"
│  │  "https://pureleven.com/reviews/PL-2026-001"
│  │  
│  │  "THANK YOU + ₹100 BONUS:
│  │  Leave a review, get ₹100 credit for next order! 🎁"
│  │  
│  │  "Problems? We'll fix immediately.
│  │  https://wa.me/91-9999-999-999"
│  ├─ Success Metric: 50%+ open, 8-10% review rate
│  └─ Incentive: ₹100 credit for review

REPEAT CUSTOMER (VIP, Day 30)
├─ Day 30: Replenishment Reminder
│  ├─ Template: Friendly check-in
│  ├─ Content: "Hi [Name]! 🎁"
│  │  "Time to restock? Fresh harvest just arrived!"
│  │  
│  │  "You ordered Kerala Cardamom 30 days ago"
│  │  "New batch = Better aroma + Better price"
│  │  
│  │  "VIP Offer (Loyalty):"
│  │  "🌿 20% OFF on cardamom"
│  │  "🚚 Free shipping"
│  │  "📦 Limited to 100 units"
│  │  
│  │  "Restock now:
│  │  https://pureleven.com/?code=VIP20&tracking=repeat"
│  ├─ Success Metric: 25%+ click rate, 5-8% repurchase
│  └─ Personalization: Use past product purchase

AT-RISK / CHURN (Day 60+, If inactive)
├─ Day 60: Win-back Message (VIP only)
│  ├─ Template: Personal, warm
│  ├─ Content: "Hi [Name]! 🌿"
│  │  "We miss you! It's been 60 days..."
│  │  
│  │  "Come back to us! Here's a special offer:"
│  │  
│  │  "🎁 ₹200 OFF your next order"
│  │  "🚚 Free shipping (all items)"
│  │  "⏰ Valid for 7 days only"
│  │  
│  │  "Bring back the love:
│  │  https://pureleven.com/?code=COMEBACK200"
│  │  
│  │  "Anything wrong? Let's talk:
│  │  https://wa.me/91-9999-999-999"
│  ├─ Success Metric: 20%+ click rate, 4-6% reactivation
│  └─ Tone: Personal, genuinely caring
```

### Meta Ads Sequence by Segment

```
META ADS TARGETING STRATEGY:

AWARENESS STAGE (Cold Visitor)
├─ Audience: Website visitors (last 30 days)
├─ Campaign: Brand Awareness + Education
├─ Ad Types:
│  ├─ Carousel ads (4-5 products, swipeable)
│  ├─ Video ads (30s: "How are we different?")
│  ├─ Collection ads (tap to explore products)
│  └─ Reels ads (lifestyle, customer stories)
├─ Budget: ₹50-100/day
├─ Frequency: 1-3 times/week per user
├─ Creative Messaging:
│  ├─ "Farm-to-you in 48 hours"
│  ├─ "Organic, Direct, ₹3 cheaper than retail"
│  ├─ "Not your grocery store spices"
│  └─ "10,000+ people switched from [competitor]"
├─ CTA: "Learn More" or "Browse Now"
└─ Expected Metrics:
   ├─ CTR: 1-2%
   ├─ Cost per click: ₹5-10
   └─ Conversion rate: 0.5-1%

CONSIDERATION STAGE (2nd+ Visit)
├─ Audience: Website visitors + product viewers (no purchase)
├─ Campaign: Education + Value Prop
├─ Ad Types:
│  ├─ Testimonial videos (customer stories, 20s)
│  ├─ Before/After ads (regular vs. pure spices)
│  ├─ FAQ carousel (top objections)
│  └─ Value prop video (why cheaper, why better)
├─ Budget: ₹100-150/day
├─ Frequency: 2-4 times/week per user
├─ Creative Messaging:
│  ├─ "Why we're 30% cheaper than retail"
│  ├─ "What customers love about us" (reviews)
│  ├─ "Freshness guaranteed or money back"
│  └─ "Free shipping on first order"
├─ CTA: "Get First-Time Discount" or "See Testimonials"
└─ Expected Metrics:
   ├─ CTR: 2-3%
   ├─ Cost per click: ₹4-8
   └─ Conversion rate: 1-2%

DECISION STAGE (Cart Abandoner)
├─ Audience: Cart abandoners (last 3 days)
├─ Campaign: Urgency + Incentive + Reassurance
├─ Ad Types:
│  ├─ Dynamic product ads (items in their cart!)
│  ├─ Carousel of product images
│  ├─ Video ad: "Last chance, limited time offer"
│  └─ Collection: "Complete your order"
├─ Budget: ₹200-300/day (HIGH priority)
├─ Frequency: Daily (up to 3 ads/day for 3 days)
├─ Creative Messaging:
│  ├─ "Your order is waiting: ₹350"
│  ├─ "₹100 OFF to complete your order (expires tomorrow)"
│  ├─ "Free shipping + next-day delivery"
│  ├─ "30-day money-back guarantee"
│  └─ "Join 10,000+ happy customers"
├─ CTA: "Claim your discount" (direct to cart)
├─ Visual: Bright colors, urgency, countdown timer
└─ Expected Metrics:
   ├─ CTR: 3-5%
   ├─ Cost per click: ₹3-6
   └─ Conversion rate: 5-8%

POST-PURCHASE (Customer - Loyalty)
├─ Audience: Converters (30 days)
├─ Campaign: Upsell + Cross-sell + Loyalty
├─ Ad Types:
│  ├─ Carousel: "Customers who bought X also got Y"
│  ├─ Product ads: Complementary items
│  ├─ Video: "Real customers, real stories"
│  └─ Collection: VIP member exclusive deals
├─ Budget: ₹100-150/day
├─ Frequency: 1-2 times/week
├─ Creative Messaging:
│  ├─ "You loved [product]. Try [complement]"
│  ├─ "VIP members save 20% on everything"
│  ├─ "Exclusive: Limited edition spice blends"
│  └─ "Refer a friend, both get ₹100 OFF"
├─ CTA: "Shop Complementary Products" or "Join VIP"
└─ Expected Metrics:
   ├─ CTR: 2-3%
   ├─ Cost per click: ₹4-7
   └─ Conversion rate: 2-4% (higher LTV)

RETENTION (At-Risk / Churn, 60+ days inactive)
├─ Audience: Converters not active in 60 days
├─ Campaign: Win-back
├─ Ad Types:
│  ├─ Video: "We miss you" emotional appeal
│  ├─ Carousel: "New products since you left"
│  ├─ Bold discount ad: "₹200 OFF to come back"
│  └─ Testimonial: "Why people came back"
├─ Budget: ₹150-200/day
├─ Frequency: 2-3 times/week
├─ Creative Messaging:
│  ├─ "We miss you! Come back for ₹200 OFF"
│  ├─ "New harvests, better quality, same love"
│  ├─ "The products you loved are fresher now"
│  └─ "Refer friends + get rewards"
├─ CTA: "Redeem your ₹200 discount"
└─ Expected Metrics:
   ├─ CTR: 2-4%
   ├─ Cost per click: ₹5-10
   └─ Conversion rate: 3-6% (win-back success)

LOOKALIKE AUDIENCES
├─ Base: Converters (past 30 days)
├─ Type: 1-5% lookalike (most similar)
├─ Campaign: Acquisition (like converters)
├─ Budget: ₹500-1000/day (high spend, high scale)
├─ Expected Metrics:
│  ├─ Cost per purchase: ₹1500-2000
│  └─ ROI: 3-5:1
└─ Refresh: Weekly from new converters
```

---

## PART 5: TECHNICAL IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-2)
**Goal:** Build the unified data layer & tracking infrastructure

**Tasks:**
1. **CRM Database Enhancements**
   - ✅ customers table (exists)
   - ✅ crm_events table (exists)
   - ADD: crm_journeys table (customer path across channels)
   - ADD: crm_audiences table (segment definitions + sync targets)
   - ADD: crm_message_logs table (detailed message tracking)
   - ADD: segments table (dynamic segment assignments)

2. **Tracking Implementation**
   - Email: ✅ (already done)
   - Website: Enhance GA4 events (product_view, add_to_cart, etc.)
   - WhatsApp: Add Wabis webhook for click/read events
   - Meta: Add pixel events (ViewContent, AddToCart, Purchase) beyond current
   - Google Ads: Add remarketing list upload capability

3. **Segmentation Engine**
   - Build segment_assignment() function in crm_routes.py
   - Create daily job that assigns all customers to segments
   - Build segment sync to Meta, Google, Wabis

4. **Deliverables:**
   - Database migrations: 4 new tables
   - API endpoints: /api/crm/segments, /api/crm/journeys
   - Job scheduler: segment_assignment_job (runs daily 2 AM)
   - Documentation: Data flow diagram, segment definitions

---

### Phase 2: Channel Integration (Weeks 3-5)
**Goal:** Connect all channels to the orchestration engine

**Tasks:**

1. **Email Orchestration (Already partially done)**
   - ✅ Email templates exist
   - ADD: Trigger-based sending (on segment entry)
   - ADD: A/B testing framework (subject lines, send times)
   - ADD: Unsubscribe & preference management

2. **WhatsApp Integration (Wabis)**
   - Setup: Wabis API token ✅ (have it)
   - ADD: Webhook receiver for click events, read events
   - ADD: Message templates in Wabis dashboard
   - ADD: Template-based message sending (queue + scheduler)
   - ADD: Opt-in/opt-out management
   - ADD: Per-user frequency capping (max 2/week)

3. **Meta Ads Integration**
   - CAPI setup: ✅ (pixel ID, access token exist)
   - ADD: Server-side conversion tracking (purchase events)
   - ADD: Customer list sync (email + phone, hashed)
   - ADD: Nightly audience sync job
   - ADD: Monitor API rate limits, errors

4. **Google Ads Integration**
   - Offline conversions: ✅ (setup done)
   - ADD: Remarketing list upload (nightly)
   - ADD: Customer match list upload (hashed emails)
   - ADD: Monitor API rate limits, errors

5. **GA4 Integration**
   - ✅ Already firing events
   - ADD: Enhanced ecommerce events (product_id, category, etc.)
   - ADD: User ID tracking (after login/purchase)

6. **Deliverables:**
   - API endpoints: /api/crm/messages/send (router for all channels)
   - Webhooks: Wabis click/read events, Shiprocket status
   - Jobs: Customer list sync (nightly to Meta, Google)
   - Message templates: 8 WhatsApp templates in Wabis
   - Documentation: Integration checklist for each channel

---

### Phase 3: Orchestration & Workflows (Weeks 6-8)
**Goal:** Automate customer journeys across channels

**Tasks:**

1. **Journey Automation**
   - Cold → Warm → Customer flows
   - Rule-based triggers (segment entry, days elapsed, behavior)
   - Multi-channel sequencing (email → WhatsApp → Meta in order)

2. **Segment-Based Triggers**
   - When customer enters "warm_consideration" segment:
     - Send welcome email (Day 0)
     - Queue WhatsApp message (Day 1)
     - Create Meta audience for retargeting (Day 0)
   - When customer enters "hot_decision" segment:
     - Send urgent cart recovery email (Hour 1)
     - Send WhatsApp cart recovery (2 hours)
     - Increase Meta ad frequency
   - When customer converts:
     - Send confirmation email (immediate)
     - Send to Meta CAPI for lookalike audience
     - Send to Google Ads for conversion tracking
     - Move to "customer" segment, trigger next sequence

3. **Frequency & Channel Prioritization**
   - Rules:
     - Don't send same message via two channels in 4 hours
     - Max 2 WhatsApp per week
     - Max 1 email per day
     - Prefer WhatsApp for high-intent (hot_decision)
     - Prefer email for education (warm_consideration)

4. **Deliverables:**
   - Journey engine: crm_journey_runner() job
   - Trigger framework: register_trigger(segment, event, action)
   - Scheduling: APScheduler or similar
   - Monitoring: Dashboard of active journeys, drop-off rates

---

### Phase 4: Platforms Sync & Lists (Weeks 9-10)
**Goal:** Keep audiences in sync across platforms

**Tasks:**

1. **Nightly Audience Sync**
   - Export segments from CRM:
     - All Google Ads visitors → Google Ads remarketing list
     - All Meta visitors → Meta website audience
     - Converters → Meta lookalike seed audience
     - VIP customers (2+ purchases) → Meta VIP audience
     - At-risk (60+ days inactive) → Meta win-back audience

2. **Format Conversions**
   - Email hashing (SHA256 for Meta/Google)
   - Phone number hashing (for Meta customer match)
   - CSV formatting (one email per line)
   - Chunking (avoid API limits)

3. **Error Handling**
   - Retry failed uploads (exponential backoff)
   - Log all sync operations
   - Alert on failures

4. **Deliverables:**
   - Job: audience_sync_job (nightly 2 AM)
   - Status page: Shows last sync time per platform
   - Error logs: Detailed troubleshooting

---

### Phase 5: Testing & Optimization (Weeks 11-12)
**Goal:** Verify, measure, and optimize the entire system

**Tasks:**

1. **End-to-End Testing**
   - Test cold visitor journey:
     - Create test visitor → Assign to cold_awareness segment
     - Verify email sent → Click link → Verify GA4 event
     - Verify customer added to Meta audience
   - Test cart abandonment:
     - Add to cart → Verify email → Verify WhatsApp → Verify Meta ads show
   - Test purchase:
     - Complete purchase → Verify emails → Verify CAPI → Verify Google Ads

2. **Metrics & Dashboards**
   - Setup dashboards:
     - Funnel: Awareness → Consideration → Decision → Purchase → Loyalty
     - Channel metrics: Email (open, click, convert), WhatsApp (click, read), Meta (CTR, ROAS), etc.
     - Attribution: Which channel drove the conversion?
     - Segment health: Size, conversion rate, engagement rate per segment
   - Track KPIs:
     - Email open rate (target: 30-45%)
     - WhatsApp click rate (target: 15-25%)
     - Meta ROAS (target: 3-5:1)
     - Cold → Customer conversion rate (target: 2-4%)
     - Customer lifetime value (target: ₹2,000+)

3. **A/B Tests**
   - Email: Subject line variants (urgency vs. value)
   - Email: Send time optimization (morning vs. evening)
   - WhatsApp: Message length (short vs. detailed)
   - Meta: Creative variants (video vs. carousel vs. static)

4. **Deliverables:**
   - Analytics dashboard (Google Data Studio or similar)
   - A/B testing framework
   - Weekly performance reports
   - Optimization recommendations doc

---

## PART 6: SUCCESS METRICS & KPIs

### Funnel-Level Metrics

```
AWARENESS STAGE
├─ Website visitors/day: Current ?, Target 200+
├─ Unique email captures: Current ?, Target 50-100/day
├─ GA4 event tracking: Verified ✅
└─ Expected segment size: 500-1000 cold prospects

CONSIDERATION STAGE
├─ Email open rate: Target 30-45%
├─ Email click rate: Target 15-25%
├─ WhatsApp click rate: Target 15-25%
├─ Meta click-through rate: Target 1-2%
└─ Warm prospect size: Target 20-30% of cold

DECISION STAGE
├─ Cart abandonment rate: Current ?, Target < 40%
├─ Cart recovery email click: Target 20%+
├─ Cart recovery conversion: Target 5-8%
├─ Hot prospect size: Target 5-10% of cold
└─ Average cart value: Target ₹400+

PURCHASE STAGE
├─ Cold → Customer conversion: Target 2-4%
├─ Average order value: Target ₹500+
├─ First-time buyer CAC: Target < ₹500
└─ Customer segment size: Target 2-5% of cold

LOYALTY STAGE
├─ Repeat purchase rate: Target 20%+ (within 60 days)
├─ Customer lifetime value: Target ₹2,000+
├─ Review rate: Target 5-10%
├─ Churn rate: Target < 20% (at 90 days)
└─ VIP customer rate: Target 10-15% of customers
```

### Channel-Specific Metrics

```
EMAIL METRICS
├─ Delivery rate: Target > 99%
├─ Open rate: Target 30-45%
├─ Click rate: Target 15-25%
├─ Unsubscribe rate: Target < 0.5%
├─ Conversion rate: Target 1-3%
└─ Cost: ₹0.20 per send (via Plunk)

WHATSAPP METRICS
├─ Delivery rate: Target > 95%
├─ Read rate: Target 80-90%
├─ Click rate: Target 15-25%
├─ Reply rate: Target 5-10%
├─ Opt-out rate: Target < 2%
└─ Cost: ₹0.50 per message (via Wabis)

META ADS METRICS
├─ Click-through rate: Target 1-3%
├─ Cost per click: Target ₹3-10
├─ Cost per purchase: Target ₹1,500-2,000
├─ ROAS (return on ad spend): Target 3-5:1
├─ Frequency: 1-3 ads per user per week
└─ Monthly budget: Target ₹10,000-15,000

GOOGLE ADS METRICS
├─ Conversion rate: Target 1-3%
├─ Cost per conversion: Target ₹1,500-2,500
├─ ROAS: Target 2-4:1
├─ Remarketing list size: Target 500-1000
└─ Monthly budget: Target ₹5,000-10,000

GA4 METRICS
├─ Sessions: Target 1000+/day
├─ Users: Target 500+/day
├─ Bounce rate: Target < 40%
├─ Avg. session duration: Target 2-3 min
├─ Conversion rate: Target 2-4%
└─ Goal completion rate: Purchase = 2-4%
```

### Business Metrics

```
GROWTH METRICS
├─ Monthly revenue: Target ₹500,000+ (from email + WhatsApp + ads)
├─ Customer acquisition cost: Target < ₹500
├─ Customer lifetime value: Target ₹2,000+
├─ LTV:CAC ratio: Target > 4:1
├─ Monthly active customers: Target 100+
└─ Customer growth rate: Target 10-20%/month

RETENTION METRICS
├─ Repeat purchase rate: Target 20%+
├─ Churn rate (90 days): Target < 20%
├─ VIP conversion rate: Target 10-15%
├─ Referral rate: Target 5-10% of customers
└─ Net promoter score: Target 40+

PROFITABILITY METRICS
├─ Average order value: Target ₹500+
├─ Gross margin: Target 60-70%
├─ Marketing spend/revenue: Target 20-25%
├─ CAC payback period: Target < 90 days
└─ ROAS across all channels: Target 3-4:1
```

---

## PART 7: IMPLEMENTATION TIMELINE

### Week 1-2: Foundation
- [ ] Database migrations (4 new tables)
- [ ] Segment assignment engine
- [ ] Testing frameworks

### Week 3-5: Integration
- [ ] WhatsApp templates + webhooks
- [ ] Meta audience sync
- [ ] Google Ads list upload
- [ ] Enhanced GA4 tracking

### Week 6-8: Orchestration
- [ ] Journey automation engine
- [ ] Trigger framework
- [ ] Frequency capping
- [ ] Monitoring dashboard

### Week 9-10: List Sync
- [ ] Nightly audience sync jobs
- [ ] Hash/encrypt functions
- [ ] Error handling & retries

### Week 11-12: Testing & Optimization
- [ ] End-to-end testing
- [ ] Performance dashboards
- [ ] A/B testing framework
- [ ] Documentation

---

## PART 8: CRITICAL SUCCESS FACTORS

1. **Data Quality** — Every customer must have email (required) + phone (optional)
2. **Consent** — Must have opt-in before WhatsApp/SMS messaging
3. **Frequency Capping** — Don't overwhelm users (max 2 WhatsApp/week)
4. **Attribution** — Track which channel drove the conversion (multi-touch)
5. **Timing** — Right message at right time (urgency for hot, education for warm)
6. **Personalization** — Use past behavior (products viewed, purchase history)
7. **Testing** — Always A/B test creative, timing, messaging
8. **Compliance** — GDPR (if EU users), CAN-SPAM (emails), WhatsApp ToS

---

## PART 9: QUICK START CHECKLIST

**Week 1 (This Week)**
- [ ] Review this document, share with team
- [ ] Identify missing data (phone numbers for customers)
- [ ] Start DB migrations (segments table, journeys table)
- [ ] Plan WhatsApp message templates (decide 8 templates)

**Week 2**
- [ ] Segment assignment engine (code)
- [ ] Segment sync job (daily 2 AM)
- [ ] WhatsApp webhook receiver

**Week 3**
- [ ] Meta audience sync (nightly)
- [ ] Google Ads list upload (nightly)
- [ ] Email trigger automation (on segment entry)

**Week 4**
- [ ] WhatsApp message sending (Wabis integration)
- [ ] Test cold → warm journey (end-to-end)
- [ ] Monitor metrics (dashboards)

**Week 5+**
- [ ] Optimize based on metrics
- [ ] Expand to more campaigns
- [ ] Increase budgets on high-ROAS channels

---

## NEXT STEPS: What to Build First

1. **Database Foundation** (1-2 days)
   - Create segments, journeys, message_logs tables
   - Build segment_assignment() logic

2. **Segment Sync** (2-3 days)
   - Write nightly jobs for Meta, Google, Wabis
   - Test with small audience first

3. **WhatsApp Integration** (3-4 days)
   - Add webhook receiver
   - Create 8 message templates
   - Test sending

4. **End-to-End Testing** (1-2 days)
   - Simulate cold visitor → customer journey
   - Verify all events logged correctly
   - Verify all messages sent

5. **Metrics Dashboard** (2-3 days)
   - Setup Google Data Studio or similar
   - Query key metrics from CRM
   - Track weekly trends

---

**This is your roadmap. It's ambitious but achievable in 12 weeks. The key is to start with Phase 1 (data layer) before building automations. Once the data is clean and flowing, everything else becomes easier.**

**Ready to start?**
