# Pureleven Customer Intelligence Platform — Optimized, Minimal Architecture

**Status:** Architect-Approved, Lean, Executable  
**Approach:** Identity → Profile → Timeline → UI (then expand)  
**Timeline:** 7 phases, 7 weeks  
**Philosophy:** Build what matters. Add complexity only when needed.

---

## Core Principle

```
Event
  ↓
Identity (who?)
  ↓
Profile (what's their story?)
  ↓
Timeline (what did they do?)
  ↓
UI (see it)
  ↓
Predictions (predict next step)
  ↓
Automation (act)
```

**Everything else is premature.**

---

## Folder Structure (Minimal)

```
app/

├── domains/
│   ├── tracking/
│   │   ├── event_service.py
│   │   ├── models.py
│   │   └── repository.py
│   │
│   ├── customers/
│   │   ├── identity_service.py
│   │   ├── profile_service.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── api.py
│   │
│   ├── communications/  [STUB, ready for WhatsApp]
│   │   ├── models.py
│   │   └── api.py
│   │
│   └── automation/  [STUB, ready for workflows]
│       ├── models.py
│       └── api.py
│
├── shared/
│   ├── database/
│   │   ├── models.py
│   │   ├── session.py
│   │   └── migrations/
│   │
│   ├── events/
│   │   └── event_schemas.py  (validation)
│   │
│   └── utils/
│       └── logging.py
│
├── api/
│   ├── health.py
│   └── v1/
│       └── customers.py  (Customer 360 API)
│
├── celery_tasks.py
├── settings.py
└── main.py
```

**Why:** Each domain stays < 500 lines. Clean, understandable, ready to scale.

---

## Data Model (Minimal)

### What's Required

```sql
-- Events (foundation)
CREATE TABLE behavior_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR NOT NULL,  -- page_view, product_view, add_to_cart, purchase
    event_data JSONB NOT NULL,
    visitor_id UUID,
    customer_id VARCHAR,
    session_id UUID,
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    gclid VARCHAR,
    fbclid VARCHAR,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT now(),
    
    CREATE INDEX idx_customer_id ON behavior_events(customer_id) 
        WHERE customer_id IS NOT NULL;
    CREATE INDEX idx_event_type ON behavior_events(event_type);
    CREATE INDEX idx_created_at ON behavior_events(created_at DESC);
);

-- Visitors (anonymous tracking)
CREATE TABLE visitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR,
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now()
);

-- Sessions (browser tabs)
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id UUID NOT NULL,
    started_at TIMESTAMP DEFAULT now(),
    ended_at TIMESTAMP,
    
    FOREIGN KEY (visitor_id) REFERENCES visitors(id)
);

-- Identity (visitor → customer)
CREATE TABLE customer_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL UNIQUE,
    email VARCHAR UNIQUE,
    phone VARCHAR UNIQUE,
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Profile (single customer view)
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL UNIQUE,
    
    -- Identity
    email VARCHAR,
    phone VARCHAR,
    
    -- Metrics
    lifetime_value NUMERIC(12,2) DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    average_order_value NUMERIC(12,2) DEFAULT 0,
    
    -- Timeline
    first_seen TIMESTAMP,
    first_purchase TIMESTAMP,
    last_purchase TIMESTAMP,
    last_activity TIMESTAMP,
    days_since_last_activity INTEGER,
    
    -- Engagement
    page_views INTEGER DEFAULT 0,
    product_views INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    
    -- Segment (simple rule in profile)
    segment VARCHAR DEFAULT 'prospect',  -- prospect, first_time, repeat, vip, at_risk
    
    -- Health
    health_score INTEGER DEFAULT 0,
    
    -- AI (optional, can be NULL)
    churn_probability FLOAT,
    predicted_reorder_days INTEGER,
    
    generated_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_customer_id ON customer_profiles(customer_id);
    CREATE INDEX idx_segment ON customer_profiles(segment);
    CREATE INDEX idx_ltv ON customer_profiles(lifetime_value DESC);
);

-- Timeline (generated, human-readable)
CREATE TABLE customer_activity_feed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL,
    
    action VARCHAR NOT NULL,  -- viewed_product, added_to_cart, purchased
    display_text TEXT NOT NULL,  -- "Viewed Black Pepper", "Purchased ₹899"
    context JSONB,  -- {product_id, product_name, price}
    
    behavior_event_id UUID,
    order_id VARCHAR,
    
    created_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_customer_id ON customer_activity_feed(customer_id, created_at DESC);
);
```

**That's it. 6 tables. Everything else flows from these.**

---

### What's NOT Needed Yet

❌ **products table** — Store product_id in event_data, link at query time  
❌ **orders table** — Modify existing crm_orders instead  
❌ **daily_metrics** — Query PostgreSQL directly for now  
❌ **ai_recommendations** — Premature, add in Sprint 5  
❌ **collections** — Premature, add in Sprint 6  
❌ **product_attributes** — Premature, add in Sprint 6  

**Add these only when:**
- Products become a first-class feature
- Order logic gets complex (returns, refunds, partial fulfillment)
- You have 100k+ events/day

---

## Core Services (Minimal)

### Service 1: Event Service

```python
# domains/tracking/event_service.py

from shared.events.event_schemas import EventValidator

def create_behavior_event(
    db: Session,
    event_type: str,
    event_data: dict,
    visitor_id: str = None,
    customer_id: str = None,
    session_id: str = None,
    utm_source: str = None,
    utm_medium: str = None,
    utm_campaign: str = None,
    gclid: str = None,
    fbclid: str = None,
    ip_address: str = None,
    user_agent: str = None
) -> dict:
    """
    Create behavior event.
    Validate, store, dispatch to identity/profile services.
    """
    
    # Validate event
    if not EventValidator.validate(event_type, event_data):
        raise ValueError(f"Invalid event: {event_type}")
    
    event = BehaviorEvent(
        event_type=event_type,
        event_data=event_data,
        visitor_id=visitor_id,
        customer_id=customer_id,
        session_id=session_id,
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        gclid=gclid,
        fbclid=fbclid,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(event)
    db.flush()
    
    # Immediately dispatch to identity/profile
    from domains.customers.identity_service import resolve_identity
    from domains.customers.profile_service import mark_profile_dirty
    from domains.tracking.activity_feed_service import create_activity
    
    if customer_id:
        # Mark profile dirty (background worker rebuilds in 5-30s)
        mark_profile_dirty(db, customer_id)
        
        # Create activity feed entry (immediate, for timeline)
        create_activity(db, event.id, customer_id, event_type, event_data)
    
    db.commit()
    
    return {"event_id": str(event.id), "created_at": event.created_at}
```

**Key:** No dispatcher, no abstraction. Direct calls, real-time profile updates.

---

### Service 2: Identity Service (Priority-Based Matching)

```python
# domains/customers/identity_service.py

# IDENTITY MATCHING PRIORITY (documented)
# 1. Email (primary, highest confidence)
# 2. Phone (secondary)
# 3. Shopify Customer ID (future)
# 4. Visitor ID (fallback, lowest confidence)

def resolve_identity(
    db: Session,
    email: str = None,
    phone: str = None,
    shopify_customer_id: str = None,
    visitor_id: str = None
) -> str:
    """
    Link visitor → customer using priority matching.
    Returns customer_id (UUID).
    """
    
    customer_id = None
    identity = None
    
    # 1. Check email (primary)
    if email:
        identity = db.query(CustomerIdentity).filter(
            CustomerIdentity.email == email
        ).first()
        if identity:
            customer_id = identity.customer_id
    
    # 2. Check phone (if no email match)
    if not customer_id and phone:
        identity = db.query(CustomerIdentity).filter(
            CustomerIdentity.phone == phone
        ).first()
        if identity:
            customer_id = identity.customer_id
    
    # 3. Check Shopify customer ID (future, placeholder)
    # if not customer_id and shopify_customer_id:
    #     identity = db.query(CustomerIdentity).filter(...).first()
    
    # Create or update
    if customer_id:
        # Update existing identity
        identity.last_seen = datetime.now()
        if email and not identity.email:
            identity.email = email
        if phone and not identity.phone:
            identity.phone = phone
    else:
        # Create new customer
        customer = Customer(
            id=str(uuid.uuid4()),
            email=email,
            phone=phone,
            created_at=datetime.now()
        )
        db.add(customer)
        db.flush()
        
        customer_id = customer.id
        
        # Create identity
        identity = CustomerIdentity(
            customer_id=customer_id,
            email=email,
            phone=phone,
            visitor_id=visitor_id
        )
        db.add(identity)
    
    db.commit()
    
    # Link all events from this visitor to customer
    if visitor_id and customer_id:
        db.query(BehaviorEvent).filter(
            BehaviorEvent.visitor_id == visitor_id,
            BehaviorEvent.customer_id.is_(None)
        ).update({BehaviorEvent.customer_id: customer_id})
        db.commit()
    
    return customer_id
```

---

### Service 3: Profile Service (Background Queue, 5-30s Debounce)

**Pattern:** Mark dirty on event → Background worker rebuilds (not every event).

```python
# domains/customers/profile_service.py

def mark_profile_dirty(db: Session, customer_id: str):
    """Mark profile for rebuild, no immediate update."""
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if profile:
        profile.dirty = True
        db.commit()
    else:
        profile = CustomerProfile(customer_id=customer_id, dirty=True)
        db.add(profile)
        db.commit()


@celery_app.task(bind=True, rate_limit="10000/m")
def rebuild_profile(self, customer_id: str):
    """
    Background task: Rebuild customer profile (5-30s after last event).
    Queries all events + orders, recalculates metrics once.
    Real-time feel, not overloaded.
    """
    db = SessionLocal()
    
    try:
        # Get events for this customer
        events = db.query(BehaviorEvent).filter(
            BehaviorEvent.customer_id == customer_id
        ).all()
        
        # Get identity & orders
        identity = db.query(CustomerIdentity).filter(
            CustomerIdentity.customer_id == customer_id
        ).first()
        
        orders = []
        if identity and identity.email:
            orders = db.query(CrmOrder).filter(
                CrmOrder.email == identity.email
            ).all()
        
        # Calculate metrics
        ltv = sum(o.total_amount for o in orders) if orders else 0.0
        total_orders = len(orders)
        avg_order_value = ltv / total_orders if total_orders > 0 else 0.0
        
        page_views = len([e for e in events if e.event_type == "page_view"])
        product_views = len([e for e in events if e.event_type == "product_view"])
        total_events = len(events)
        
        first_seen = min(e.created_at for e in events) if events else None
        last_activity = max(e.created_at for e in events) if events else None
        first_purchase = min(o.created_at for o in orders) if orders else None
        last_purchase = max(o.created_at for o in orders) if orders else None
        
        # Health score
        health_score = 0
        if total_orders > 0:
            health_score += 25
        if total_events > 5:
            health_score += 25
        if avg_order_value > 500:
            health_score += 25
        if not last_activity or (datetime.now() - last_activity).days < 30:
            health_score += 25
        
        # Segment (simple rules)
        segment = "prospect"
        if total_orders > 0:
            if ltv > 5000:
                segment = "vip"
            elif total_orders > 1:
                segment = "repeat"
            else:
                segment = "first_time"
        elif last_activity and (datetime.now() - last_activity).days > 60:
            segment = "at_risk"
        
        # Find or create profile
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer_id
        ).first()
        
        if not profile:
            profile = CustomerProfile(customer_id=customer_id)
            db.add(profile)
        
        # Update fields (store only what's stable, compute rest at API)
        profile.email = identity.email if identity else None
        profile.phone = identity.phone if identity else None
        profile.lifetime_value = ltv
        profile.total_orders = total_orders
        profile.average_order_value = avg_order_value
        profile.first_seen = first_seen
        profile.first_purchase = first_purchase
        profile.last_purchase = last_purchase
        profile.last_activity = last_activity  # Store ONLY this
        # DO NOT store days_since_last_activity (calculate at API layer)
        profile.page_views = page_views
        profile.product_views = product_views
        profile.total_events = total_events
        profile.segment = segment
        profile.health_score = health_score
        profile.dirty = False
        profile.generated_at = datetime.now()
        
        db.commit()
    finally:
        db.close()
```

**Key:** Event marks dirty → Celery debounces → Profile rebuilds once, not N times.

---

### Service 4: Activity Feed Service

```python
# domains/tracking/activity_formatter.py
# (Separate module, keeps activity_feed_service clean)

def format_display_text(event_type: str, event_data: dict) -> tuple[str, str]:
    """
    Map raw event → human-readable display_text + action.
    Centralized rules, reusable.
    """
    
    if event_type == "page_view":
        return "viewed_page", f"Viewed {event_data.get('page_title', 'Page')}"
    
    elif event_type == "product_view":
        product_name = event_data.get("product_name", "Product")
        return "viewed_product", f"Viewed {product_name} Product"
    
    elif event_type == "add_to_cart":
        product_name = event_data.get("product_name", "Product")
        return "added_to_cart", f"Added {product_name} to Cart"
    
    elif event_type == "purchase":
        amount = event_data.get("amount", 0)
        return "purchased", f"Purchased ₹{amount:.0f}"
    
    return None, None


# domains/tracking/activity_feed_service.py

from domains.tracking.activity_formatter import format_display_text

def create_activity(
    db: Session,
    event_id: str,
    customer_id: str,
    event_type: str,
    event_data: dict
):
    """
    Create timeline entry.
    Store event_id + event_type for future debugging ("Open Raw Event").
    """
    
    action, display_text = format_display_text(event_type, event_data)
    
    if not display_text:
        return
    
    activity = CustomerActivityFeed(
        customer_id=customer_id,
        event_id=event_id,              # NEW: Store for debugging
        event_type=event_type,          # NEW: Store for filtering
        action=action,
        display_text=display_text,
        context=event_data,
        created_at=datetime.now()
    )
    
    db.add(activity)
    db.commit()
```

**Key:** Formatter rules separated, activity_feed_service stays small, event_id stored for debugging.

---

## Customer 360 API (The Center)

```python
# api/v1/customers.py

@router.get("/customers")
async def search_customers(q: str, db: Session = Depends(get_db)):
    """Search customers by email or name"""
    
    customers = db.query(CustomerProfile).filter(
        (CustomerProfile.email.ilike(f"%{q}%")) |
        (CustomerProfile.phone.ilike(f"%{q}%"))
    ).limit(20).all()
    
    return [
        {
            "customer_id": c.customer_id,
            "email": c.email,
            "phone": c.phone,
            "lifetime_value": c.lifetime_value,
            "total_orders": c.total_orders,
            "segment": c.segment,
            "health_score": c.health_score
        }
        for c in customers
    ]


@router.get("/customers/{customer_id}")
async def get_customer_360(customer_id: str, db: Session = Depends(get_db)):
    """
    Get complete customer view.
    This API is the CENTER of everything.
    """
    
    # Profile
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404)
    
    # Timeline
    timeline = db.query(CustomerActivityFeed).filter(
        CustomerActivityFeed.customer_id == customer_id
    ).order_by(CustomerActivityFeed.created_at.desc()).limit(100).all()
    
    # Orders
    orders = db.query(CrmOrder).filter(
        CrmOrder.email == profile.email
    ).order_by(CrmOrder.created_at.desc()).all()
    
    # Predictions (optional, added later)
    predictions = None  # Will add in Sprint 5
    
    return {
        "profile": {
            "email": profile.email,
            "phone": profile.phone,
            "lifetime_value": profile.lifetime_value,
            "total_orders": profile.total_orders,
            "average_order_value": profile.average_order_value,
            "segment": profile.segment,
            "health_score": profile.health_score,
            "first_seen": profile.first_seen,
            "first_purchase": profile.first_purchase,
            "last_purchase": profile.last_purchase,
            "last_activity": profile.last_activity,
            "days_since_last_activity": (datetime.now() - profile.last_activity).days if profile.last_activity else None
        },
        "timeline": [
            {
                "event_id": t.event_id,
                "event_type": t.event_type,
                "action": t.action,
                "display_text": t.display_text,
                "context": t.context,
                "created_at": t.created_at
            }
            for t in timeline
        ],
        "orders": [
            {
                "order_id": o.shopify_order_id,
                "amount": o.total_amount,
                "created_at": o.created_at,
                "status": o.payment_status
            }
            for o in orders
        ],
        "predictions": predictions
    }
```

**Search Strategy v1 (PostgreSQL ILIKE):**
```python
db.query(CustomerProfile).filter(
    (CustomerProfile.email.ilike(f"%{q}%")) |
    (CustomerProfile.phone.ilike(f"%{q}%"))
).limit(20)
```
Add indexes on email, phone columns. If search becomes bottleneck (> 100ms), upgrade to full-text search (PostgreSQL tsvector) in v2.

**Key:** This API is the foundation for Customer 360 UI, WhatsApp, automation, everything.

---

## Integration: How New System Connects to Existing System

### Existing Tables (KEEP, No Changes)
- `crm_orders` — Shopify orders, source of truth
- `crm_customers` — Customer dedup by email
- `tracking_events` — Audit log of tracking attempts

### New Tables (CREATE)
- `behavior_events` — New event stream
- `visitors` — Anonymous tracking
- `sessions` — Browser sessions
- `customer_identities` — Link email/phone → customer
- `customer_profiles` — Computed customer state
- `customer_activity_feed` — Generated timeline

### Data Flow: No Duplication

**Shopify Webhook → Both Systems:**
```
Shopify Order
  ↓
crm_orders (existing, no change)
  ↓
behavior_events (new, "purchase" event)
  ↓
customer_identities (new, resolve email → customer)
  ↓
customer_profiles (new, rebuild via Celery)
  ↓
customer_activity_feed (new, "Purchased ₹899")
```

**Browser Attribution → New System:**
```
crm-attribution.js (existing)
  ↓
Stores: gclid, fbclid, utm_* in localStorage
  ↓
POST /api/crm/identify (existing)
  ↓
NEW: Also emit behavior_events
  (page_view, product_view, add_to_cart)
```

**Customer 360 API: Queries Both Systems**
```python
# No data duplication
profile = CustomerProfile (new)
orders = CrmOrder (old, linked by email)
timeline = CustomerActivityFeed (new)
predictions = Profile AI fields (new)
```

### No ETL, No Migration
- Existing crm_orders stays as-is
- Existing crm_customers stays as-is
- New tables are separate
- Link at query time via email
- Keep both systems until you're confident in new one

---

## 7-Phase Implementation (Minimal, Executable)

### Sprint 0: Infrastructure (Week 1)

**Build:**
- Redis, Celery (for future async jobs)
- Folder structure
- Database session management
- Migrations framework

**Outcome:** ✅ Ready to code

---

### Sprint 1: Events Foundation (Week 2)

**Create:**
- behavior_events table
- visitors table
- sessions table
- event_service.py (validation only)

**Update:**
- crm_routes.py: POST /api/events endpoint
- crm-attribution.js: Emit page_view, product_view, add_to_cart

**Test:**
- Events flowing in
- Visitors registered

**Outcome:** ✅ Event system live

---

### Sprint 2: Identity Service (Week 3)

**Create:**
- customer_identities table
- identity_service.py
- POST /api/customers/identify endpoint

**Test:**
- Visitors linked to customers
- Email resolution working

**Outcome:** ✅ Who is this? (answered)

---

### Sprint 3: Profiles + Timeline (Week 4)

**Create:**
- customer_profiles table (with `last_activity`, not `days_since`)
- customer_activity_feed table (with `event_id`, `event_type`)
- profile_service.py (with mark_profile_dirty + Celery rebuild_profile task)
- activity_formatter.py (display text rules)
- activity_feed_service.py (clean, uses formatter)

**Setup:**
- Celery beat task to rebuild dirty profiles every 5-30s

**Test:**
- Events mark profiles dirty
- Celery rebuilds profiles
- Timeline visible in < 30s
- days_since_last_activity calculated at API layer

**Outcome:** ✅ Real-time feel + Background queue + Timeline visible

---

### Sprint 4: Customer 360 UI (Week 5)

**Create:**
- GET /api/customers (search)
- GET /api/customers/{id} (360 view)
- Frontend: CustomerListPage, CustomerDetailPage

**Tabs:**
- Overview (profile, segment, health)
- Timeline (activity feed)
- Orders
- Insights (empty for now)

**Test:**
- Search works
- Timeline renders
- Mobile responsive

**Outcome:** ✅ See everything, feel progress

---

### Sprint 5: Predictions (Week 6)

**Add to customer_profiles:**
- churn_probability
- predicted_reorder_days

**Create:**
- Simple rules in profile_service

**Update:**
- GET /api/customers/{id} includes predictions

**Test:**
- Predictions calculated
- UI displays predictions

**Outcome:** ✅ Predict next step

---

### Sprint 6: Communications (Stub) (Week 7)

**Create:**
- domains/communications/ folder structure
- models.py (stub)
- api.py (stub)

**Status:** Empty, ready for WhatsApp integration

---

### (Future) Sprint 7: Automation (Stub)

**Create:**
- domains/automation/ folder structure
- models.py (stub)
- api.py (stub)

**Status:** Empty, ready for workflows

---

## What This Avoids

❌ **Event dispatcher** — Too abstract, not needed yet  
❌ **Products domain** — Not a first-class feature  
❌ **Orders domain** — Modify existing crm_orders  
❌ **Segmentation service** — Just rules in profile  
❌ **Recommendations** — Too early, no data  
❌ **Data warehouse** — Query PostgreSQL directly  
❌ **Admin APIs** — Not separate, just the customer 360 API  
❌ **Schema registry** — Validation in code only  

---

## After Sprint 6: What You Have

✅ **Identity** — Know WHO your customers are  
✅ **Profile** — Know WHAT their story is (real-time)  
✅ **Timeline** — Know WHAT they did (human-readable)  
✅ **UI** — See everything in Customer 360  
✅ **Predictions** — Know WHAT happens next  
✅ **Future-ready** — Communications + Automation stubs ready  

**Total effort:** 6 weeks (not 12), 1 engineer, ship something real.

---

## Why This Works Better

| What | Original Plan | Optimized |
|------|---|---|
| Complexity | 12 tables, 8 services, 12 weeks | 6 tables, 3 services, 6 weeks |
| Visible results | Week 12 | Week 4 |
| Risk | High (too much to test) | Low (focused, simple) |
| Future-ready | Overengineered (adds bloat) | Stub-ready (adds value) |
| Real-time | Delayed (5 min batches) | Background queue (5-30s debounce) |
| First-class API | Too many endpoints | Single Customer 360 API |

---

## Critical Success Factors

1. **Identity first** — Everything depends on knowing WHO
2. **Real-time profiles** — No delayed projection jobs
3. **Timeline visibility** — See human-readable history in Week 4
4. **Single API** — GET /api/customers/{id} is the foundation
5. **UI early** — See progress in Week 5, not Week 12

---

## Migration Strategy: Old System ↔ New System (CRITICAL)

**Principle:** No duplication. No big ETL. Keep both, link at query time.

### Existing Tables (KEEP AS-IS)

| Table | Status | Why |
|-------|--------|-----|
| crm_orders | Keep | Source of truth for orders |
| crm_customers | Keep | Source of truth for customer dedup |
| tracking_events | Keep | Audit log remains |

**No refactoring, no migration.** These tables continue working exactly as they do now.

### New Tables (CREATE SEPARATE)

| Table | Created In | Purpose |
|-------|-----------|---------|
| behavior_events | Sprint 1 | New event stream (page_view, product_view, purchase) |
| visitors | Sprint 1 | Anonymous visitor tracking |
| sessions | Sprint 1 | Browser session tracking |
| customer_identities | Sprint 2 | Email/phone → customer linking |
| customer_profiles | Sprint 3 | Computed customer metrics + segment + health |
| customer_activity_feed | Sprint 3 | Generated human-readable timeline |

### Integration Points (No ETL Pipeline)

**1. Shopify Webhook → Both Systems**

```
Existing: Shopify → crm_routes.py → crm_orders (working now)
New:      Shopify → crm_routes.py → behavior_events (new)
```

In crm_routes.py, after storing in crm_orders:
```python
# Emit behavior_events
emit_purchase_event(
    customer_id=customer_email,  # Link by email
    event_type="purchase",
    event_data={"order_id": order_id, "amount": total}
)
```

**2. Browser Attribution → New System**

```
Existing: crm-attribution.js → /api/crm/identify
New:      crm-attribution.js → behavior_events (page_view, product_view, add_to_cart)
```

Update crm-attribution.js to emit events on user interactions.

**3. Customer 360 API → Queries Both**

```python
@router.get(\"/api/customers/{customer_id}\")
def get_customer_360(customer_id: str):
    # Profile from NEW system
    profile = db.query(CustomerProfile).get(customer_id)
    
n    # Orders from OLD system
    orders = db.query(CrmOrder).filter(
        CrmOrder.email == profile.email
    ).all()
    
    # Timeline from NEW system
    timeline = db.query(CustomerActivityFeed).filter(
        CustomerActivityFeed.customer_id == customer_id
    ).all()
    
    return {profile, timeline, orders, predictions}
```

**Zero duplication. Query across both tables.**

### Identity Linking: Keep crm_customers, Don't Duplicate

**Pattern:**
```
customer_identities (NEW) links email → customer_id
customer_id is UUID in customer_profiles (NEW)

DO NOT duplicate customer records from crm_customers
Keep crm_customers as existing source, reference at query time
```

### Data Consistency: Sequential-Only Guarantee

When Shopify order arrives:
1. Store in `crm_orders` (existing, fast)
2. Emit `behavior_events` (new, fast)
3. Identity service resolves `email → customer_id` (eventually consistent, < 5s)
4. Profile rebuild queued (eventually consistent, < 30s)
5. Timeline created (eventually consistent, < 30s)

**Not ACID across systems, but sequential within each system.**

### Rollback Plan

If new system fails:
- Keep using `crm_orders` + `crm_customers` + old tracking (unchanged)
- Delete `behavior_events` + `customer_profiles` + new tables
- No data loss, no customer impact

### Validation Phase (Week 8, Post Sprint 6)

After deploying Sprint 6:
1. Run both systems in parallel for 1 week
2. Compare: crm_orders vs behavior_events (purchase count, totals)
3. Compare: crm_customers vs customer_profiles (counts, metrics)
4. If 100% match, proceed; otherwise debug and fix
5. Deprecate old system only after 4-week parallel run

---

## Expansion Path (After Sprint 6)

**If you need more:**

- **Sprint 7:** Order domain (returns, refunds, partial fulfillment) — only if needed
- **Sprint 8:** Product domain (attributes, collections) — only if needed
- **Sprint 9:** Recommendation engine — only after 1000+ purchases
- **Sprint 10:** WhatsApp integration (domain ready)
- **Sprint 11:** Automation engine (domain ready)
- **Sprint 12+:** Whatever comes next

**But you don't start here.** You start with identity → profile → timeline → UI.

