# 📊 PURE LEVEN — QUICK VISUAL SUMMARY

---

## 🌿 THE BRAND
```
     PURE LEVEN
   ▔▔▔▔▔▔▔▔▔▔▔▔▔▔
   
   Organic Spices
   from Kerala
   
   Premium • Trustworthy • Educational
   Bright • Warm • Natural
   
   → https://pureleven.com
```

---

## 🏗️ THE 5 MAIN SYSTEMS

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1️⃣  SHOPIFY STOREFRONT          2️⃣  WHATSAPP MESSAGING SYSTEM │
│     (pureleven.com)                  (Wabis + Audit)           │
│     • Product catalog                • Bot flows                │
│     • Checkout                       • Customer communication   │
│     • Theme design                   • Order tracking           │
│     • Inventory                      • AI responses (disabled)  │
│                                       • Conversation audit      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  3️⃣  CUSTOMER CRM               4️⃣  PAID MEDIA & RETARGETING │
│     (ai.pureleven.com)              (Google Ads + Meta)        │
│     • Customer profiles             • Conversion tracking      │
│     • Order data                    • Audience syncing         │
│     • Behavior tracking             • Campaign management      │
│     • Segments & audiences          • ROI measurement          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  5️⃣  EMAIL & AUTOMATION                                        │
│     (Plunk + N8N)                                              │
│     • Campaign sequences                                       │
│     • Order notifications                                      │
│     • Win-back campaigns                                       │
│     • Lifecycle marketing                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📈 CUSTOMER JOURNEY

```
VISITOR ARRIVES              BROWSES PRODUCTS          ADDS TO CART
     ↓                            ↓                         ↓
  Session                  Tracked events            Email captured
  gclid tracked            GA4 events                Abandonment tracked


    CHECKOUT                 ORDER PLACED          FULFILLMENT BEGINS
       ↓                           ↓                        ↓
  Wabis capture         Shopify webhook           WhatsApp tracking
  Email recovery        CRM insert               Delhivery integration
  GA4 event             Google Ads tracked       Daily updates


    DELIVERY COMPLETE         RETARGETING STARTS
         ↓                            ↓
  Thank-you flow          Google Ads campaigns
  Review request          Meta remarketing
  Follow-up series        Segment-based messaging
```

---

## 🗂️ WHERE THINGS LIVE

```
PROJECT: /Users/bthomas/Documents/pureleven_dev/

├── STOREFRONT CODE
│   └── src/                          (Shopify theme files)
│
├── BACKEND (VPS - 192.46.213.140)
│   ├── anu-login/backend/            (Main AI/messaging engine)
│   │   └── app/
│   │       ├── ai/                   (Intent routing, audit logging)
│   │       └── routes/               (API endpoints, webhooks)
│   │
│   └── [Docker containers running on VPS]
│       ├── pureleven-ai-engine       (FastAPI, Port 8000)
│       └── pureleven-postgres        (Database, Port 5432)
│
├── CONFIGURATION
│   ├── .env.production               (Prod secrets)
│   ├── docker-compose.yml            (Container setup)
│   └── alembic/                      (Database migrations)
│
├── DOCUMENTATION
│   ├── PROJECT_OVERVIEW_COMPLETE.md  ← YOU ARE HERE
│   ├── CRM_MASTER_README.md
│   ├── SYSTEM_ARCHITECTURE_COMPLETE.md
│   ├── DEPLOYMENT_COMPLETE_2026_06_02.md
│   ├── CONVERSATION_AUDIT_SYSTEM.md
│   ├── FLOW_VALIDATION_IMPLEMENTATION.md
│   └── [100+ other docs]
│
├── UTILITIES
│   ├── scripts/                      (Deployment & helpers)
│   ├── n8n/                          (Automation workflows)
│   └── tests/                        (Test suites)
│
└── DATA EXPORTS
    ├── CHATBOT_TRAINING_DATA.json
    ├── customer_chats/               (Exported conversations)
    └── reports/                      (Analytics reports)
```

---

## 🚀 WHAT WE JUST DEPLOYED (June 2, 2026)

```
┌──────────────────────────────────────────────────────────────┐
│                   TWO MAJOR SYSTEMS DEPLOYED                │
└──────────────────────────────────────────────────────────────┘

SYSTEM 1: FLOW VALIDATION (Bug Fix)
───────────────────────────────────
Problem: Customer types "Cardamom" in language selection flow
         → Got looped back to language menu instead of product page
Solution: 
  ✅ Fuzzy matching on bot options
  ✅ Product intent detection (20+ keywords)
  ✅ Flow abandonment tracking
  ✅ Automatic fallback to catalog search

SYSTEM 2: CONVERSATION AUDIT (Full Visibility)
───────────────────────────────────────────────
What it captures:
  ✅ Every customer message
  ✅ Intent detection (what they want)
  ✅ Routing decision (where it went)
  ✅ Owner changes (human vs bot vs AI)
  ✅ Flow state transitions
  ✅ Response generation logs

Live Endpoints:
  📊 GET /api/admin/conversations
     → List all conversations
  
  💬 GET /api/admin/conversations/{phone}
     → View full chat history
  
  📱 GET /api/admin/conversations/{phone}/html
     → WhatsApp-style conversation replay
  
  ⚠️ GET /api/admin/routing-errors
     → Detect misroutes and issues
  
  📈 GET /api/admin/daily-report
     → Automated daily summary

Automation:
  🕐 Daily reports generated at midnight UTC
  📁 Stored in: /app/data/reports/
  📧 Can be emailed automatically

NEW: AI RESPONSES DISABLED FOR TESTING
──────────────────────────────────────
Why disabled?
  • Need to verify bot is working correctly before
    adding AI layer
  • Collecting data without AI interference
  • Testing Phase 2 in controlled way

Current behavior:
  ✅ AI still generates responses
  ✅ Responses logged to database
  ✅ Responses NOT sent to WhatsApp
  ✅ Customer doesn't see AI responses
  ✅ But we have full record for analysis

When re-enabling:
  → Just uncomment 3 lines in wave02_wabis_routes.py
  → Restart service
  → AI responses start flowing to WhatsApp
```

---

## 📊 DATABASES

```
┌───────────────────────────────────────────────────────────┐
│              POSTGRESQL (ai.pureleven.com)               │
├───────────────────────────────────────────────────────────┤
│ customers          Orders              Events             │
│ • ID               • ID                 • session_id       │
│ • Email            • customer_id        • event_type       │
│ • Phone            • total_amount       • timestamp        │
│ • gclid            • status             • metadata         │
│ • fbclid           • payment_method     • ...              │
│ • ...              • ...                • ...              │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│              SQLITE (track.pureleven.com)                │
├───────────────────────────────────────────────────────────┤
│ conversation_audit_log      flow_audit                   │
│ • message from customer      • flow_id                   │
│ • detected intent            • abandoned_at              │
│ • route decision             • expected vs actual        │
│ • owner before/after         • user message              │
│ • timestamp (UTC)            • reason for abandonment    │
│ • metadata                   • ...                       │
│ • ...                                                     │
└───────────────────────────────────────────────────────────┘
```

---

## 🎯 YOUR CURRENT MISSION

```
Phase 1: BUILD AUDIT SYSTEM           ✅ DONE (June 2)
         ├─ Flow validation
         ├─ Conversation logging
         ├─ Intent detection
         └─ Daily reports

Phase 2: COLLECT DATA                 🔄 IN PROGRESS
         ├─ Run for 1 week (June 2-9)
         ├─ Monitor conversations daily
         ├─ Review daily reports
         └─ Build baseline metrics

Phase 3: ANALYZE & DECIDE             📋 NEXT
         ├─ Measure flow completion
         ├─ Review intent distribution
         ├─ Identify gaps/problems
         ├─ Review customer feedback
         └─ Plan Phase 2 changes

Phase 4: IMPLEMENT IMPROVEMENTS       🚀 FUTURE
         ├─ Re-enable AI responses
         ├─ Add missing flows
         ├─ Optimize routing
         └─ A/B test changes

PHILOSOPHY:
"Don't build advanced features until measuring real data"
```

---

## 🎓 QUICK FACTS

- **Country**: India (Bangalore HQ)
- **Currency**: INR (₹)
- **Timezone**: IST (UTC+5:30)
- **Primary Traffic**: India mobile (70%)
- **Languages**: English, Hindi, Malayalam
- **Payment Methods**: COD (cash on delivery), UPI, Card
- **Logistics**: Delhivery, Shiprocket, In-house
- **Shipping**: 1-2 days metro, 3-5 days pan-India

---

## 💡 KEY INTEGRATIONS

| System | What It Does | Status |
|--------|-------------|--------|
| **Shopify** | E-commerce platform | 🟢 Live |
| **Wabis** | WhatsApp Business API | 🟢 Live |
| **GA4** | Website analytics | 🟢 Live |
| **Google Ads** | Search & remarketing | 🟢 Live |
| **Meta (Facebook/IG)** | Ads & CAPI tracking | 🟢 Live |
| **Delhivery** | Order tracking | 🟢 Live |
| **Plunk** | Email platform | 🟢 Live |
| **Sendgrid** | Transactional emails | 🟢 Live |
| **N8N** | Workflow automation | 🟢 Live |
| **Notion** | Project docs | 🟢 Live |

---

## 🔑 KEY FILES TO KNOW

```
FOR STOREFRONT CHANGES:
  → src/sections/           (Product, header, footer sections)
  → src/styles/             (CSS files)
  → design_book/BRAND_BOOK.md  (Design system)

FOR WHATSAPP CHANGES:
  → anu-login/backend/app/routes/wave02_wabis_routes.py
  → anu-login/backend/app/ai/intent_router.py
  → anu-login/backend/app/ai/audit_logger.py

FOR CRM/ANALYTICS CHANGES:
  → anu-login/backend/app/routes/crm_routes.py
  → anu-login/backend/app/storage.py

FOR DEPLOYMENTS:
  → deploy_flow_fixes.sh    (Flow system deployment)
  → setup_audit_system.sh   (Audit system deployment)
  → docker-compose.yml      (Container config)

FOR UNDERSTANDING:
  → PROJECT_OVERVIEW_COMPLETE.md    (What you're reading)
  → SYSTEM_ARCHITECTURE_COMPLETE.md (How it all connects)
  → CRM_MASTER_README.md            (CRM details)
```

---

## 🎯 REMEMBER

1. **You're building for a real business** serving actual customers in India
2. **Data drives decisions** - collect first, build second
3. **All systems are live** - changes go to production customers
4. **Focus on what matters** - flow completion, customer satisfaction, conversion
5. **Document everything** - future you will thank you

---

**Last Updated**: June 2, 2026  
**Next Review**: June 9, 2026 (after 1 week of data collection)

