# Pureleven Platform Architecture — Foundation-First Plan

**Status:** Pre-Implementation Planning  
**Approach:** Platform foundation FIRST, then features  
**Timeline:** 4 sprints (backend), then UI, 8-10 weeks total  
**Philosophy:** Event-driven foundation prevents feature silos  

---

## The Core Insight

**What fails:** Building Customer 360 → Leads → WhatsApp → AI (4 disconnected silos)  
**What works:** Build event foundation → everything else becomes projections of events

```
Current (fragmented):
crm_orders
tracking_events
crm_customers
(nothing talks to anything)

Future (unified):
crm_events (source of truth)
  ↓
customer_profiles (projection)
  ↓
Leads / Automation / WhatsApp / AI (all read from events)
```

---

## Platform Architecture (8 Layers)

### Layer 1: Multi-Tenant Foundation

**Even though only Pureleven uses it, add `tenant_id` everywhere:**

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR,
    created_at TIMESTAMP
);
```

Every table gets:
```sql
tenant_id UUID NOT NULL,
FOREIGN KEY (tenant_id) REFERENCES tenants(id)
```

**Why:** Future: Pureleven, Brand B, Brand C on same platform.  
**Zero extra cost now.** Prevents refactor pain later.

---

### Layer 2: Visitor & Session Tracking

**New tables:**

```sql
CREATE TABLE crm_visitors (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    session_id UUID,
    customer_id VARCHAR,  -- Linked later
    
    -- Browser fingerprint
    device_id VARCHAR,
    user_agent TEXT,
    ip_address INET,
    
    -- Timeline
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE TABLE crm_sessions (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    visitor_id UUID NOT NULL,
    
    -- Session metrics
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Entry/exit
    landing_page VARCHAR,
    exit_page VARCHAR,
    referrer VARCHAR,
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

**Purpose:** Track anonymous traffic before anyone logs in.

---

### Layer 3: Event Schema Registry

**DO NOT allow random events. Validate against schema:**

```sql
CREATE TABLE crm_event_types (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    event_name VARCHAR,        -- page_view, product_view, etc.
    event_schema JSONB,        -- {required_fields: [...], optional_fields: [...]}
    description TEXT,
    created_at TIMESTAMP,
    
    UNIQUE(tenant_id, event_name),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- Seed canonical events:
-- page_view (required: url)
-- product_view (required: product_id)
-- add_to_cart (required: product_id)
-- begin_checkout (required: items_count)
-- purchase (required: order_id, amount)
-- whatsapp_sent (required: phone, message_id)
-- whatsapp_click (required: phone, link)
-- review_submitted (required: product_id, rating)
-- task_created (required: task_id, assignee)
-- automation_executed (required: automation_id, result)
```

**All events validated against schema. No spelling variations.**

---

### Layer 4: Universal Customer ID

**DO NOT use email/phone as primary key:**

```sql
CREATE TABLE customers (
    id VARCHAR PRIMARY KEY,  -- cust_01HJK9... (Nanoid or UUID)
    tenant_id UUID NOT NULL,
    
    -- Core identity (null until known)
    email VARCHAR,
    phone VARCHAR,
    name VARCHAR,
    
    -- Metadata
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    UNIQUE(tenant_id, email),
    UNIQUE(tenant_id, phone),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

**Everything references `cust_01HJK9...`, nothing else.**

---

### Layer 5: Event Stream (Central Nervous System)

```sql
CREATE TABLE crm_events (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    
    -- What happened
    event_type_id UUID NOT NULL,
    event_name VARCHAR,  -- Denormalized for queries
    event_data JSONB,    -- Flexible: {product_id, price, order_id, etc}
    
    -- Who did it
    visitor_id UUID,
    customer_id VARCHAR,  -- NULL until identity resolved
    session_id UUID,
    
    -- Attribution (captured at event time)
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    utm_content VARCHAR,
    gclid VARCHAR,
    fbclid VARCHAR,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    referer VARCHAR,
    
    created_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (event_type_id) REFERENCES crm_event_types(id),
    FOREIGN KEY (visitor_id) REFERENCES crm_visitors(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    -- Critical indexes
    CREATE INDEX idx_tenant_customer ON crm_events(tenant_id, customer_id) 
        WHERE customer_id IS NOT NULL;
    CREATE INDEX idx_tenant_event_type ON crm_events(tenant_id, event_name);
    CREATE INDEX idx_tenant_created ON crm_events(tenant_id, created_at DESC);
);
```

**This is the single most important table.**

Every action: page view, product view, purchase, message, task → here.

---

### Layer 6: Identity Resolution (Automated Linking)

```sql
CREATE TABLE crm_identities (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    customer_id VARCHAR NOT NULL,
    
    -- Identity keys
    email VARCHAR UNIQUE,
    phone VARCHAR UNIQUE,
    shopify_customer_id VARCHAR UNIQUE,
    
    -- Attribution IDs
    ga_client_id VARCHAR,
    fbp VARCHAR,          -- Meta's browser ID
    fbc VARCHAR,          -- Meta's conversion ID
    
    -- When linked
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    UNIQUE(tenant_id, email),
    UNIQUE(tenant_id, phone),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
```

**Service runs during event processing:**
1. Event has email?
2. Lookup in crm_identities
3. If found → link to that customer_id
4. If not → create new customer, link

---

### Layer 7: Customer Projection (Generated Profile)

```sql
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    customer_id VARCHAR NOT NULL UNIQUE,
    
    -- Identity
    email VARCHAR,
    phone VARCHAR,
    name VARCHAR,
    
    -- Timeline
    first_seen TIMESTAMP,
    first_purchase TIMESTAMP,
    last_purchase TIMESTAMP,
    last_activity TIMESTAMP,
    days_since_last_activity INTEGER,
    
    -- Purchase Metrics
    lifetime_value NUMERIC(12,2) DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    average_order_value NUMERIC(12,2),
    total_item_count INTEGER DEFAULT 0,
    
    -- Engagement
    total_events INTEGER DEFAULT 0,
    events_last_7_days INTEGER,
    events_last_30_days INTEGER,
    page_views_count INTEGER,
    product_views_count INTEGER,
    
    -- Preferences
    favorite_product_category VARCHAR,
    favorite_product_id VARCHAR,
    most_used_channel VARCHAR,  -- web, whatsapp, email, etc
    
    -- Segmentation
    segments JSONB,  -- {vip: true, wholesale: false, churn_risk: false}
    tags JSONB,      -- {cod_customer: true, bulk_buyer: true}
    
    -- Health Score (0-100)
    health_score INTEGER DEFAULT 0,
    
    -- AI Fields (Phase 4+)
    lead_score INTEGER DEFAULT 0,
    churn_probability FLOAT DEFAULT 0,
    predicted_reorder_days INTEGER,
    
    -- Lifecycle
    lifecycle_stage VARCHAR,  -- prospect, customer, repeat_customer, at_risk, churned
    
    -- Generation timestamp
    generated_at TIMESTAMP DEFAULT now(),
    
    UNIQUE(tenant_id, customer_id),
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_tenant_ltv ON customer_profiles(tenant_id, lifetime_value DESC);
    CREATE INDEX idx_tenant_score ON customer_profiles(tenant_id, lead_score DESC);
    CREATE INDEX idx_tenant_stage ON customer_profiles(tenant_id, lifecycle_stage);
);
```

**Generated every 5 minutes. Never edited manually.**

Recalculates from:
- crm_orders (revenue)
- crm_events (engagement)
- crm_identities (identity)

---

### Layer 8: Linked Order Data

**Modify existing `crm_orders`:**

```sql
ALTER TABLE crm_orders 
ADD COLUMN tenant_id UUID,
ADD COLUMN customer_id VARCHAR,
ADD FOREIGN KEY (customer_id) REFERENCES customers(id);

-- Backfill: match by email
UPDATE crm_orders co
SET customer_id = c.id
FROM customers c
WHERE co.email = c.email 
  AND c.tenant_id = co.tenant_id;
```

Now orders are linked to customer profiles.

---

## Customer Profile Enrichment

### Segments (Automatic)

Rules generated during profile creation:

```
VIP: lifetime_value > ₹10,000
Wholesale: total_orders > 20
Bulk Buyer: average_order_value > ₹1,000
Churn Risk: last_activity > 90 days
Early Adopter: first_purchase within 30 days of first_seen
```

### Tags (Manual + Automatic)

```
Manual: COD Customer, Influencer, Wholesale Partner
Automatic: High Return Rate, Delayed Payment, Frequent Support Contact
```

### Health Score

```
Health Score = 
  (Purchase Frequency Weight: 25%) +
  (Average Order Value Weight: 25%) +
  (Engagement Weight: 25%) +
  (Support/Returns Weight: 25%)

Result: 0-100 score
```

---

## Infrastructure Prerequisites

**Before any code:**

Add to VPS:

1. **Redis** (in-memory cache + queue)
   - Session storage
   - Profile cache (5 min TTL)
   - Job queue for background tasks

2. **Celery** (async task processing)
   - Profile generation job (every 5 min)
   - Event processing job
   - Webhook retries

3. **Sentry** (error tracking)
   - Catch exceptions
   - Alert on critical errors
   - Track error trends

4. **OpenTelemetry** (distributed tracing)
   - Trace event processing pipeline
   - Identify performance bottlenecks
   - Monitor async jobs

5. **Structured Logging** (ELK or CloudWatch)
   - Log every event
   - Query event processing
   - Audit trail

**Docker Compose additions:**
```yaml
redis:
  image: redis:latest
  
sentry:
  image: sentry:latest
```

---

## The Four-Sprint Execution Plan

### Sprint 1: Event Foundation (Week 1-2)

**Goal:** Event stream live, no UI needed.

**What to build:**

1. Create tables:
   - crm_visitors
   - crm_sessions
   - crm_event_types (with seed data)
   - crm_events

2. Update `crm_routes.py`:
   - POST `/api/crm/events` endpoint
   - Modify Shopify webhook to emit `purchase` event
   - Validate events against crm_event_types schema

3. Update `crm-attribution.js`:
   - Emit `page_view` events
   - Emit `product_view` events
   - Emit `add_to_cart` events
   - Emit `identify` events (when email entered)

**Code files to modify:**
- crm_routes.py (add event endpoint, modify webhook)
- crm-attribution.js (emit events instead of just localStorage)
- models.py (add CrmEvent, CrmVisitor, CrmSession models)

**Outcome:**
- ✅ crm_events table has 100+ events/day
- ✅ Browser events tracked
- ✅ Order events tracked
- ✅ All attribution in crm_events

**No UI. No CRM. Just data plumbing.**

---

### Sprint 2: Identity Resolution (Week 2-3)

**Goal:** All events for one person linked to single customer_id.

**What to build:**

1. Create tables:
   - crm_identities
   - Modify customers table (add tenant_id, universal ID)

2. Create Identity Service:
   - On every event: resolve visitor → customer
   - Link by email, phone, ga_client_id
   - Update all previous events from visitor

3. Backfill:
   - Match existing crm_customers by email
   - Create crm_identities entries
   - Link existing events

**Code files to modify:**
- crm_routes.py (add resolve_identity service, call during event processing)
- models.py (add CrmIdentity, update Customer model)

**Outcome:**
- ✅ All events for same person linked to one customer_id
- ✅ Zero duplicate customers
- ✅ crm_identities is source of truth

**No UI. Still just data.**

---

### Sprint 3: Customer Profile Projector (Week 3-4)

**Goal:** customer_profiles table fully populated.

**What to build:**

1. Create table:
   - customer_profiles

2. Create Profile Generation Service:
   - Runs every 5 minutes (Celery job)
   - Reads: crm_orders + crm_events + crm_identities
   - Writes: customer_profiles (replace entire row)
   - Calculates: LTV, lifecycle_stage, segments, tags, health_score

3. Backfill:
   - Generate profiles for all existing customers
   - Verify calculations correct

**Code files to modify:**
- crm_routes.py (add generate_customer_profile service)
- celery_tasks.py (add profile generation job, schedule every 5 min)
- models.py (add CustomerProfile model)

**Outcome:**
- ✅ customer_profiles fully populated
- ✅ LTV calculations correct
- ✅ Lifecycle stages derived from behavior
- ✅ All metrics ready for UI

**Still no UI. But now data is ready.**

---

### Sprint 4: Customer 360 UI + APIs (Week 4-5)

**Goal:** First UI that reads from unified data model.

**What to build:**

1. Backend APIs (read-only):
   - GET `/api/customers?q=...` (search in customer_profiles)
   - GET `/api/customers/{id}` (return customer_profiles row)
   - GET `/api/customers/{id}/timeline` (return crm_events)
   - GET `/api/customers/{id}/orders` (return crm_orders)
   - GET `/api/customers/{id}/segments` (segments from profile)

2. Frontend:
   - CustomerListPage (search + cards)
   - CustomerDetailPage (tabs: Overview, Timeline, Orders, Segments, Tags)
   - TimelineComponent (event feed)
   - OrderHistoryComponent

3. Styling:
   - Tailwind CSS
   - ShadCN UI components

**Code files to create:**
- New: crm/customers/pages/, crm/customers/components/
- Update: Next.js layout for customer module

**Outcome:**
- ✅ Click any customer, see full 360° view
- ✅ Timeline shows every interaction
- ✅ Orders visible
- ✅ Segments/tags visible
- ✅ Health score visible

---

## What NOT to Build Until Foundation is Solid

❌ Lead Pipeline (until customer_profiles done)  
❌ Automation Engine (until event foundation done)  
❌ WhatsApp Hub (until event foundation done)  
❌ AI Models (until rich customer data exists)  
❌ Reporting (until event system stable)  

**Why:** Each of these depends on events + profiles. Building them first creates duplicate logic.

---

## Key Decisions

1. **tenant_id everywhere** — Multi-tenant ready, even though single-tenant today

2. **Universal customer ID** — `cust_01HJK9...` not email/phone

3. **Event schema registry** — No spelling variations, all events validated

4. **customer_profiles is generated** — Recalculated every 5 min, never edited

5. **crm_events is immutable** — Never update or delete, only insert

6. **Separation of concerns:**
   - crm_events = What happened
   - crm_identities = Who did it
   - customer_profiles = Summary
   - crm_orders = Transactions

---

## Why This Prevents Silos

**If you build features first:**
```
Customer 360 → has its own customer table
Leads → has its own lead table
WhatsApp → has its own conversation table
AI → has its own scoring table

All duplicating customer data. Nightmare.
```

**If you build foundation first:**
```
crm_events (single source of truth)
  ↓
customer_profiles (single customer view)
  ↓
Customer 360 (reads profiles + events)
Leads (reads profiles)
Automation (reads events)
WhatsApp (reads profiles + events)
AI (reads profiles + events)

All reading same data. Clean.
```

---

## Success Metrics by Sprint

**Sprint 1:**
- ✅ crm_events table exists, 1000+ events
- ✅ Shopify orders emitted as events
- ✅ Browser events emitted from crm-attribution.js

**Sprint 2:**
- ✅ All events for same person linked to single customer_id
- ✅ crm_identities fully populated
- ✅ Zero duplicate customers
- ✅ Test: one person across 3 sessions → same customer_id

**Sprint 3:**
- ✅ customer_profiles generated for all customers
- ✅ LTV calculations match crm_orders totals
- ✅ Lifecycle stages correct
- ✅ Health scores 0-100

**Sprint 4:**
- ✅ Customer search < 200ms
- ✅ Customer detail loads instantly
- ✅ Timeline renders 100+ events instantly
- ✅ Mobile responsive
- ✅ No N+1 queries

---

## After Foundation is Built

**Phase 2: Lead Management**
- Lead table (reads from customer_profiles)
- Task management
- Activity feed
- Assignment rules

**Phase 3: Automation**
- Workflow builder (triggers on crm_events)
- Delays, branching, conditions
- Campaign attribution

**Phase 4: WhatsApp Hub**
- Conversation management
- Template library
- Message campaigns
- Bulk sending

**Phase 5: AI Layer**
- Lead scoring (ML models)
- Churn prediction
- Reorder prediction
- Product recommendations

All of these are now trivial because they have:
- Unified customer data (customer_profiles)
- Complete event history (crm_events)
- Automatic linking (crm_identities)

---

## Critical Success Factor

**The biggest mistake would be:**
- Building Customer 360 directly on crm_orders
- Not creating crm_events
- Not doing identity resolution

This leads to:
- Scattered data
- Hard to add WhatsApp later
- Hard to add automation later
- Hard to add AI later
- Refactoring nightmare

**The right way:**
- Build event foundation first
- Everything else is a view of events
- Easy to extend later

