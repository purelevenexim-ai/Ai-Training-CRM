# Sprint 0 Validation Report

**Date:** 2026-05-25  
**Status:** ⚠️ BLOCKERS FOUND — Plan adjustment required before coding

---

## Executive Summary

The audit revealed **3 critical data quality issues** that change the Sprint 0 scope:

1. **crm_events** — Only 40% linked to customers (224/370 orphaned)
2. **crm_messages** — 0% linked to customers (all 7 have customer_id = NULL)
3. **crm_segments** — No customer membership data (table structure issue)

### Impact on Sprint 0

| Component | Status | Risk |
|---|---|---|
| Customer /360 (profile) | ✅ Can build | Use crm_orders + crm_customers |
| Timeline (events/messages) | ⚠️ Partial | Can use crm_orders only (skip events/messages) |
| Segments in /360 | ❌ Cannot build | No customer-segment mapping exists |
| Data quality | ⚠️ Mixed | Orders perfect, events broken |

---

## Detailed Findings

### 1. crm_events — 60% Orphaned

**Schema:** ✅ Correct structure
```sql
Table "crm_events"
  - id (PK)
  - customer_id (FK → crm_customers) — NULLABLE
  - email
  - event_type (wabis_sent, purchase, etc.)
  - source (wabis, shopify, etc.)
  - event_data (json)
  - timestamp
```

**Data Quality:** ❌ Problem
```
Total events:              370
Events WITH customer_id:   146 (40%)
Events WITH NULL customer_id: 224 (60%)

Sample of NULL rows:
  - All 5 sampled rows were "wabis_sent" events (no customer context)
  - No customer_id, no email field populated
```

**Root Cause:** Likely n8n workflow or event source doesn't capture/link customer info

### 2. crm_messages — 100% Orphaned

**Schema:** ✅ Correct structure
```sql
Table "crm_messages"
  - id (PK)
  - customer_id (FK → crm_customers) — NULLABLE
  - customer_email
  - customer_phone
  - channel
  - template_id
  - sent_at
```

**Data Quality:** ❌ Problem
```
Total messages:            7
Messages WITH customer_id: 0 (0%)
Messages WITH NULL customer_id: 7 (100%)
```

**Root Cause:** Messages table is populated but never linked to crm_customers

### 3. crm_segments — No Customer Membership

**Schema:** ❌ Architecture Issue
```sql
Table "crm_segments"
  - id (PK)
  - name
  - rule_set (json)
  - customer_count
  - is_active
  - (NO customer_id column!)
```

**Problem:** Segment master table exists, but there's NO separate "customer_segment_membership" table or many-to-many relationship.

**Data:**
```
Total segments: 4
Can we query "which customers in this segment"? NO
Can we query "which segments for this customer"? NO
```

**Root Cause:** Segments are defined as rules (JSON), but not materialized into customer mappings.

---

## Orders — Data Quality Good ✅

```
Total orders:                259
Orders WITH customer_id:     259 (100%)
Orders WITH NULL customer_id: 0 (0%)
Orders orphaned (no match):   0 (0%)
```

**All orders properly linked to crm_customers.**

---

## Customer Linking Summary

| Table | Linked to crm_customers | Status |
|---|---|---|
| crm_orders | 100% (259/259) | ✅ Production-ready |
| crm_events | 40% (146/370) | ⚠️ Partial data |
| crm_messages | 0% (0/7) | ❌ Not linked |
| crm_segments | N/A (no membership) | ❌ Not applicable |
| crm_customer_identities | 100% (10/10) | ✅ Working |

---

## What This Means for Sprint 0

### Original Plan

```
Customer 360
├── Profile (from crm_customers) ✅
├── Revenue (from crm_orders) ✅
├── Timeline (from crm_events + crm_messages + crm_orders) ⚠️
└── Segments ❌
```

### Revised Scope (Can Build Now)

```
Customer 360
├── Profile (from crm_customers) ✅
├── Revenue (from crm_orders) ✅
├── Timeline (from crm_orders ONLY — skip events/messages) ✅
└── Segments (remove for now) ❌
```

### What We CAN'T Build Yet

- ❌ Events timeline (146/370 orphaned)
- ❌ Messages timeline (all orphaned)
- ❌ Segment associations (no mapping table)

---

## Questions Before Proceeding

### Option 1: Continue Sprint 0 with Limited Scope

**Build:**
- /360 endpoint: customer + orders only (no events, no segments)
- /timeline endpoint: order history only

**Success criteria:**
```
Customer 360
├── Name, Email, Phone
├── Total Revenue
├── Order Count
├── Last Order Date
└── Order Timeline (5-10 most recent orders)
```

**Pros:** Ships fast, proves concept, uses good data  
**Cons:** Not the full "360" we promised

---

### Option 2: Fix Data First, Then Build Sprint 0

**Actions needed:**
1. Link crm_events to customers (backfill customer_id for 146 orphaned events)
2. Link crm_messages to customers (populate customer_id for 7 messages)
3. Create crm_customer_segments junction table (materialize segment membership)
4. Then build full /360 + /timeline

**Pros:** Complete feature  
**Cons:** 2-3 days of data work before Sprint 0 code

---

### Option 3: Hybrid — Fix Highest Value, Skip Lower Priority

**Fix immediately:**
- Link crm_events to customers (most data, 40% already good)

**Skip for now:**
- crm_messages (only 7 rows, marginal value)
- crm_segments (complex, lower priority)

**Pros:** Balance speed and completeness  
**Cons:** Still partial solution

---

## Nginx Routing Status

❓ Could not test `api.pureleven.com/api/health` (no response captured)

**Action:** Need manual verification that:
```
api.pureleven.com
  ↓ (Nginx proxy)
:8080
  ↓
FastAPI :8000
```

is working correctly. This should be confirmed before any deployment.

---

## Frontend Status

❓ **Question for user:** Does an existing customer detail UI already exist?

If **YES:**
- Sprint 0 APIs plug directly in
- We just need data to be correct

If **NO:**
- Sprint 0 proves API works
- But frontend build happens separately

---

## Recommendation

### Do NOT code Sprint 0 yet.

**Instead:**

1. **Today:** Review this report
2. **Tomorrow:** Decide: Option 1, 2, or 3 above
3. **Then:** Code Sprint 0 with confirmed scope

**I would recommend Option 3 (hybrid):**
- Fix crm_events linking (highest ROI)
- Build /360 + /timeline with crm_orders + linked crm_events
- Skip crm_messages + crm_segments for Sprint 1

This gives you 80% of the value in 90% less time than Option 2.

---

## Data Quality Checklist

Before proceeding with ANY option:

- [ ] Confirm Nginx routing works: `curl https://api.pureleven.com/api/health`
- [ ] Confirm frontend exists (or plan for Swagger-only Sprint 0)
- [ ] Choose Option 1, 2, or 3 above
- [ ] If Option 2/3: Schedule data fix work
- [ ] Review this report with team

---

## Next Steps

**Questions for user:**

1. Which option? (1, 2, or 3)
2. Does frontend exist? (for customer detail page)
3. Should we fix data first or ship limited /360 first?
4. Timeline preference: Fast + limited, or slow + complete?
