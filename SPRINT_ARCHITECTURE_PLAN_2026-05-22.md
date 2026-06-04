# 🏗️ ORPHAN RECONNECTION & SPRINT ARCHITECTURE PLAN
**Pureleven CRM - Zero-Debt Recovery Path**  
**Date**: May 22, 2026  
**Strategy**: Reconnect Orphaned Features + Extend Existing Architecture

---

# EXECUTIVE SUMMARY

## The Core Problem
**10 orphaned features** exist with **40-100% missing connections**:
- Infrastructure built, integration missing
- Database ready, API disconnected  
- UI framework ready, business logic missing
- Webhooks ready, triggers not wired

## The Solution Strategy
Instead of building new systems, **reconnect existing orphan features** in a specific order:
1. **Layer 1** (Foundation): Lead management + offline matching
2. **Layer 2** (Marketing): Cart recovery + propensity scoring
3. **Layer 3** (Fulfillment): Delhivery tracking + inventory
4. **Layer 4** (Scale): Integrations + automation + optimization

**Key Principle**: Every new feature extends existing patterns, reuses existing code, and removes duplicate implementations.

---

# PART A: ORPHAN FEATURE RECONNECTION MAP

## 🔴 CRITICAL ORPHANS (Blocks Revenue)

### ORPHAN #1: Lead Management System
**Status**: 30% complete (10% database, 0% API, 0% UI)

**Why Needed**:
- CRM without lead management is just a customer database
- Currently: Salespeople can't identify/nurture leads separately
- Impact: 15-25% of prospects stay unqualified until they buy or leave
- Revenue Impact: -$50K-100K/year from lost leads

**What Exists** (Reusable):
```
✅ crm_customers table (can add is_lead, lead_source, lead_status fields)
✅ crm_journeys platform (can enroll leads)
✅ crm_segments for targeting (can create lead segments)
✅ Email campaigns infrastructure (can send to leads)
✅ Webhook infrastructure (can capture lead sources)
✅ API pattern for CRUD operations (copy from customers)
✅ Frontend dashboard pattern (copy from CRMDashboard_V2.jsx)
```

**What's Missing** (To Build):
```
❌ Lead-specific database table OR normalized lead schema
❌ Lead status workflow (new → qualified → nurture → customer → lost)
❌ Lead enrichment service (append company, industry, title)
❌ Lead scoring algorithm (RFM-based)
❌ Lead manager UI panel (LeadManagerPanel.jsx)
❌ Lead source tracking integration
❌ Lead-to-customer conversion endpoint
❌ Lead analytics dashboard
```

**Dependencies**:
- ✅ Prerequisite: Phase 0 (Auth, Standards) - Blocks until complete
- ✅ Prerequisite: Pydantic models for input validation
- ✅ Prerequisite: Database schema migration

**What Future Features Depend On This**:
- → Propensity scoring (needs lead segment)
- → CSV import (needs lead import capability)
- → Google Forms integration (leads come from forms)
- → Meta Lead Ads (leads come from ads)
- → Lead enrichment (needs enriched leads first)

**Implementation Estimate**: 40 hours (1 dev, 1 week)

**Code Reuse Checklist**:
- [ ] Copy CRUD pattern from customers → lead_routes.py
- [ ] Extend crm_models.py with Lead-related fields
- [ ] Reuse journeys enrollment logic for leads
- [ ] Reuse email campaign framework for lead sequences
- [ ] Copy dashboard panel pattern for lead manager UI
- [ ] Reuse segment creation logic for lead segmentation

---

### ORPHAN #2: Offline Conversion Matching (Phone/Address)
**Status**: 45% complete (endpoints exist, matching algorithm 0%)

**Why Needed**:
- Google Ads & Meta CAPI require 3 matching types: email, phone, address
- Currently: Only email matching works, phone/address unimplemented
- Impact: 40-60% of conversions don't match (attributed to "direct")
- Revenue Impact: -$150K-300K/year from misattribution

**What Exists** (Reusable):
```
✅ CAPI endpoints for Google Ads & Meta (framework ready)
✅ ConversionFeed table (stores matched conversions)
✅ Event ingestion pipeline (GA4, GA, Meta)
✅ Hashing utilities in API (use for phone hashing)
✅ Email matching algorithm (can adapt for phone/address)
✅ Retry queue pattern (exists in bulk enrollment)
```

**What's Missing** (To Build):
```
❌ Phone hashing algorithm (SHA256 of normalized phone)
❌ Address matching algorithm (postcode + city + street)
❌ Feedback loop from CAPI platforms (success/failure)
❌ Error/retry queue for failed matches
❌ Address normalization (Postman API or local)
❌ Match confidence scoring
❌ Dashboard showing match rates by platform
❌ Manual match override UI
```

**Dependencies**:
- ✅ Prerequisite: Lead management (leads can match offline)
- ✅ Prerequisite: Phone/address fields in customer table
- ✅ Prerequisite: CAPI endpoints functioning

**What Future Features Depend On This**:
- → Accurate attribution (depends on match rates)
- → Budget allocation to winners (needs correct attribution)
- → Delhivery tracking (order data for matching)

**Implementation Estimate**: 25 hours (1 dev, 1 week)

**Code Reuse Checklist**:
- [ ] Reuse existing email matching logic as template
- [ ] Extend ConversionFeed table schema for match_method
- [ ] Reuse error handling from journey bulk operations
- [ ] Reuse retry queue pattern from webhook processing

---

### ORPHAN #3: Customer Propensity Score
**Status**: 100% orphaned (endpoint exists, algorithm missing)

**Why Needed**:
- Propensity model identifies highest-value prospects
- Currently: Score endpoint exists but returns placeholder (always 0.5)
- Impact: Can't prioritize targets → spend wasted on low-probability conversions
- Revenue Impact: -$75K-150K/year from bad targeting

**What Exists** (Reusable):
```
✅ Propensity endpoint (GET /api/crm/propensity/{email}) - wired but not calculated
✅ crm_customers table with RFM data ready
✅ Order history tracking (all orders captured)
✅ Segment creation logic (can create propensity segments)
✅ Journey targeting by segment (can auto-enroll high-propensity)
✅ Analytics framework (can track model performance)
```

**What's Missing** (To Build):
```
❌ ML model training pipeline (RFM + behavior scoring)
❌ Feature engineering (recency, frequency, monetary, tenure)
❌ Model persistence (save trained model to disk)
❌ Scoring algorithm at customer retrieval time
❌ Model retraining schedule (weekly/monthly)
❌ Propensity segment auto-creation
❌ Propensity display in customer panel
❌ A/B testing propensity-based journeys
```

**Dependencies**:
- ✅ Prerequisite: Lead management (needs lead propensity too)
- ✅ Prerequisite: 90+ days of order history (for RFM calculation)
- ✅ Prerequisite: Offline matching (accurate order attribution)

**What Future Features Depend On This**:
- → Abandonment scoring (predict who will abandon)
- → Churn prediction (predict who will unsubscribe)
- → Inventory allocation (stock high-propensity items)

**Implementation Estimate**: 30 hours (1 dev + data scientist 0.5, 1 week)

**Code Reuse Checklist**:
- [ ] Copy order aggregation query from analytics
- [ ] Reuse segment creation for propensity segments
- [ ] Reuse journey enrollment for propensity-based sequences
- [ ] Extend customer response model to include propensity

---

### ORPHAN #4: Abandoned Cart Recovery
**Status**: 60% complete (detection works, recovery email not wired)

**Why Needed**:
- 70-80% of visitors leave without purchasing
- Currently: Can detect carts, but emails don't send automatically
- Impact: $1M-3M in lost revenue annually (industry standard: 3-5% recovery)
- Revenue Impact: +$50K-150K/year from recovery emails

**What Exists** (Reusable):
```
✅ AbandonedLeadPanel.jsx (UI ready)
✅ Cart detection endpoint (GET /api/crm/abandoned-carts)
✅ Email campaign infrastructure (Plunk/SendGrid ready)
✅ N8N automation hooks (webhooks can trigger N8N)
✅ Journey platform (can create cart recovery journey)
✅ Email template system (templates exist in Plunk)
✅ Attribution tracking (can track recovery order source)
```

**What's Missing** (To Build):
```
❌ Trigger mapping: Abandoned cart → N8N workflow
❌ Recovery email template variables (cart total, items, etc)
❌ Dynamic checkout link generation
❌ Recovery link tracking (UTM params)
❌ Conversion attribution for recovered orders
❌ Recovery email scheduling (1hr, 24hr, 72hr)
❌ Exclusion logic (don't email customers who already bought)
❌ Recovery dashboard metrics
```

**Dependencies**:
- ✅ Prerequisite: Lead management (recoverable carts are leads)
- ✅ Prerequisite: Offline matching (need to attribute recovery)
- ✅ Prerequisite: N8N webhooks working

**What Future Features Depend On This**:
- → Retention scoring (predict repeat buyers)
- → Upsell campaigns (abandoned vs completed carts)

**Implementation Estimate**: 25 hours (1 dev, 1 week)

**Code Reuse Checklist**:
- [ ] Copy email sending logic from lifecycle campaigns
- [ ] Reuse N8N webhook pattern from journey triggers
- [ ] Reuse attribution tracking from order conversion
- [ ] Copy dashboard metrics from analytics

---

### ORPHAN #5: Delhivery Shipment Tracking
**Status**: 20% complete (structure ready, API not connected)

**Why Needed**:
- Shipping is 50% of customer experience post-purchase
- Currently: RTO (return) tracking exists, but forward tracking doesn't
- Impact: Customers can't track deliveries → support tickets increase
- Revenue Impact: -$20K/year in support costs + churn

**What Exists** (Reusable):
```
✅ Delhivery webhook receiver (ready in crm_routes.py)
✅ Order status field (awaiting_shipment → shipped → delivered)
✅ Webhook validation pattern (HMAC signing)
✅ crm_orders table (can add tracking_url, tracking_id fields)
✅ Email notification system (can send tracking emails)
✅ RTO status tracking logic (can extend for forward tracking)
```

**What's Missing** (To Build):
```
❌ Delhivery API authentication (access token)
❌ Order-to-shipment ID mapping
❌ Polling logic (fetch shipment status periodically)
❌ Status update trigger (update order when status changes)
❌ Tracking URL generation
❌ Email notification trigger (shipment confirmed, out for delivery, delivered)
❌ Customer tracking page UI
❌ Delivery exception handling (lost, delayed, failed)
```

**Dependencies**:
- ✅ Prerequisite: Order management (needs orders)
- ✅ Prerequisite: Shopify order webhook (triggers tracking)
- ✅ Prerequisite: Delhivery API credentials (obtain from Delhivery)

**What Future Features Depend On This**:
- → Delivery confirmation email (needs tracking status)
- → Inventory sync (needs shipment data)

**Implementation Estimate**: 30 hours (1 dev, 1 week)

**Code Reuse Checklist**:
- [ ] Copy webhook validation pattern from Shopify webhooks
- [ ] Reuse email sending logic for tracking emails
- [ ] Copy polling pattern from GA4 import jobs
- [ ] Extend order update logic in crm_routes.py

---

## ⚠️ SECONDARY ORPHANS (Enhanced Features)

### ORPHAN #6: Google Forms Integration
**Status**: 25% orphaned (webhook receiver exists)

**Problem**: Google Forms API not connected, leads don't auto-import

**Quick Fix** (8 hours):
- Authenticate to Google Forms API
- Map form fields to customer_email, customer_name, phone, company
- Create lead for each response
- Enroll in lead nurture journey

**Existing Code to Reuse**:
- Lead creation logic (from lead management sprint)
- Journey enrollment (from journeys_routes.py)
- Webhook validation pattern (from Shopify)

---

### ORPHAN #7: Meta Lead Ads Integration
**Status**: 35% orphaned (lead capture exists, enrollment missing)

**Problem**: Leads captured from Meta but not enrolled in journeys

**Quick Fix** (12 hours):
- Map Meta Lead Ads fields to customers
- Auto-create lead for each ad lead
- Auto-enroll in lead nurture journey
- Track lead source = "Meta Ads"

**Existing Code to Reuse**:
- Lead enrollment from lead management
- Journey enrollment logic
- Meta API client (exists in crm_routes.py)

---

### ORPHAN #8: CSV Data Import
**Status**: 40% orphaned (export works, import doesn't)

**Problem**: Can export customers/orders, but can't import from CSV

**Quick Fix** (15 hours):
- Create CSV import endpoint
- Validate rows against schema
- Upsert customers based on email
- Handle duplicates & conflicts
- Provide import progress UI

**Existing Code to Reuse**:
- CSV parsing logic (exists in crm_routes.py for exports)
- Customer create logic
- Validation patterns
- Job tracking from bulk enrollment

---

### ORPHAN #9: Real-Time Notifications
**Status**: 60% orphaned (WebSocket works, UI/email digests missing)

**Problem**: WebSocket connected, browser notifications & email digests don't exist

**Quick Fix** (18 hours):
- Add browser notification support (Notification API)
- Create email digest service (summarize events)
- Wire journey step completion notifications
- Add unsubscribe control

**Existing Code to Reuse**:
- WebSocket pattern from realtime_routes.py
- Email sending logic from campaigns
- Event aggregation from analytics

---

### ORPHAN #10: Inventory Management
**Status**: 100% orphaned (completely missing)

**Problem**: No inventory tracking despite Shopify tracking it

**Implementation** (25 hours):
- Create crm_inventory table
- Sync from Shopify ProductVariant webhook
- Track inventory levels & changes
- Create inventory alerts (low stock)
- Use for product recommendations

**Existing Code to Reuse**:
- Webhook pattern from Shopify
- Table schema pattern from crm_models.py
- Alert pattern from error queue

---

# PART B: DEPENDENCY GRAPH

```
┌──────────────────────────────────────────────────────────────┐
│ PHASE 0: FOUNDATION (Must Complete First - 40 hours)         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  • Auth/Security (16h) → All endpoints protected            │
│  • Route consolidation (6h) → No duplicate definitions      │
│  • API standardization (12h) → Consistent responses         │
│  • Database indexes (6h) → Performance                      │
│                                                              │
│  ↓ ENABLES ALL SPRINTS BELOW                                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ SPRINT 1: CRITICAL ORPHANS (2 weeks, 4 devs, 100 hours)     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ✅ Lead Management (40h)                                     │
│    ├─ Database: Add lead-related fields to customers        │
│    ├─ API: CRUD endpoints for leads                         │
│    ├─ UI: LeadManagerPanel.jsx                              │
│    ├─ Business Logic: Lead status workflow                  │
│    └─ Enables: Google Forms, Meta Ads, CSV import           │
│                                                              │
│ ✅ Offline Conversion Matching (25h)                         │
│    ├─ Phone/address hashing                                 │
│    ├─ Match confidence scoring                              │
│    ├─ CAPI feedback loop                                    │
│    ├─ Error retry queue                                     │
│    └─ Enables: Accurate attribution, budget allocation      │
│                                                              │
│ ✅ Propensity Scoring (30h)                                  │
│    ├─ RFM model training                                    │
│    ├─ Feature engineering                                   │
│    ├─ Scoring algorithm                                     │
│    ├─ Propensity UI display                                 │
│    └─ Enables: Segment targeting, budget allocation         │
│                                                              │
│ ✅ Cart Recovery Wiring (25h)                                │
│    ├─ N8N trigger setup                                     │
│    ├─ Recovery email workflow                               │
│    ├─ Attribution tracking                                  │
│    ├─ Analytics dashboard                                   │
│    └─ Enables: Revenue recovery (+$50K/yr potential)        │
│                                                              │
│ Dependencies: ✅ All on Phase 0                              │
│ Blocks: Sprint 2 features                                   │
│ Revenue Impact: +$75K-250K potential                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ SPRINT 2: FULFILLMENT & AUTOMATION (2 weeks, 3 devs, 80h)  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ✅ Delhivery Shipment Tracking (30h)                         │
│    ├─ API authentication                                    │
│    ├─ Order-shipment mapping                                │
│    ├─ Status polling                                        │
│    ├─ Email notifications                                   │
│    └─ Enables: Delivery emails, customer satisfaction       │
│                                                              │
│ ✅ Google Forms Integration (8h)                             │
│    ├─ Reuse Lead Management (Sprint 1)                      │
│    ├─ Auto-create leads                                     │
│    ├─ Auto-enroll in journey                                │
│    └─ Enables: Lead capture from forms                      │
│                                                              │
│ ✅ Inventory Sync from Shopify (25h)                         │
│    ├─ Create crm_inventory table                            │
│    ├─ Webhook sync                                          │
│    ├─ Stock alerts                                          │
│    ├─ Dashboard display                                     │
│    └─ Enables: Product recommendations, stock-based offers  │
│                                                              │
│ ✅ Meta Lead Ads Auto-Enrollment (12h)                       │
│    ├─ Reuse Lead Management (Sprint 1)                      │
│    ├─ Auto-create leads from ads                            │
│    ├─ Auto-enroll in journey                                │
│    └─ Enables: Lead ads → CRM → Journey                     │
│                                                              │
│ Dependencies: ✅ Sprint 1 complete                           │
│ Blocks: Sprint 3 integrations                               │
│ Revenue Impact: -$20K support costs, +$50K inventory ops    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ SPRINT 3: DATA & INTEGRATIONS (2 weeks, 3 devs, 75h)       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ✅ CSV Import/Export (15h)                                   │
│    ├─ Reuse Lead Management endpoints                       │
│    ├─ Bulk customer import                                  │
│    ├─ Bulk order import                                     │
│    ├─ Progress tracking UI                                  │
│    └─ Enables: Data migration, partner integrations         │
│                                                              │
│ ✅ Real-Time Notifications (18h)                             │
│    ├─ Browser notifications API                             │
│    ├─ Email digest service                                  │
│    ├─ Journey completion alerts                             │
│    ├─ Unsubscribe controls                                  │
│    └─ Enables: User engagement, real-time updates           │
│                                                              │
│ ✅ SMS Provider Integration (20h)                            │
│    ├─ Twilio/AWS SNS setup                                  │
│    ├─ SMS template system                                   │
│    ├─ Journey SMS nodes                                     │
│    ├─ Delivery tracking                                     │
│    └─ Enables: Multi-channel messaging                      │
│                                                              │
│ ✅ Lead Enrichment Service (22h)                             │
│    ├─ Clearbit or Hunter API integration                    │
│    ├─ Auto-append company, industry, title                  │
│    ├─ Async processing                                      │
│    ├─ Manual enrichment UI                                  │
│    └─ Enables: Better lead scoring, targeting               │
│                                                              │
│ Dependencies: ✅ Sprint 2 complete                           │
│ Blocks: Sprint 4 optimization                               │
│ Revenue Impact: +$30K efficiency, +$25K enrichment value    │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ SPRINT 4: OPTIMIZATION & SCALE (2 weeks, 2 devs, 60h)      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ ✅ Advanced Analytics Dashboard (25h)                        │
│    ├─ Cohort analysis                                       │
│    ├─ Funnel analysis                                       │
│    ├─ Churn prediction visualization                        │
│    ├─ Custom report builder                                 │
│    └─ Enables: Data-driven decisions                        │
│                                                              │
│ ✅ Performance Optimization (20h)                            │
│    ├─ Query optimization                                    │
│    ├─ Response caching                                      │
│    ├─ Dashboard load time < 1s                              │
│    ├─ Database connection pooling                           │
│    └─ Enables: Scaling to 1M+ customers                     │
│                                                              │
│ ✅ Testing & Documentation (15h)                             │
│    ├─ Unit tests for lead management                        │
│    ├─ Integration tests for workflows                       │
│    ├─ E2E tests for critical paths                          │
│    ├─ API documentation                                     │
│    └─ Enables: Confidence in deployments                    │
│                                                              │
│ Dependencies: ✅ Sprint 3 complete                           │
│ Revenue Impact: +$50K efficiency, better ROI tracking       │
└──────────────────────────────────────────────────────────────┘
```

---

# PART C: SPRINT BREAKDOWN (DETAILED)

## SPRINT 1: CRITICAL ORPHANS (2 Weeks)
**Goal**: Reconnect lead management, propensity, matching, and cart recovery

### Task 1.1: Lead Management Database & API (40 hours)
**Why Needed**: CRM needs to track leads separately from customers

**Existing Code to Reuse**:
- `crm_models.py` - Base model patterns
- `crm_routes.py` - CRUD endpoint patterns  
- `crm_customers` table - Extend with lead fields
- `journeys_routes.py` - Enrollment pattern

**New Database Changes**:
```sql
-- Extend crm_customers table
ALTER TABLE crm_customers ADD COLUMN lead_source VARCHAR(50);  -- contact form, google forms, meta ads, etc
ALTER TABLE crm_customers ADD COLUMN lead_status VARCHAR(50) DEFAULT 'new';  -- new, contacted, qualified, converted, lost
ALTER TABLE crm_customers ADD COLUMN lead_score FLOAT DEFAULT 0.0;
ALTER TABLE crm_customers ADD COLUMN lead_created_at TIMESTAMP;
ALTER TABLE crm_customers ADD COLUMN contacted_at TIMESTAMP;
ALTER TABLE crm_customers ADD COLUMN qualified_at TIMESTAMP;

CREATE INDEX idx_lead_status ON crm_customers(lead_status);
CREATE INDEX idx_lead_source ON crm_customers(lead_source);
```

**New API Endpoints**:
```python
# In lead_routes.py (NEW FILE)
POST /api/crm/leads - Create lead
GET /api/crm/leads - List leads (paginated)
GET /api/crm/leads/{lead_id} - Get lead detail
PUT /api/crm/leads/{lead_id} - Update lead
PUT /api/crm/leads/{lead_id}/status - Change lead status (new→contacted→qualified→converted→lost)
POST /api/crm/leads/{lead_id}/convert - Convert lead to customer
POST /api/crm/leads/bulk-import - Import leads from CSV
GET /api/crm/leads/analytics - Lead funnel metrics
```

**New Frontend Component**:
```jsx
// src/components/LeadManagerPanel.jsx (NEW FILE)
├─ Lead list with filtering (by status, source, score)
├─ Lead detail view with timeline
├─ Status change workflow (buttons for each status)
├─ Lead to customer conversion button
├─ Manual lead creation form
├─ Lead score display
├─ Lead source badge
└─ Bulk action menu
```

**Files Affected**:
- `crm_models.py` - Add Lead-related fields
- `lead_routes.py` (NEW) - Lead CRUD endpoints
- `src/components/LeadManagerPanel.jsx` (NEW)
- `src/components/CRMDashboard_V2.jsx` - Add lead manager tab
- `src/services/crmApi.js` - Add lead API calls
- `alembic/versions/` - Migration for lead fields

**Testing Requirements**:
- [ ] Create lead via API (verify lead_status=new)
- [ ] Update lead status (verify timestamp updates)
- [ ] Convert lead to customer (verify email/phone merged)
- [ ] List leads paginated (verify sorting & filtering)
- [ ] Bulk import leads from CSV (verify validation)
- [ ] Lead analytics query (verify counts by status)

---

### Task 1.2: Offline Conversion Matching (25 hours)
**Why Needed**: Attribution incomplete without phone/address matching

**Existing Code to Reuse**:
- `crm_routes.py` - Event matching logic (email matching works)
- `ConversionFeed` table - For storing matches
- `crm_models.py` - Model patterns
- Error retry queue from bulk enrollment

**New Database Changes**:
```sql
-- Extend crm_conversion_feeds table
ALTER TABLE crm_conversion_feeds ADD COLUMN match_method VARCHAR(20);  -- email, phone, address
ALTER TABLE crm_conversion_feeds ADD COLUMN match_confidence FLOAT;  -- 0.0-1.0
ALTER TABLE crm_conversion_feeds ADD COLUMN hash_email VARCHAR(255);
ALTER TABLE crm_conversion_feeds ADD COLUMN hash_phone VARCHAR(255);
ALTER TABLE crm_conversion_feeds ADD COLUMN hash_address VARCHAR(255);

-- Create retry queue table
CREATE TABLE crm_conversion_match_errors (
    id SERIAL PRIMARY KEY,
    conversion_feed_id INTEGER,
    error_code VARCHAR(50),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**New API Endpoints**:
```python
# Add to crm_routes.py

POST /api/crm/conversions/match-phone - Match conversion by phone
POST /api/crm/conversions/match-address - Match conversion by address
POST /api/crm/conversions/match-error/{id}/retry - Retry failed match
GET /api/crm/conversions/match-stats - Match success rate metrics
POST /api/crm/conversions/feedback - Receive match feedback from CAPI
```

**Business Logic**:
```python
def hash_phone(phone: str) -> str:
    """Normalize and hash phone for matching"""
    # Remove non-digits, format as +1XXXXXXXXXX
    # SHA256 hash
    
def match_by_phone(conversion_feed: Dict, customer: Customer) -> Dict:
    """Match conversion feed to customer by phone"""
    # Hash both phones
    # Compare
    # Return match confidence score
    
def match_by_address(conversion_feed: Dict, customer: Customer) -> Dict:
    """Match conversion feed to customer by address"""
    # Normalize addresses (postcode + city + street)
    # Compare
    # Return match confidence score
```

**Files Affected**:
- `crm_routes.py` - Add matching logic
- `crm_models.py` - Extend ConversionFeed
- `crm_models.py` (NEW table) - ConversionMatchError
- Migration file

**Testing Requirements**:
- [ ] Phone hashing consistent (same input = same hash)
- [ ] Phone matching works (normalized +1-800-555-1234 matches)
- [ ] Address matching works (postcode + city matches)
- [ ] Failed matches queued for retry
- [ ] Retry logic increments counter
- [ ] Match statistics query accurate

---

### Task 1.3: Propensity Score Implementation (30 hours)
**Why Needed**: Score identifies high-value prospects for targeting

**Existing Code to Reuse**:
- Customer order history (all stored in crm_orders)
- RFM queries from analytics endpoints
- Segment creation logic (can create propensity segments)
- Journey enrollment (can auto-enroll high-propensity)

**New Database/Calculation**:
```python
# RFM Scoring Algorithm
def calculate_rfm_score(customer: Customer, orders: List[Order]) -> float:
    """
    Recency: Days since last order (weight: 0.4)
    Frequency: Number of orders (weight: 0.3)
    Monetary: Total order value (weight: 0.3)
    Returns score 0.0-1.0
    """
    r_days = (datetime.now() - orders[0].order_date).days
    recency_score = max(0, 1.0 - (r_days / 180))  # 180 days = 0 score
    
    frequency_score = min(1.0, len(orders) / 10.0)  # 10+ orders = max
    
    total_value = sum(o.total for o in orders)
    monetary_score = min(1.0, total_value / 5000.0)  # $5K+ = max
    
    return (recency_score * 0.4) + (frequency_score * 0.3) + (monetary_score * 0.3)

# Store in crm_customers
customer.propensity_score = calculate_rfm_score(customer, orders)
customer.propensity_updated_at = datetime.now()
```

**New API Endpoints**:
```python
# Add to crm_routes.py
GET /api/crm/customers/{email}/propensity - Get customer propensity
POST /api/crm/propensity/calculate-all - Batch calculate for all customers
GET /api/crm/propensity/stats - Score distribution stats
POST /api/crm/segments/propensity - Create segment by propensity range
```

**New Frontend Changes**:
```jsx
// In src/components/CustomerDetailPanel.jsx (extend)
├─ Display propensity score (visual gauge 0-100)
├─ Show score breakdown (Recency, Frequency, Monetary)
├─ Suggest high-propensity journey
└─ Manual override score button
```

**Files Affected**:
- `crm_models.py` - Add propensity_score, propensity_updated_at
- `crm_routes.py` - Add propensity calculation & endpoint
- `src/components/CustomerDetailPanel.jsx` - Display score
- Migration file

**Testing Requirements**:
- [ ] RFM score calculation accurate (test with known data)
- [ ] Score in range 0.0-1.0
- [ ] Batch calculation processes all customers
- [ ] Segment creation by propensity range works
- [ ] High-propensity customers identifiable
- [ ] Score updates over time as orders change

---

### Task 1.4: Abandoned Cart Recovery Wiring (25 hours)
**Why Needed**: Revenue leak from unrecovered carts

**Existing Code to Reuse**:
- `AbandonedLeadPanel.jsx` - UI ready
- Email sending from `crm_routes.py` - Lifecycle email logic
- N8N webhook pattern from journeys
- Order tracking & attribution logic
- Cart item display from shop data

**New Integration Points**:
```
Shopify Cart Webhook
    ↓
Detect Abandoned (no purchase 6+ hours)
    ↓
Trigger N8N Workflow
    ↓
Send Recovery Email (1hr, 24hr, 72hr schedule)
    ↓
Generate Checkout Link (direct to checkout)
    ↓
Track Recovery Email Sent (flag on order when recovered)
    ↓
Track Conversion (attribute to "abandoned cart recovery")
```

**New Database Changes**:
```sql
-- Extend crm_orders table
ALTER TABLE crm_orders ADD COLUMN abandoned_cart_detected_at TIMESTAMP;
ALTER TABLE crm_orders ADD COLUMN recovery_email_sent_at TIMESTAMP;
ALTER TABLE crm_orders ADD COLUMN recovery_email_clicked BOOLEAN DEFAULT FALSE;
ALTER TABLE crm_orders ADD COLUMN recovered_from_abandoned BOOLEAN DEFAULT FALSE;

-- Create recovery tracking
CREATE TABLE crm_abandoned_cart_recovery (
    id SERIAL PRIMARY KEY,
    cart_id VARCHAR(255),
    customer_id INTEGER,
    cart_value DECIMAL(10,2),
    cart_items JSONB,
    detected_at TIMESTAMP,
    email_sent_1hr BOOLEAN DEFAULT FALSE,
    email_sent_24hr BOOLEAN DEFAULT FALSE,
    email_sent_72hr BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**N8N Workflow Connection**:
```json
{
  "workflow": "Cart Recovery Emails",
  "trigger": "Cart abandoned (no purchase 6+ hours)",
  "steps": [
    {
      "action": "Wait 1 hour"
    },
    {
      "action": "Send Email 1",
      "template": "Abandoned Cart - First Reminder",
      "variables": ["customer_name", "cart_total", "checkout_url", "cart_items"]
    },
    {
      "action": "Wait 24 hours"
    },
    {
      "action": "Send Email 2",
      "template": "Abandoned Cart - 24hr Follow-up",
      "condition": "Not yet purchased"
    },
    {
      "action": "Wait 72 hours"
    },
    {
      "action": "Send Email 3",
      "template": "Abandoned Cart - Final Offer",
      "condition": "Not yet purchased"
    }
  ]
}
```

**New API Endpoints**:
```python
# Add to crm_routes.py
POST /api/crm/webhooks/cart-abandoned - Shopify cart webhook
GET /api/crm/abandoned-carts - List abandoned carts
POST /api/crm/abandoned-carts/{id}/trigger-recovery - Manually trigger recovery
GET /api/crm/abandoned-carts/analytics - Recovery metrics
POST /api/crm/abandoned-carts/{id}/mark-recovered - Mark order as recovered
```

**Files Affected**:
- `crm_routes.py` - Add cart recovery webhook & endpoints
- `crm_models.py` - Extend Order & create AbandonedCart table
- `src/components/AbandonedLeadPanel.jsx` - Display recovery status
- N8N workflow JSON (update)
- Migration file

**Testing Requirements**:
- [ ] Abandoned cart detected correctly (6+ hours no purchase)
- [ ] Recovery emails send at correct intervals (1hr, 24hr, 72hr)
- [ ] Checkout link works and goes to correct cart
- [ ] Recovered order attributed correctly
- [ ] Recovery metrics accurate (sent count, conversion rate)
- [ ] Manual trigger works for testing

---

## SPRINT 2: FULFILLMENT & AUTOMATION (2 Weeks)
**Goal**: Complete shipment tracking, Google Forms, Meta Ads, inventory sync

### Task 2.1: Delhivery Shipment Tracking (30 hours)
**Why Needed**: Customers need to track deliveries

**Existing Code to Reuse**:
- Webhook pattern from Shopify (crm_routes.py)
- RTO tracking logic (already implemented)
- Email sending from campaigns
- Order status update logic

**New Database Changes**:
```sql
ALTER TABLE crm_orders ADD COLUMN tracking_id VARCHAR(255);
ALTER TABLE crm_orders ADD COLUMN tracking_url VARCHAR(500);
ALTER TABLE crm_orders ADD COLUMN tracking_status VARCHAR(50);  -- in_transit, delivered, rto, failed
ALTER TABLE crm_orders ADD COLUMN tracking_last_updated TIMESTAMP;
ALTER TABLE crm_orders ADD COLUMN delivery_date DATE;

CREATE INDEX idx_tracking_id ON crm_orders(tracking_id);
```

**Delhivery API Integration**:
```python
# Add to crm_routes.py
import requests

class DelhiveryClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.delhivery.com/api/shipments"
    
    def get_shipment_status(self, tracking_id: str) -> Dict:
        """Fetch shipment status from Delhivery"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(f"{self.base_url}/{tracking_id}", headers=headers)
        return response.json()
    
    def poll_all_orders(self) -> List[Dict]:
        """Periodically poll all outstanding orders"""
        # Find orders with status awaiting_shipment or in_transit but no delivery_date
        # Call get_shipment_status for each
        # Update tracking_status & delivery_date
```

**New Webhook Endpoint**:
```python
POST /api/crm/webhooks/delhivery - Receive tracking status updates from Delhivery
# Payload: {tracking_id, status, updated_at, location}
# Update crm_orders.tracking_status & send email notification
```

**Email Triggers**:
```
Order Shipped → Send: "Your order is on its way" + tracking URL
Out for Delivery → Send: "Delivery today" + track real-time
Delivered → Send: "Order delivered! Thanks for your purchase"
RTO → Send: "Return initiated - tracking link"
Failed Delivery → Send: "Delivery attempted - reschedule"
```

**Files Affected**:
- `crm_routes.py` - Add Delhivery webhook & polling
- `crm_models.py` - Extend Order table
- Email templates (create in Plunk)
- Scheduled task (add polling job)
- Migration file

**Testing Requirements**:
- [ ] Delhivery API authentication works
- [ ] Shipment status fetched correctly
- [ ] Order tracking_status updated on webhook
- [ ] Tracking emails sent at right events
- [ ] Tracking URL generated correctly
- [ ] Polling job runs without errors

---

### Task 2.2: Google Forms Integration (8 hours)
**Why Needed**: Capture leads from forms automatically

**Existing Code to Reuse**:
- Lead management API (from Sprint 1)
- Journey enrollment logic (journeys_routes.py)
- Webhook validation pattern
- Google OAuth flow (partially exists)

**Implementation**:
```python
# Add to crm_routes.py
@router.post("/api/crm/webhooks/google-forms")
async def google_forms_webhook(request: Request):
    """
    Receive form response from Google Forms webhook
    Fields expected: email, name, phone, company, message
    """
    payload = await request.json()
    
    # Create lead
    lead = Lead(
        email=payload.get("email"),
        name=payload.get("name"),
        phone=payload.get("phone"),
        company=payload.get("company"),
        lead_source="google_forms",
        lead_status="new"
    )
    db.add(lead)
    db.commit()
    
    # Auto-enroll in lead nurture journey
    journey = db.query(Journey).filter_by(name="Lead Nurture").first()
    if journey:
        enrollment = JourneyEnrollment(
            customer_id=lead.id,
            journey_id=journey.id,
            enrolled_at=datetime.now()
        )
        db.add(enrollment)
        db.commit()
    
    return {"status": "processed"}
```

**Files Affected**:
- `crm_routes.py` - Add Google Forms webhook
- Setup Google Forms webhook configuration (manual)

**Testing Requirements**:
- [ ] Google Forms webhook configured
- [ ] Lead created on form submission
- [ ] Lead enrolled in journey automatically
- [ ] Lead source set to "google_forms"

---

### Task 2.3: Meta Lead Ads Auto-Enrollment (12 hours)
**Why Needed**: Auto-qualify leads from Meta ads

**Existing Code to Reuse**:
- Lead management API (Sprint 1)
- Journey enrollment (journeys_routes.py)
- Meta API client (already in crm_routes.py)

**Implementation**:
```python
# Add to crm_routes.py
@router.post("/api/crm/webhooks/meta-lead-ads")
async def meta_lead_ads_webhook(request: Request):
    """
    Receive lead from Meta Lead Ads
    Map fields: email → email, name → name, phone → phone
    """
    payload = await request.json()
    
    # Create lead from Meta
    lead = Lead(
        email=payload.get("email"),
        name=payload.get("name"),
        phone=payload.get("phone"),
        lead_source="meta_ads",
        lead_status="new"
    )
    db.add(lead)
    db.commit()
    
    # Auto-enroll in lead nurture
    journey = db.query(Journey).filter_by(name="Lead Nurture").first()
    if journey:
        JourneyEnrollment(...).add_and_commit()
    
    return {"status": "processed"}
```

**Files Affected**:
- `crm_routes.py` - Add Meta Lead Ads webhook

**Testing Requirements**:
- [ ] Meta Lead Ads webhook receives leads
- [ ] Lead created with correct fields
- [ ] Lead source set to "meta_ads"
- [ ] Auto-enrolled in journey

---

### Task 2.4: Inventory Sync from Shopify (25 hours)
**Why Needed**: Track inventory for stock-based offers

**New Database**:
```sql
CREATE TABLE crm_inventory (
    id SERIAL PRIMARY KEY,
    shopify_product_id VARCHAR(255),
    shopify_variant_id VARCHAR(255),
    product_name VARCHAR(255),
    variant_title VARCHAR(255),
    sku VARCHAR(50),
    quantity_available INTEGER,
    quantity_allocated INTEGER,
    last_synced TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sku ON crm_inventory(sku);
CREATE INDEX idx_product_id ON crm_inventory(shopify_product_id);
```

**Inventory Webhook** (from Shopify):
```python
@router.post("/api/crm/webhooks/inventory")
async def inventory_webhook(request: Request):
    """Receive inventory updates from Shopify"""
    payload = await request.json()
    
    # Update or create inventory record
    for variant in payload.get("variants", []):
        inv = db.query(Inventory).filter_by(
            shopify_variant_id=variant["id"]
        ).first()
        
        if inv:
            inv.quantity_available = variant["inventory_quantity"]
            inv.last_synced = datetime.now()
        else:
            inv = Inventory(
                shopify_product_id=payload["product_id"],
                shopify_variant_id=variant["id"],
                product_name=payload["title"],
                variant_title=variant["title"],
                sku=variant["sku"],
                quantity_available=variant["inventory_quantity"]
            )
            db.add(inv)
    
    db.commit()
    return {"status": "processed"}
```

**Files Affected**:
- `crm_models.py` - Create Inventory model
- `crm_routes.py` - Add inventory webhook
- Migration file

**Testing Requirements**:
- [ ] Inventory webhook received
- [ ] Inventory created or updated
- [ ] Quantities accurate
- [ ] Query performance acceptable

---

## SPRINT 3: DATA & INTEGRATIONS (2 Weeks)
**Goal**: CSV import, real-time notifications, SMS, lead enrichment

### Task 3.1: CSV Data Import/Export (15 hours)

**CSV Export** (Already Works):
- Download customer list as CSV
- Download order list as CSV

**CSV Import** (NEW):
```python
@router.post("/api/crm/bulk-import/customers")
async def import_customers_csv(request: Request, file: UploadFile):
    """
    Import customers from CSV
    Fields: email, name, phone, company
    """
    contents = await file.read()
    csv_reader = csv.DictReader(io.StringIO(contents.decode('utf-8')))
    
    created_count = 0
    for row in csv_reader:
        # Validate row
        if not row.get("email"):
            continue
        
        # Check if exists
        existing = db.query(Customer).filter_by(email=row["email"]).first()
        if existing:
            # Update
            existing.name = row.get("name") or existing.name
            existing.phone = row.get("phone") or existing.phone
        else:
            # Create new
            customer = Customer(
                email=row["email"],
                name=row.get("name"),
                phone=row.get("phone"),
                company=row.get("company")
            )
            db.add(customer)
            created_count += 1
    
    db.commit()
    return {"created": created_count, "total": len(list(csv_reader))}
```

**Files Affected**:
- `crm_routes.py` - Add import endpoints

**Testing Requirements**:
- [ ] CSV import creates customers
- [ ] CSV import updates existing
- [ ] Validation catches errors
- [ ] Progress tracking works

---

### Task 3.2: Real-Time Notifications (18 hours)

**Browser Notifications**:
```jsx
// In src/components/RealTimeNotificationCenter.jsx (NEW)
useEffect(() => {
    // Subscribe to WebSocket events
    socket.on("journey.step.completed", (data) => {
        showNotification(`Customer ${data.customer_name} completed ${data.step_name}`);
        Notification.requestPermission().then(permission => {
            if (permission === "granted") {
                new Notification("Journey Update", {
                    body: `${data.customer_name} completed ${data.step_name}`,
                    icon: "/pureleven-icon.png"
                });
            }
        });
    });
}, []);
```

**Email Digest**:
```python
# Daily email summarizing events
@router.post("/api/crm/notifications/send-digest")
async def send_notification_digest():
    """Send daily email digest of events"""
    # Aggregate events from last 24 hours
    # Create email with summary
    # Send via Plunk/SendGrid
```

**Files Affected**:
- `src/components/RealTimeNotificationCenter.jsx` (NEW)
- `realtime_routes.py` - Add digest endpoint
- Email template for digest

**Testing Requirements**:
- [ ] Browser notifications appear
- [ ] WebSocket events trigger notifications
- [ ] Email digest sends daily
- [ ] Digest content accurate

---

### Task 3.3: SMS Provider Integration (20 hours)

```python
# Add to crm_routes.py
from twilio.rest import Client

class SMSService:
    def __init__(self, account_sid, auth_token):
        self.client = Client(account_sid, auth_token)
    
    def send_sms(self, phone: str, message: str) -> Dict:
        """Send SMS via Twilio"""
        message = self.client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE"),
            to=phone
        )
        return {"sms_id": message.sid, "status": message.status}

@router.post("/api/crm/sms/send")
async def send_sms(phone: str, template_name: str, variables: Dict):
    """Send SMS to customer"""
    # Get template
    # Format with variables
    # Send via SMS service
    # Log in crm_messages table
```

**Journey SMS Node** (NEW):
```
Journey → SMS Action Node → SMS Service → Customer Phone
```

**Files Affected**:
- `crm_routes.py` - Add SMS endpoints
- `src/components/JourneyBuilderUI.jsx` - Add SMS node

**Testing Requirements**:
- [ ] SMS sends via Twilio
- [ ] SMS appears in journey log
- [ ] Template variables work
- [ ] Delivery confirmation received

---

### Task 3.4: Lead Enrichment Service (22 hours)

```python
# Add to crm_routes.py
import requests

class EnrichmentService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.clearbit.com/v1"
    
    async def enrich_lead(self, email: str) -> Dict:
        """Fetch lead enrichment from Clearbit"""
        # email → company, job title, industry, location
        url = f"{self.base_url}/enrichment?email={email}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "company": data.get("company", {}).get("name"),
                "job_title": data.get("person", {}).get("title"),
                "industry": data.get("company", {}).get("industry"),
                "location": data.get("person", {}).get("location")
            }
        return {}

@router.post("/api/crm/leads/{lead_id}/enrich")
async def enrich_lead(lead_id: int):
    """Async enrich lead with Clearbit data"""
    lead = db.query(Lead).get(lead_id)
    enrichment = await EnrichmentService(...).enrich_lead(lead.email)
    
    lead.company = enrichment.get("company")
    lead.job_title = enrichment.get("job_title")
    lead.industry = enrichment.get("industry")
    
    db.commit()
    return {"status": "enriched", "data": enrichment}
```

**Files Affected**:
- `crm_routes.py` - Add enrichment endpoint
- `crm_models.py` - Add enrichment fields to Lead

**Testing Requirements**:
- [ ] Enrichment API called with email
- [ ] Data populated correctly
- [ ] Async processing works
- [ ] Manual enrichment triggered

---

## SPRINT 4: OPTIMIZATION & SCALE (2 Weeks)
**Goal**: Analytics, performance, testing, documentation

### Task 4.1: Advanced Analytics Dashboard (25 hours)

**Cohort Analysis**:
```
Cohorts by signup date
Revenue per cohort
Retention by cohort
Churn rate by cohort
```

**Funnel Analysis**:
```
Lead → Contacted → Qualified → Customer
Conversion rates at each step
Drop-off analysis
Time between steps
```

**Files Affected**:
- `src/components/AnalyticsAdvancedDashboard.jsx` (NEW)
- `crm_routes.py` - Add analytics endpoints

---

### Task 4.2: Performance Optimization (20 hours)

**Query Optimization**:
- Add missing database indexes
- Optimize N+1 query problems
- Cache frequent queries

**Response Caching**:
- Redis caching for customer list
- Cache propensity scores (expire hourly)
- Cache segment counts

**Dashboard Performance**:
- Lazy load components
- Paginate table data
- Parallel API calls

**Files Affected**:
- `crm_routes.py` - Query optimization
- `main.py` - Add caching middleware
- Database migrations - Add indexes

---

### Task 4.3: Testing & Documentation (15 hours)

**Unit Tests**:
- Lead creation validation
- Propensity calculation
- Matching algorithm
- SMS sending

**Integration Tests**:
- Full lead workflow (create → contact → qualify → convert)
- Cart recovery workflow
- Journey enrollment workflow

**E2E Tests**:
- Customer signup → lead creation → journey enrollment
- Cart abandonment → recovery email → conversion

**Documentation**:
- API docs for new endpoints
- Integration guides (Delhivery, Google Forms, SMS)
- Lead management workflow
- Troubleshooting guide

**Files Affected**:
- `tests/` - Unit and integration tests
- `docs/` - API documentation
- README updates

---

# PART D: REUSABLE CODE INVENTORY

## Backend Patterns (To Extend)

### Pattern 1: CRUD Endpoint
```python
# Location: crm_routes.py (lines 200-300)
# Used by: Customer, Order, Event endpoints
# Reuse for: Lead, Inventory

@router.post("/api/crm/{resource}")
async def create_resource(payload: ResourceCreate, db: Session):
    resource = Resource(**payload.dict())
    db.add(resource)
    db.commit()
    return {"id": resource.id, "status": "created"}

@router.get("/api/crm/{resource}")
async def list_resource(skip: int = 0, limit: int = 100, db: Session):
    resources = db.query(Resource).offset(skip).limit(limit).all()
    return {"total": len(resources), "items": resources}

@router.get("/api/crm/{resource}/{id}")
async def get_resource(id: int, db: Session):
    resource = db.query(Resource).get(id)
    if not resource:
        raise HTTPException(status_code=404)
    return resource

@router.put("/api/crm/{resource}/{id}")
async def update_resource(id: int, payload: ResourceUpdate, db: Session):
    resource = db.query(Resource).get(id)
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(resource, key, value)
    db.commit()
    return resource

@router.delete("/api/crm/{resource}/{id}")
async def delete_resource(id: int, db: Session):
    resource = db.query(Resource).get(id)
    db.delete(resource)
    db.commit()
    return {"status": "deleted"}
```

### Pattern 2: Webhook Handler
```python
# Location: crm_routes.py (lines 800-900)
# Used by: Shopify, GA4, Meta webhooks
# Reuse for: Delhivery, Google Forms, Meta Ads

def validate_webhook_signature(request_body: str, signature: str, secret: str) -> bool:
    """Validate webhook signature (HMAC-SHA256)"""
    expected = hmac.new(
        secret.encode(),
        request_body.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

@router.post("/api/crm/webhooks/{provider}")
async def handle_webhook(request: Request):
    signature = request.headers.get("X-Webhook-Signature")
    body = await request.body()
    
    if not validate_webhook_signature(body.decode(), signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = json.loads(body)
    # Process webhook...
    return {"status": "processed"}
```

### Pattern 3: Bulk Job Processing
```python
# Location: journeys_routes.py (lines 1200-1300)
# Used by: Bulk enrollment, CSV import
# Reuse for: CSV import, enrichment batch

@router.post("/api/crm/jobs/bulk-process")
async def start_bulk_job(payload: BulkJobRequest, background_tasks: BackgroundTasks):
    # Create job record
    job = BulkJob(
        name=payload.name,
        status="processing",
        total_items=len(payload.items)
    )
    db.add(job)
    db.commit()
    
    # Process in background
    background_tasks.add_task(process_bulk_job, job.id, payload.items)
    
    return {"job_id": job.id, "status": "started"}

def process_bulk_job(job_id: int, items: List[Dict]):
    job = db.query(BulkJob).get(job_id)
    for i, item in enumerate(items):
        # Process item
        job.processed_items = i + 1
        db.commit()
```

### Pattern 4: Event Publishing
```python
# Location: realtime_routes.py (lines 50-100)
# Used by: Journey updates, metrics publishing
# Reuse for: Notification events, inventory alerts

async def publish_event(event_type: str, data: Dict, channel: str = None):
    """Publish event to Redis pub/sub"""
    if redis:
        redis_client.publish(
            f"events:{channel or 'general'}",
            json.dumps({
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        )
```

## Frontend Patterns (To Extend)

### Pattern 1: CRUD Panel
```jsx
// Location: src/components/CRMDashboard_V2.jsx
// Used by: Customer, Order, Event panels
// Reuse for: Lead, Inventory, Notification panels

export function CRUDPanel() {
    const [items, setItems] = useState([]);
    const [filter, setFilter] = useState({});
    
    useEffect(() => {
        crmApi.list(filter).then(setItems);
    }, [filter]);
    
    return (
        <div>
            <FilterBar onFilterChange={setFilter} />
            <Table data={items} />
            <Pagination />
        </div>
    );
}
```

### Pattern 2: Detail View
```jsx
// Location: src/components/CustomerDetailPanel.jsx
// Used by: Customer details, Order details
// Reuse for: Lead details, Inventory details

export function DetailPanel({ id }) {
    const [item, setItem] = useState(null);
    
    useEffect(() => {
        crmApi.get(id).then(setItem);
    }, [id]);
    
    return (
        <div>
            <Header data={item} />
            <Tabs>
                <Tab name="Overview" content={<OverviewTab data={item} />} />
                <Tab name="History" content={<HistoryTab itemId={id} />} />
                <Tab name="Actions" content={<ActionsTab data={item} />} />
            </Tabs>
        </div>
    );
}
```

## Database Patterns (To Extend)

### Pattern 1: Audit Trail
```python
# Used by: All models
# Pattern: Track created_at, updated_at, created_by, updated_by

class AuditMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)
    updated_by = Column(String, nullable=True)

class Lead(Base, AuditMixin):
    __tablename__ = "crm_leads"
    ...
```

### Pattern 2: Soft Delete
```python
# Used by: Customers, Orders, Journeys
# Pattern: Flag deleted instead of removing

class SoftDeleteMixin:
    deleted_at = Column(DateTime, nullable=True)
    
    def soft_delete(self):
        self.deleted_at = datetime.utcnow()

class Lead(Base, SoftDeleteMixin):
    __tablename__ = "crm_leads"
    ...
```

---

# PART E: EXECUTION CHECKLIST

## Pre-Sprint 1 Checklist
- [ ] Phase 0 (Foundation) complete
- [ ] Team assigned (4 devs)
- [ ] Staging environment ready
- [ ] Database backup taken
- [ ] Daily standup scheduled
- [ ] Jira/Github issues created
- [ ] Code review process defined

## Sprint 1 Completion Checklist
- [ ] Lead CRUD endpoints tested
- [ ] Lead manager UI functional
- [ ] Offline matching working (email + phone + address)
- [ ] Propensity scores calculated
- [ ] Cart recovery emails flowing
- [ ] All 4 features deployed to staging
- [ ] Regression testing passed
- [ ] Performance acceptable (< 500ms responses)

## Sprint 2 Completion Checklist
- [ ] Delhivery tracking end-to-end
- [ ] Google Forms leads auto-created
- [ ] Meta lead ads auto-enrolled
- [ ] Inventory synced from Shopify
- [ ] All 4 features deployed to staging
- [ ] Integration testing passed

## Sprint 3 Completion Checklist
- [ ] CSV import/export working
- [ ] Real-time notifications functional
- [ ] SMS provider integrated
- [ ] Lead enrichment service live
- [ ] Performance optimized (< 1s dashboard load)

## Sprint 4 Completion Checklist
- [ ] Advanced analytics dashboard working
- [ ] Database queries optimized
- [ ] All tests passing (70%+ coverage)
- [ ] Documentation complete
- [ ] Ready for production deployment

---

# PART F: SUCCESS METRICS

| Metric | Current | After Sprint 1 | After Sprint 4 |
|--------|---------|---|---|
| Lead qualification rate | 0% | 60% | 85%+ |
| Attribution accuracy | 45% | 75% | 95%+ |
| Propensity model | N/A | 0.7 AUC | 0.85 AUC |
| Cart recovery rate | 0% | 15% | 25%+ |
| Tracking coverage | 0% | 85% | 99%+ |
| Dashboard load time | 3s | 1.5s | < 1s |
| API error rate | 1.2% | 0.5% | < 0.1% |
| Customer satisfaction | 3.2/5 | 3.8/5 | 4.5/5 |

---

# PART G: RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|---|---|---|
| Database migration fails | 5% | HIGH | Backup before, rollback plan ready |
| API breaks existing clients | 10% | MEDIUM | Test in staging, gradual rollout |
| Performance degrades | 15% | MEDIUM | Index all new queries, benchmark |
| Lead scoring inaccurate | 20% | MEDIUM | A/B test model, manual validation |
| Third-party APIs down | 30% | LOW | Graceful degradation, fallback UI |
| Team velocity slower | 25% | MEDIUM | Hire contractors if needed |

---

**END OF SPRINT ARCHITECTURE PLAN**

Next Steps:
1. Review this plan with the team
2. Assign developers to sprints
3. Create Jira/GitHub issues
4. Start Phase 0 (if not done)
5. Begin Sprint 1 Week 1

**Questions? Refer to:**
- `COMPREHENSIVE_PROJECT_AUDIT_2026-05-22.md` - Full audit
- `EXECUTIVE_ACTION_PLAN_2026-05-22.md` - High-level strategy
- `TECH_DEBT_SCORECARD_2026-05-22.md` - Technical breakdown
