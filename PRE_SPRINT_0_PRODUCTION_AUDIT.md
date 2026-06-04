# Pre-Sprint 0: Production System Audit

**Status:** BLOCKING SPRINT 0 UNTIL ANSWERED  
**Purpose:** Understand existing architecture before designing new system  
**Risk Level:** CRITICAL (These answers determine 30% of implementation decisions)

---

## The Core Problem

We've designed a new Customer Intelligence Platform **without fully understanding** what currently exists.

This is backwards.

**Correct approach:**
```
Current System Audit
    ↓
Identify Gaps
    ↓
Design Extension (not replacement)
    ↓
Build Sprint 0
```

**Wrong approach (what we almost did):**
```
Design New System
    ↓
Hope It Fits
    ↓
Build Sprint 0
    ↓
Discover incompatibility at Month 2
```

---

# PART 1: Current Production System Inventory

## 1.1 Database Schema

**What we know:**
```sql
crm_orders
crm_customers
tracking_events
```

**What we DON'T know:**

Run this command on VPS and paste exact output:

```bash
ssh root@192.46.213.140 "docker exec pureleven-postgres psql -U pureleven -d pureleven -c \"\dt public.\""
```

Expected output:
```
            List of relations
 Schema | Name | Type  | Owner
--------+------+-------+--------
 public | crm_orders | table | pureleven
 public | crm_customers | table | pureleven
 public | tracking_events | table | pureleven
 ...
```

**Question 1.1:** What are ALL table names?

---

For each table, need schema:

```bash
ssh root@192.46.213.140 "docker exec pureleven-postgres psql -U pureleven -d pureleven -c \"\\d crm_orders\""
```

Expected output:
```
                     Table "public.crm_orders"
      Column      | Type | Collation | Nullable | Default
------------------+------+-----------+----------+---------
 id               | uuid |           | not null |
 shopify_order_id | text |           | not null |
 email            | text |           |          |
 total_amount     | numeric |       |          |
 ...
```

**Question 1.2:** For each table (crm_orders, crm_customers, tracking_events, others):
- Column names
- Data types
- NOT NULL constraints
- Unique constraints
- Foreign keys
- Indexes

---

## 1.2 Current APIs

**What we know:**
```
POST /api/crm/webhooks/shopify
GET/POST /api/crm/identify
(Meta, Google tracking endpoints)
```

**What we need:**

Run:
```bash
ssh root@192.46.213.140 "grep -r '@app.get\|@app.post\|@router.get\|@router.post' /opt/pureleven/app --include='*.py' | grep -v test"
```

Or read the FastAPI app file:
```bash
ssh root@192.46.213.140 "cat /opt/pureleven/app/crm_routes.py | grep -A 2 'def ' | head -50"
```

**Question 1.3:** What are ALL current API endpoints?
- Path
- Method (GET/POST/etc)
- Request/response format
- Authentication method

---

## 1.3 Current Docker Structure

**What we know:**
```
pureleven-postgres
pureleven-ai-engine
```

**What we need:**

Run:
```bash
ssh root@192.46.213.140 "docker compose -f /opt/pureleven/docker-compose.yml config | grep -A 5 'services:'"
```

**Question 1.4:** What are ALL running services?
- Service name
- Image/Dockerfile
- Ports exposed
- Environment variables
- Volumes
- Dependencies

---

## 1.4 Current Code Structure

**What we know:**
```
crm_routes.py
crm-attribution.js
```

**What we need:**

Run:
```bash
ssh root@192.46.213.140 "find /opt/pureleven/app -name '*.py' -type f | head -30"
```

**Question 1.5:** What's the folder structure of existing code?
- All Python files
- All JavaScript files
- Config files
- Migration files

---

---

# PART 2: Critical Architecture Questions

## 2.1 Customer Identifier Hierarchy

**Current reality check:**

Run:
```bash
ssh root@192.46.213.140 "docker exec pureleven-postgres psql -U pureleven -d pureleven -c \"
SELECT 
  email IS NOT NULL as has_email,
  phone IS NOT NULL as has_phone,
  shopify_customer_id IS NOT NULL as has_shopify_id,
  COUNT(*) as customer_count
FROM crm_customers
GROUP BY 1, 2, 3
ORDER BY 4 DESC
\""
```

Example output:
```
 has_email | has_phone | has_shopify_id | customer_count
-----------+-----------+----------------+----------------
 t         | t         | f              | 150
 t         | f         | f              | 50
 f         | t         | f              | 10
```

**Question 2.1:** Of your 200+ customers, what identifiers actually exist?
- What % have email?
- What % have phone?
- What % have shopify_customer_id?
- Any customer with ZERO identifiers?

**Question 2.2:** If customer has email + phone + shopify_id, which is source of truth?
- Shopify customer ID (primary)
- Email (primary)
- Phone (fallback)
- Order by this priority

---

## 2.2 Customer Merge Rules

**Scenario:**

Customer places Order 1 with:
```
Email: basil@example.com
Phone: NULL
Shopify ID: gid://shopify/Customer/12345
```

Later, same person places Order 2 with:
```
Email: basil.kumar@example.com (changed email!)
Phone: +919876543210
Shopify ID: gid://shopify/Customer/12345
```

**Question 2.3:** Are these same customer or different?
- If same: How do we detect (Shopify ID match)?
- If different: How do we manually merge later?
- Can customer have multiple emails?

---

**Question 2.4:** If customer has:
```
Phone: +919876543210
```

and later:

```
Email: different@example.com
Phone: +919876543210
```

Merge rule?

---

## 2.3 Source of Truth

**Question 2.5:** Which system is source of truth for customer data?

**Option A: Shopify**
```
Shopify API
    ↓
crm_customers
```

New system reads from crm_customers (which syncs from Shopify nightly).

**Option B: CRM**
```
crm_customers
    ↓
Source of truth
```

Shopify can have stale data. CRM decides.

**Option C: Event-Driven**
```
Shopify webhook
    ↓
behavior_events
    ↓
identity_service
    ↓
customer_profiles
```

New system is source of truth (no crm_customers dependency).

Which is it?

---

## 2.4 Traffic Volume

**Critical for performance decisions.**

Run:
```bash
ssh root@192.46.213.140 "docker exec pureleven-postgres psql -U pureleven -d pureleven -c \"
SELECT 
  DATE(created_at) as date,
  COUNT(*) as event_count,
  COUNT(DISTINCT CASE WHEN event_type='order' THEN order_id END) as order_count
FROM tracking_events
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 7
\""
```

**Question 2.6:** What's typical daily volume?
- Daily tracking events
- Daily orders
- Peak hour orders
- Expected growth rate

---

## 2.5 Shopify Webhook Reliability

**Question 2.7:** Current webhook handling:

Run:
```bash
ssh root@192.46.213.140 "docker logs pureleven-ai-engine --since 7d | grep -i 'webhook\|error\|retry' | tail -20"
```

- How many webhook failures/day?
- How many retries?
- How do you recover from failures?
- Is there a webhook replay mechanism?

---

## 2.6 Attribution Logic

**Question 2.8:** Current attribution model:

For a customer journey:
```
Day 1: Google Ads click (gclid) → visit store
Day 2: Direct → browse
Day 3: Purchase
```

Who gets credit?
- Google (first click)?
- Direct (last click)?
- Both (multi-touch)?

---

For Shopify+Meta+Google integration:

```
Shopify webhook
    ↓
Meta (90% with email)
Google (blocked, but hypothetically)
GA4 (100%)
```

Does this mean:
- Same order sent to 2-3 systems?
- Or one system is "primary"?

**Question 2.9:** What's the current attribution architecture?

---

## 2.7 Historical Data

**Question 2.10:** Existing data volume:

Run:
```bash
ssh root@192.46.213.140 "docker exec pureleven-postgres psql -U pureleven -d pureleven -c \"
SELECT 
  'crm_orders' as table_name, COUNT(*) as row_count FROM crm_orders
UNION ALL
SELECT 'crm_customers', COUNT(*) FROM crm_customers
UNION ALL
SELECT 'tracking_events', COUNT(*) FROM tracking_events
\""
```

Example:
```
     table_name    | row_count
-------------------+-----------
 crm_orders        | 259
 crm_customers     | 200
 tracking_events   | 5000
```

- How far back does data go?
- What's date range?
- Enough for retroactive linking (Option B in Q2.8)?

---

---

# PART 3: Business & Success Criteria

## 3.1 Week 4 Deliverable

**Question 3.1:** In Week 4 (after Sprint 0-3), what exactly do you need to see?

### Option A: Customer Timeline
```
Customer: Basil Kumar (basil@example.com)

Timeline:
  May 25: Viewed Black Pepper Product
  May 25: Added Pepper to Cart
  May 20: Purchased ₹899
  May 19: Viewed Turmeric Product
  ...

Orders:
  Order 1: ₹899 (May 20)
  Order 2: ₹699 (May 15)

Metrics:
  LTV: ₹1598
  Orders: 2
```

### Option B: Segment + Score
```
Customer: Basil Kumar
  Segment: Repeat Customer
  Health: 85/100
  Lead Score: 0.8
  Churn Risk: Low
  Next Action: WhatsApp Campaign
```

### Option C: Journey Attribution
```
Customer: Basil Kumar
  Google: 30% (attribution)
  Direct: 40%
  WhatsApp: 30%
  Total Revenue: ₹1598
```

### Option D: Something Else?

---

**Question 3.2:** Which screen from above matters most for business?

---

## 3.2 Product vs Foundation

**Question 3.3:** Is Customer 360 the destination or the foundation?

### Interpretation A: Destination
```
Customer 360 Platform
    ↓
Use Case 1: Support agents look up customer data
Use Case 2: Sales previews customer
Use Case 3: Dashboards
```

Ship Customer 360, done.

---

### Interpretation B: Foundation
```
Customer 360 API
    ↓
Use Case 1: Meta retargeting (send lookalike audiences)
Use Case 2: WhatsApp campaigns (segment by LTV)
Use Case 3: Email sequences (by segment + churn risk)
Use Case 4: Lead scoring (prioritize sales calls)
Use Case 5: Dashboards (secondary)
```

Customer 360 is means to an end.

---

**Question 3.4:** For Pureleven, which is it?

If Interpretation B:
- Which use case matters most?
- Meta audiences? WhatsApp? Lead scoring?

---

## 3.3 Current Revenue Impact

**Question 3.5:** How would you measure success?

### Option A: Engagement
```
Support agents: 5 lookups/day → 50 lookups/day
```

### Option B: Conversions
```
WhatsApp campaigns: 2% open → 5% open
Email campaigns: 1% CTR → 3% CTR
```

### Option C: Revenue
```
LTV: ₹500 → ₹800
Repeat order rate: 10% → 25%
```

### Option D: Operations
```
Customer data lookup time: 10 min → 30 seconds
Manual customer merges: 5/week → 0/week
```

---

**Question 3.6:** Which metric do you care about most?

---

---

# PART 4: Decision Matrix

**Based on your answers, here's what changes:**

## If Traffic = High (1000+ events/day)

**Changes:**
- Need async event processing (Celery mandatory)
- Need Redis for caching
- Need profile rebuild queue (not real-time)
- Need connection pooling (pgBouncer)

---

## If Source of Truth = Shopify

**Changes:**
- Don't create new customer table
- Link all events to crm_customers (foreign key)
- Read from crm_customers, not customer_profiles
- No retroactive identity linking (Shopify syncs nightly)

---

## If Source of Truth = Event-Driven (New)

**Changes:**
- Create customer_profiles as source
- Don't depend on crm_customers
- Retroactive identity linking needed
- Historical replay needed
- Separate from existing CRM

---

## If Week 4 = Timeline (Option A)

**Priority 1:** Events flowing
**Priority 2:** Identity service
**Priority 3:** Activity feed formatter
**Priority 4:** Simple UI

---

## If Week 4 = Segments + Score (Option B)

**Priority 1:** Events flowing
**Priority 2:** Identity service
**Priority 3:** Profile service (health score, segment rules)
**Priority 4:** Simple UI (metric cards, not timeline)

---

## If Week 4 = Meta Audiences (Foundation)

**Priority 1:** Events flowing
**Priority 2:** Identity service
**Priority 3:** Profile service
**Priority 4:** Meta export API (not UI)

---

---

# What I Need: Complete Your Answers

Fill in this template:

```markdown
# Pureleven Production System Audit

## Database
- Current tables: [Your list]
- crm_orders columns: [Your schema]
- crm_customers columns: [Your schema]
- tracking_events columns: [Your schema]
- Other tables: [Your list]

## APIs
- Current endpoints: [Your list]
- Auth mechanism: [JWT/Admin Secret/None]

## Docker
- Running services: [Your list]

## Traffic
- Daily tracking events: [Number]
- Daily orders: [Number]
- Peak load: [Events/sec]

## Identifiers
- % customers with email: [%]
- % customers with phone: [%]
- % customers with Shopify ID: [%]
- Data sample:
  [Paste output of Q2.1]

## Merge Rules
- [Answer Q2.3, Q2.4]

## Source of Truth
- [Answer Q2.5 - A, B, or C]

## Week 4 Success
- [Answer Q3.1 - Option A, B, C, or D]

## Product vs Foundation
- [Answer Q3.3 - Destination or Foundation]
- [If Foundation, which use case: Meta/WhatsApp/Email/Lead Scoring]

## Business Metric
- [Answer Q3.6]
```

---

# Why This Matters

These 10 answers determine:

1. **Architecture Style** — Monolithic or async-first
2. **Data Flow** — Event-driven or sync-driven
3. **Integration Points** — Extend existing or replace
4. **Success Criteria** — What we're actually building
5. **Timeline** — 6 weeks or 12+ weeks
6. **Risk Level** — High confidence or guessing

Without answers, we're designing blind.

---

**RECOMMENDATION:**

Before Sprint 0:
1. Complete this audit (2-3 hours)
2. Paste production schema + APIs here
3. Answer business questions 2.5-3.6
4. Then I adjust architecture based on reality
5. THEN code Sprint 0

**This is not overthinking. This is avoiding catastrophic redesign at month 2.**

