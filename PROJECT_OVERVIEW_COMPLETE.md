# 🌿 PURE LEVEN PROJECT — Complete Overview

**Project Workspace**: `/Users/bthomas/Documents/pureleven_dev`  
**Status**: 🟢 **PRODUCTION ACTIVE** (Multiple systems live)  
**Last Updated**: June 2, 2026

---

## 📍 WHAT IS PURE LEVEN?

**Pure Leven** is a **premium organic spices e-commerce platform** based in Kerala, India.

### Brand Essence
- **Category**: Organic Foods & Wellness
- **Core Offering**: Authentic, traceable Kerala-origin spices
- **Values**: Natural, trustworthy, educational, family-friendly, fresh
- **Design Direction**: Modern Kerala luxury commerce (calm, warm, premium)
- **Market**: India-focused (Hindi/English), growing international

### Core Products
- Premium spices (cardamom, cinnamon, turmeric, clove, pepper, etc.)
- Wellness products
- Organic pantry items
- Direct-from-farmer products

### Where to Visit
- **Shopify Store**: https://pureleven.com
- **Analytics Dashboard**: https://ai.pureleven.com (Customer CRM)
- **Conversation Audit**: https://track.pureleven.com/api/admin

---

## 🏗️ SYSTEM ARCHITECTURE

Pure Leven runs on a **comprehensive omnichannel growth platform** with 4 major systems:

### 1️⃣ **SHOPIFY STOREFRONT** (ecommerce core)
- **Domain**: pureleven.com
- **Platform**: Shopify (custom theme development)
- **Focus**: Product catalog, checkout, customer experience
- **Tracking**: GA4, Meta Pixel, server-side conversion tracking
- **Tech**: Liquid templates, custom CSS/JS, API integrations

**Current Work**: 
- Theme migration to new premium Kerala design system
- Checkout optimization (fixed footer CTA, trust signals)
- Product page enhancements
- Mobile-first responsive design

---

### 2️⃣ **WHATSAPP MESSAGING SYSTEM (WABIS)** 
- **Platform**: Wabis (WhatsApp Business API provider)
- **Purpose**: Customer communication, order tracking, promotional flows
- **Language Support**: English, Hindi, Malayalam
- **Integration Type**: Webhooks + REST API

**Capabilities**:
- ✅ Incoming message handling
- ✅ Bot flows (language selection, product menus, order tracking)
- ✅ Template messages (marketing, transactional)
- ✅ AI-powered responses (currently DISABLED for testing)
- ✅ Conversation replay and audit trail
- ✅ Customer segments and journeys

**Current Work** (LATEST - What We Just Deployed):
- ✅ **Flow Validation System** - Fix "Cardamom routing bug"
  - Fuzzy matching for flow options
  - Product intent detection (20+ keywords)
  - Flow abandonment tracking
  
- ✅ **Conversation Audit System** - Complete visibility
  - Real-time message logging
  - Intent detection and routing decision recording
  - WhatsApp-style conversation replay
  - Automated daily reports
  - Knowledge gap capture
  
- ✅ **AI Response Disabling** - Testing phase
  - AI generates responses and logs them
  - NOT sent to WhatsApp (testing only)
  - Database captures all activity for analysis

**WABIS Infrastructure**:
```
VPS: 192.46.213.140 (pureleven-growth)
├── Docker: pureleven-ai-engine (FastAPI)
├── Database: SQLite at /app/data/anu_login.sqlite3
├── Service: FastAPI on 0.0.0.0:8000
├── Proxy: Nginx → track.pureleven.com/api/
└── Monitoring: Docker logs + daily reports at midnight UTC
```

---

### 3️⃣ **CUSTOMER INTELLIGENCE PLATFORM (CRM)**
- **Purpose**: Unified customer data, attribution, audience building
- **Domain**: ai.pureleven.com
- **Database**: PostgreSQL (6 tables, fully indexed)
- **Stack**: FastAPI (Python), PostgreSQL, Nginx

**What It Does**:
- ✅ Captures customer data from Shopify webhooks
- ✅ Tracks behavior from GA4 events
- ✅ Imports conversions from Google Ads & Meta Ads
- ✅ Provides real-time customer analytics dashboard
- ✅ Enables audience segmentation and targeting
- ✅ Unifies data across multiple sources

**API Endpoints**:
```
GET /api/crm/customers         (list all customers)
GET /api/crm/customers/{id}    (single customer detail)
POST /api/crm/identify         (identify visitor/customer)
POST /api/crm/events/*         (capture GA4, Ads events)
POST /api/crm/webhooks/shopify (Shopify order webhook)
```

**Data Tables**:
- `customers` — unified customer profiles
- `orders` — transaction data (COD, prepaid)
- `events` — behavioral events (page view, product view, add-to-cart, checkout)
- `segments` — audience segments for retargeting
- `conversions` — tracked conversions from Google Ads, Meta Ads
- `performance` — campaign and channel performance

---

### 4️⃣ **PAID MEDIA & RETARGETING SYSTEM**
- **Platforms**: Google Ads, Meta (Facebook/Instagram)
- **Account**: Pure Leven Exim (Facebook ad account: 237007475595482)
- **Strategy**: Multi-channel attribution and retargeting

**Capabilities**:
- ✅ Server-side conversion tracking (Google Ads, Meta CAPI)
- ✅ Audience synchronization
- ✅ Campaign performance monitoring
- ✅ Retargeting campaigns
- ✅ ROI tracking across channels

**Current Work**:
- Meta Ads: Unified audience strategy
- Google Ads: Campaign optimization, negative keyword management
- Attribution: Multi-touch attribution model
- Reporting: Daily performance dashboard

---

### 5️⃣ **EMAIL & MARKETING AUTOMATION** (Plunk/Sendgrid)
- **Purpose**: Email campaigns, lifecycle marketing, transactional emails
- **Platforms**: Plunk (self-hosted), Sendgrid
- **Integration**: N8N workflows (automation orchestration)

**Workflows**:
- ✅ Order confirmation emails
- ✅ Cart recovery email sequences
- ✅ Win-back campaigns
- ✅ Lifecycle marketing (email + WhatsApp)
- ✅ Abandoned checkout recovery

---

## 📁 PROJECT FILES STRUCTURE

```
pureleven_dev/
├── anu-login/                           # Main AI/messaging backend
│   └── backend/
│       ├── app/
│       │   ├── ai/                      # AI routing & intent detection
│       │   │   ├── intent_router.py     # Message routing logic
│       │   │   ├── wabis_reply_generator.py
│       │   │   ├── audit_logger.py      # Conversation logging
│       │   │   ├── flow_helpers.py      # Flow validation
│       │   │   ├── routing_error_detector.py
│       │   │   └── daily_report_generator.py
│       │   ├── routes/
│       │   │   ├── wave02_wabis_routes.py  # WhatsApp webhook handler
│       │   │   ├── conversation_replay_routes.py  # Audit UI
│       │   │   ├── crm_routes.py        # Customer data routes
│       │   │   └── main.py              # FastAPI app
│       │   ├── storage.py               # Database schema
│       │   └── ai/conversation_state_manager.py
│       └── requirements.txt
│
├── src/                                 # Shopify theme frontend
│   ├── sections/                        # Liquid templates
│   ├── styles/                          # CSS
│   ├── js/                              # JavaScript
│   └── layout/                          # Theme layout
│
├── design/                              # Current design system
│   └── README.md                        # Design audit & direction
│
├── design_book/                         # Legacy design reference
│   ├── BRAND_BOOK.md
│   └── design-tokens.json
│
├── docs/                                # Documentation
├── scripts/                             # Deployment & utility scripts
├── n8n/                                 # Automation workflows
├── tests/                               # Test suites
│
├── CRM_MASTER_README.md                 # CRM system guide
├── DEPLOYMENT_COMPLETE_2026_06_02.md    # Latest deployment summary
├── FLOW_VALIDATION_IMPLEMENTATION.md    # Flow fix documentation
├── CONVERSATION_AUDIT_SYSTEM.md         # Audit system guide
├── SYSTEM_ARCHITECTURE_COMPLETE.md      # Technical architecture
└── [100+ more documentation files]      # Guides, specs, reports
```

---

## 🔄 DATA FLOW (How It All Works)

```
┌──────────────────────────────────────────────────────────────┐
│                      CUSTOMER JOURNEY                        │
└──────────────────────────────────────────────────────────────┘

1️⃣ VISITOR ARRIVES
   └─→ Lands on pureleven.com
   └─→ GA4 + Meta Pixel track arrival
   └─→ gclid/fbclid captured in URL
   └─→ Session created (localStorage)

2️⃣ BROWSE PRODUCTS
   └─→ Page view events → GA4 → CRM
   └─→ Product views tracked
   └─→ Price interest identified
   └─→ Behavior logged to PostgreSQL

3️⃣ ADD TO CART
   └─→ Cart value captured
   └─→ Abandonment tracked
   └─→ Email/phone collected

4️⃣ CHECKOUT
   ├─ COMPLETED ORDER
   │  └─→ Shopify webhook fires
   │  └─→ CRM captures order
   │  └─→ Google Ads conversion tracked (server-side)
   │  └─→ Meta CAPI conversion fired
   │  └─→ Transactional email sent
   │  └─→ Confirmation WhatsApp sent (via Wabis)
   │  └─→ Order tracking flow initiated
   │
   └─ ABANDONED CART
      └─→ Captured in abandonment table
      └─→ Email recovery sequence starts (3 emails)
      └─→ WhatsApp recovery sequence starts (3 messages)
      └─→ Remarketing audience triggered (Google/Meta)

5️⃣ ORDER FULFILLMENT
   └─→ Tracking via Delhivery/Shiprocket
   └─→ Updates sent to customer (WhatsApp + Email)
   └─→ Delivery confirmation triggers thank-you flow

6️⃣ RETARGETING
   └─→ Past browsers: Google Ads dynamic remarketing
   └─→ Abandoned carts: Meta conversion campaign
   └─→ Purchased customers: Win-back campaigns
   └─→ Loyal customers: Premium tier campaigns
```

---

## 🎯 CURRENT SPRINT (June 2026)

### Just Completed ✅
- **Flow Validation System** (Cardamom bug fix)
  - Fuzzy matching for bot responses
  - Product intent detection (20+ spices)
  - Flow abandonment tracking
  
- **Conversation Audit System** (Full visibility)
  - 13-column audit log tracking every message
  - Intent detection and routing decisions
  - WhatsApp-style conversation replay UI
  - Automated daily reports at midnight UTC
  - Knowledge gap capture for gaps in catalog
  
- **AI Response Testing**
  - AI responses disabled (logged only, not sent)
  - Ready for Phase 2 verification
  - Database captures all activity

### In Progress 🔄
- System verification and data collection
- Monitoring first daily report (June 3)
- Collecting baseline week of data

### Next Phase 📋
- **Phase 2: Data-Driven Decisions**
  - Analyze conversation audit data
  - Measure flow completion rates
  - Review detected intents and gaps
  - Identify top customer needs
  - Plan feature updates based on real data

---

## 📊 KEY SYSTEMS & TECHNOLOGY

| System | Technology | Status | Purpose |
|--------|-----------|--------|---------|
| **Storefront** | Shopify, Liquid, JavaScript | 🟢 Live | E-commerce, product catalog |
| **WhatsApp Messaging** | Wabis API, FastAPI, SQLite | 🟢 Live | Customer communication, flows |
| **Customer Intelligence** | FastAPI, PostgreSQL, Nginx | 🟢 Live | CRM, audience building |
| **Paid Media** | Google Ads, Meta CAPI | 🟢 Live | Conversion tracking, retargeting |
| **Email/SMS** | Plunk, Sendgrid, N8N | 🟢 Live | Marketing automation |
| **Analytics** | GA4, GTM, server-side tracking | 🟢 Live | Event tracking, attribution |
| **Conversation Audit** | SQLite, FastAPI | 🟢 Live (NEW) | Message logging, replay, analysis |
| **Automation** | N8N, Webhook triggers | 🟢 Live | Workflow orchestration |

---

## 🖥️ INFRASTRUCTURE

### VPS (Primary AI/Messaging)
- **Host**: 192.46.213.140
- **Domain**: track.pureleven.com, ai.pureleven.com
- **Docker Containers**:
  - `pureleven-ai-engine` (FastAPI, Python 3.12)
  - `pureleven-postgres` (PostgreSQL 15)
  - Nginx (reverse proxy)
  - Caddy (SSL/TLS)

### Monitoring
- Health checks every 5 minutes
- Cron jobs for daily reports
- Docker logs for debugging
- Database backups enabled

---

## 📈 METRICS & SUCCESS MEASURES

### Now Available (from Audit System)
- Real-time conversation metrics
- Intent detection distribution
- Routing decision accuracy
- Flow completion rates
- Knowledge gap tracking
- Daily conversation summaries

### Coming (Phase 2)
- Customer lifetime value prediction
- Churn risk scoring
- Product recommendation engine
- Audience segment performance
- Attribution ROI by channel
- Campaign optimization recommendations

---

## 🔗 QUICK LINKS

### Live Services
- **Shopify Store**: https://pureleven.com
- **Customer Dashboard**: https://ai.pureleven.com
- **Conversation Audit**: https://track.pureleven.com/api/admin/conversations
- **Daily Reports**: https://track.pureleven.com/api/admin/daily-report

### Documentation
- **Brand Book**: See `design_book/BRAND_BOOK.md`
- **CRM Guide**: `CRM_MASTER_README.md`
- **Deployment Guide**: `DEPLOYMENT_COMPLETE_2026_06_02.md`
- **Architecture**: `SYSTEM_ARCHITECTURE_COMPLETE.md`
- **API Reference**: `CRM_API_DOCUMENTATION.md`

### Team
- **Primary Developer**: You
- **Deployment**: VPS + Docker
- **Database Admin**: You
- **Content/Product**: Brand team

---

## ✅ PROJECT HEALTH

| Aspect | Status | Notes |
|--------|--------|-------|
| **Storefront** | 🟢 Live | Stable, theme migration in progress |
| **WhatsApp** | 🟢 Live | All flows operational, audit system active |
| **CRM/Analytics** | 🟢 Live | All endpoints responsive, data flowing |
| **Paid Media** | 🟢 Live | Google & Meta tracking active |
| **Email** | 🟢 Live | Automation workflows running |
| **Audit System** | 🟢 Live (NEW) | Capturing conversations in real-time |
| **AI Responses** | 🟡 Testing | Disabled for Phase 2 verification |

---

## 📝 WHAT YOU'RE DOING RIGHT NOW

**Mission**: Build a data-driven, customer-centric organic spices brand with omnichannel growth platform.

**Current Focus**: 
1. ✅ Deploy conversation audit system (DONE - June 2)
2. ✅ Disable AI WhatsApp sends for testing (DONE - June 2)
3. 🔄 Collect week 1 data (baseline metrics)
4. 📊 Analyze audit data and user patterns
5. 🎯 Make Phase 2 decisions based on real data

**Philosophy**: "Don't build advanced features until measuring real data"

---

## 🚀 NEXT IMMEDIATE ACTIONS

1. **Today (June 2)**:
   - ✅ Verify AI sending is disabled
   - ✅ Confirm audit system capturing messages
   - Bookmark quick reference card

2. **Tomorrow (June 3)**:
   - Check first daily report (generated at midnight UTC)
   - Review conversation_review_2026_06_03.md
   - Verify cron job ran successfully

3. **This Week (June 3-9)**:
   - Monitor conversations being captured
   - Review daily reports each morning
   - Collect baseline week of data

4. **Next Week (June 9+)**:
   - Analyze full week of audit data
   - Measure flow completion rates
   - Identify top customer needs
   - Plan Phase 2 features based on data

