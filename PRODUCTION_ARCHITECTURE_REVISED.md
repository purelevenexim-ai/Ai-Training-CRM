# Pureleven Intelligence Platform — Production-Ready Architecture

**Status:** Revised for Production  
**Approach:** Lean, focused, service-first  
**Timeline:** 11 phases (Sprint 0 + Sprints 1-10), 11 weeks  
**Philosophy:** Build only what you need. Avoid premature complexity.

---

## Why the Original Plan Was Over-Engineered

❌ **Multi-tenant on day 1** — Adds complexity to every query, index, service (Pureleven only)  
❌ **No product model** — Events reference product_id as string, not proper records  
❌ **Predictions in profiles** — AI changes frequently, profile should stay stable  
❌ **Events mixed together** — Behavior (page_view) mixed with system (task_created)  
❌ **No data warehouse** — Dashboards querying millions of events directly  
❌ **Database-first thinking** — Should be service-first

---

## Revised Architecture: Lean & Focused

### Core Principle: Service-First, Not Database-First

**5 Core Services:**
1. **Event Service** — Validate, store, publish events
2. **Identity Service** — Link visitor → customer
3. **Profile Service** — Generate customer projections
4. **Segmentation Service** — VIP, at-risk, wholesale
5. **Prediction Service** — Lead score, churn, recommendations

**Tables are outputs of services, not the architecture.**

---

## Data Model: Simplified, Product-Aware

### Layer 1: Company Settings (Not Multi-Tenant)

```sql
CREATE TABLE platform_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR DEFAULT 'Pureleven',
    
    created_at TIMESTAMP DEFAULT now()
);

-- Single row table: INSERT VALUES only once
```

**Why:** When/if onboarding Brand B, you create migration v2 that adds tenant_id everywhere. Not day 1 complexity.

---

### Layer 2: Product Catalog (Critical, Missing Before)

```sql
CREATE TABLE products (
    id VARCHAR PRIMARY KEY,  -- pepper_200g, cardamom_100g
    
    name VARCHAR NOT NULL,
    category VARCHAR,  -- Pepper, Cardamom, Spices
    price_inr NUMERIC(12,2),
    
    -- Inventory
    stock_available INTEGER DEFAULT 0,
    reorder_point INTEGER DEFAULT 10,
    
    -- Metrics
    total_sold INTEGER DEFAULT 0,
    revenue_total NUMERIC(12,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_category ON products(category);
CREATE INDEX idx_price ON products(price_inr);


CREATE TABLE product_categories (
    id VARCHAR PRIMARY KEY,  -- pepper, cardamom, spices
    name VARCHAR NOT NULL,
    description TEXT,
    
    created_at TIMESTAMP DEFAULT now()
);


CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    order_id VARCHAR NOT NULL,  -- FK to crm_orders
    product_id VARCHAR NOT NULL,  -- FK to products
    
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (order_id) REFERENCES crm_orders(shopify_order_id)
);

CREATE INDEX idx_order_id ON order_items(order_id);
CREATE INDEX idx_product_id ON order_items(product_id);
```

**Why:** Enables product insights (top sellers, frequently bought together, recommendations).

---

### Layer 3: Event Stream (Separated)

**Two event tables: behavior + system**

```sql
CREATE TABLE behavior_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event
    event_type VARCHAR NOT NULL,  -- page_view, product_view, add_to_cart, purchase
    event_data JSONB,
    
    -- Who
    visitor_id UUID,
    customer_id VARCHAR,
    session_id UUID,
    
    -- Attribution
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    gclid VARCHAR,
    fbclid VARCHAR,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP DEFAULT now(),
    
    CREATE INDEX idx_customer_id ON behavior_events(customer_id) WHERE customer_id IS NOT NULL;
    CREATE INDEX idx_event_type ON behavior_events(event_type);
    CREATE INDEX idx_created_at ON behavior_events(created_at DESC);
);

CREATE TABLE system_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event
    event_type VARCHAR NOT NULL,  -- automation_executed, task_created, profile_generated
    event_data JSONB,
    
    -- Associated entities
    customer_id VARCHAR,
    automation_id VARCHAR,
    
    created_at TIMESTAMP DEFAULT now(),
    
    CREATE INDEX idx_customer_id ON system_events(customer_id);
    CREATE INDEX idx_event_type ON system_events(event_type);
);
```

**Why:** Keeps AI models clean (only behavior), doesn't pollute with task/automation noise.

---

### Layer 4: Visitor & Session

```sql
CREATE TABLE visitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    customer_id VARCHAR,  -- Linked later
    
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    device_id VARCHAR,
    ip_address INET
);

CREATE INDEX idx_customer_id ON visitors(customer_id) WHERE customer_id IS NOT NULL;


CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id UUID NOT NULL,
    
    started_at TIMESTAMP DEFAULT now(),
    ended_at TIMESTAMP,
    
    landing_page VARCHAR,
    exit_page VARCHAR,
    referrer VARCHAR,
    
    FOREIGN KEY (visitor_id) REFERENCES visitors(id)
);

CREATE INDEX idx_visitor_id ON sessions(visitor_id);
```

---

### Layer 5: Identity Resolution

```sql
CREATE TABLE customer_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL UNIQUE,
    
    email VARCHAR UNIQUE,
    phone VARCHAR UNIQUE,
    shopify_customer_id VARCHAR UNIQUE,
    
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX idx_customer_id ON customer_identities(customer_id);
CREATE INDEX idx_email ON customer_identities(email);
```

---

### Layer 6: Customer Profile (Stable, No AI)

```sql
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
    
    -- Preferences
    favorite_product_id VARCHAR,
    favorite_category VARCHAR,
    
    -- Segment (generated by segmentation service)
    segment VARCHAR,  -- vip, standard, at_risk, wholesale, etc
    
    -- Health (0-100, simple rule-based)
    health_score INTEGER DEFAULT 0,
    
    generated_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_customer_id ON customer_profiles(customer_id);
    CREATE INDEX idx_ltv ON customer_profiles(lifetime_value DESC);
    CREATE INDEX idx_health ON customer_profiles(health_score DESC);
    CREATE INDEX idx_segment ON customer_profiles(segment);
);
```

**No AI fields. No predictions. Just stable identity + metrics.**

---

### Layer 7: Predictions (Separate, Mutable)

```sql
CREATE TABLE customer_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL,
    
    -- AI Scores (can be recalculated frequently)
    lead_score INTEGER,
    churn_probability FLOAT,
    
    -- Predictions
    predicted_reorder_date DATE,
    predicted_reorder_days INTEGER,
    predicted_next_purchase_value NUMERIC(12,2),
    
    -- Reason/explanation
    prediction_reason TEXT,
    
    generated_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_customer_id ON customer_predictions(customer_id);
    CREATE INDEX idx_lead_score ON customer_predictions(lead_score DESC);
    CREATE INDEX idx_churn ON customer_predictions(churn_probability DESC);
);
```

**Separate from profiles. Can change rapidly. AI models own this table.**

---

### Layer 8: Data Warehouse (Daily Aggregates)

```sql
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_date DATE NOT NULL,
    
    -- Traffic
    page_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    
    -- Conversion
    add_to_cart_count INTEGER DEFAULT 0,
    purchases_count INTEGER DEFAULT 0,
    revenue_total NUMERIC(12,2) DEFAULT 0,
    
    -- Funnel
    conversion_rate FLOAT DEFAULT 0,
    atc_rate FLOAT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_metric_date ON daily_metrics(metric_date DESC);


CREATE TABLE daily_customer_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_date DATE NOT NULL,
    customer_id VARCHAR NOT NULL,
    
    -- Daily activity
    page_views INTEGER DEFAULT 0,
    product_views INTEGER DEFAULT 0,
    added_to_cart BOOLEAN DEFAULT FALSE,
    purchased BOOLEAN DEFAULT FALSE,
    
    purchase_amount NUMERIC(12,2),
    
    created_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_customer_date ON daily_customer_metrics(customer_id, metric_date DESC);
);


CREATE TABLE daily_product_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_date DATE NOT NULL,
    product_id VARCHAR NOT NULL,
    
    -- Daily activity
    views INTEGER DEFAULT 0,
    added_to_cart INTEGER DEFAULT 0,
    sold INTEGER DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (product_id) REFERENCES products(id),
    
    CREATE INDEX idx_product_date ON daily_product_metrics(product_id, metric_date DESC);
);
```

**Generated nightly. Dashboards query here, not raw events.**

---

## Core Services (Service-First Architecture)

### Service 1: Event Service

**Responsibility:** Validate, store, publish behavior events

```python
# app/services/event_service.py

def create_behavior_event(
    db: Session,
    event_type: str,
    event_data: dict = None,
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
    Validates against allowed event types.
    """
    
    # Validate event type
    ALLOWED_EVENTS = [
        "page_view",
        "product_view",
        "add_to_cart",
        "begin_checkout",
        "purchase",
        "home_page"
    ]
    
    if event_type not in ALLOWED_EVENTS:
        raise ValueError(f"Invalid event type: {event_type}")
    
    event = BehaviorEvent(
        event_type=event_type,
        event_data=event_data or {},
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
    db.commit()
    
    return {
        "event_id": str(event.id),
        "event_type": event_type,
        "created_at": event.created_at
    }


def create_system_event(db: Session, event_type: str, event_data: dict, customer_id: str = None):
    """Create system event (automation, tasks, etc)"""
    
    ALLOWED_SYSTEM_EVENTS = [
        "automation_executed",
        "task_created",
        "profile_generated",
        "prediction_updated"
    ]
    
    if event_type not in ALLOWED_SYSTEM_EVENTS:
        raise ValueError(f"Invalid system event type: {event_type}")
    
    event = SystemEvent(
        event_type=event_type,
        event_data=event_data or {},
        customer_id=customer_id
    )
    
    db.add(event)
    db.commit()
```

---

### Service 2: Identity Service

**Responsibility:** Resolve visitor → customer

```python
# app/services/identity_service.py

def resolve_identity(
    db: Session,
    email: str = None,
    phone: str = None,
    visitor_id: str = None,
    session_id: str = None
) -> str:
    """
    Link visitor to customer.
    Returns customer_id.
    """
    
    customer_id = None
    
    # Check if email exists
    if email:
        identity = db.query(CustomerIdentity).filter(
            CustomerIdentity.email == email
        ).first()
        if identity:
            customer_id = identity.customer_id
    
    # Create or update
    if customer_id:
        # Update existing
        identity.last_seen = datetime.now()
    else:
        # Check if customer exists
        customer = None
        if email:
            customer = db.query(Customer).filter(Customer.email == email).first()
        
        if not customer:
            customer = Customer(id=str(uuid.uuid4()), email=email, phone=phone)
            db.add(customer)
            db.flush()
        
        customer_id = customer.id
        
        # Create identity
        identity = CustomerIdentity(
            customer_id=customer_id,
            email=email,
            phone=phone
        )
        db.add(identity)
    
    db.commit()
    
    # Link all events from this visitor
    if visitor_id and customer_id:
        db.query(BehaviorEvent).filter(
            BehaviorEvent.visitor_id == visitor_id,
            BehaviorEvent.customer_id.is_(None)
        ).update({BehaviorEvent.customer_id: customer_id})
        db.commit()
    
    return customer_id
```

---

### Service 3: Profile Service

**Responsibility:** Generate customer_profiles from events + orders (run every 5 min)

```python
# app/services/profile_service.py

def generate_customer_profile(db: Session, customer_id: str):
    """
    Generate complete customer profile from behavior_events + crm_orders.
    Replaces entire row (always fresh).
    """
    
    # Get events
    events = db.query(BehaviorEvent).filter(
        BehaviorEvent.customer_id == customer_id
    ).all()
    
    # Get orders
    identity = db.query(CustomerIdentity).filter(
        CustomerIdentity.customer_id == customer_id
    ).first()
    
    orders = db.query(CrmOrder).filter(
        CrmOrder.email == identity.email
    ).all() if identity else []
    
    # Calculate metrics
    ltv = sum(o.total_amount for o in orders) if orders else 0
    total_orders = len(orders)
    avg_order_value = ltv / total_orders if total_orders > 0 else 0
    
    # Engagement
    page_views = len([e for e in events if e.event_type == "page_view"])
    product_views = len([e for e in events if e.event_type == "product_view"])
    total_events = len(events)
    
    # Timeline
    first_seen = min(e.created_at for e in events) if events else None
    last_activity = max(e.created_at for e in events) if events else None
    first_purchase = min(o.order_date for o in orders) if orders else None
    last_purchase = max(o.order_date for o in orders) if orders else None
    
    days_since_activity = (datetime.now() - last_activity).days if last_activity else None
    
    # Health score (simple rule-based)
    health_score = 0
    if total_orders > 0:
        health_score += 25
    if total_events > 5:
        health_score += 25
    if avg_order_value > 500:
        health_score += 25
    if not days_since_activity or days_since_activity < 30:
        health_score += 25
    
    # Favorite product
    favorite_product = None
    if orders:
        order_items = db.query(OrderItem).filter(
            OrderItem.order_id.in_([o.shopify_order_id for o in orders])
        ).all()
        if order_items:
            product_counts = {}
            for oi in order_items:
                product_counts[oi.product_id] = product_counts.get(oi.product_id, 0) + 1
            favorite_product = max(product_counts, key=product_counts.get)
    
    # Update or create profile
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        profile = CustomerProfile(customer_id=customer_id)
        db.add(profile)
    
    profile.email = identity.email if identity else None
    profile.phone = identity.phone if identity else None
    profile.lifetime_value = ltv
    profile.total_orders = total_orders
    profile.average_order_value = avg_order_value
    profile.first_seen = first_seen
    profile.first_purchase = first_purchase
    profile.last_purchase = last_purchase
    profile.last_activity = last_activity
    profile.days_since_last_activity = days_since_activity
    profile.page_views = page_views
    profile.product_views = product_views
    profile.total_events = total_events
    profile.favorite_product_id = favorite_product
    profile.health_score = health_score
    profile.generated_at = datetime.now()
    
    db.commit()
```

---

### Service 4: Segmentation Service

**Responsibility:** Assign customers to segments based on profiles

```python
# app/services/segmentation_service.py

def segment_customer(db: Session, customer_id: str) -> str:
    """
    Assign customer to segment based on metrics.
    Updates customer_profiles.segment field.
    """
    
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        return "unknown"
    
    # Rules (in order)
    if profile.lifetime_value > 10000:
        segment = "vip"
    elif profile.total_orders > 20:
        segment = "wholesale"
    elif profile.average_order_value > 1000:
        segment = "high_value"
    elif profile.days_since_last_activity and profile.days_since_last_activity > 60:
        segment = "at_risk"
    elif profile.total_orders == 1:
        segment = "first_time"
    elif profile.total_orders > 1:
        segment = "repeat"
    else:
        segment = "prospect"
    
    profile.segment = segment
    db.commit()
    
    return segment
```

---

### Service 5: Prediction Service

**Responsibility:** Generate predictions (lead score, churn, reorder date)

```python
# app/services/prediction_service.py

def predict_customer(db: Session, customer_id: str):
    """
    Generate predictions for customer.
    Stores in customer_predictions (separate table).
    """
    
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        return None
    
    # Lead Score (0-100)
    lead_score = 0
    if profile.page_views > 10:
        lead_score += 20
    if profile.product_views > 5:
        lead_score += 20
    if profile.total_events > 20:
        lead_score += 20
    if profile.health_score > 70:
        lead_score += 20
    if profile.total_orders > 0:
        lead_score += 20
    
    # Churn Probability (0-1)
    churn_prob = 0.0
    if profile.days_since_last_activity and profile.days_since_last_activity > 90:
        churn_prob = 0.8
    elif profile.days_since_last_activity and profile.days_since_last_activity > 60:
        churn_prob = 0.5
    elif profile.days_since_last_activity and profile.days_since_last_activity > 30:
        churn_prob = 0.2
    
    # Reorder Prediction (for Pureleven spices, avg reorder ~45 days)
    predicted_reorder_days = None
    if profile.last_purchase:
        avg_reorder_days = 45  # Pureleven average
        days_since = (datetime.now() - profile.last_purchase).days
        if days_since < avg_reorder_days:
            predicted_reorder_days = avg_reorder_days - days_since
        else:
            predicted_reorder_days = avg_reorder_days
    
    # Update or create prediction
    prediction = db.query(CustomerPrediction).filter(
        CustomerPrediction.customer_id == customer_id
    ).first()
    
    if not prediction:
        prediction = CustomerPrediction(customer_id=customer_id)
        db.add(prediction)
    
    prediction.lead_score = lead_score
    prediction.churn_probability = churn_prob
    prediction.predicted_reorder_days = predicted_reorder_days
    prediction.generated_at = datetime.now()
    
    db.commit()
    
    return prediction
```

---

## 11-Phase Implementation (Sprint 0 + Sprints 1-10)

### Sprint 0: Infrastructure Setup (Week 1)

**Goal:** Get infrastructure ready. No business logic.

**What to build:**
- Redis (for caching, queues)
- Celery (for async jobs)
- Sentry (for error tracking)
- Folder structure: `app/services/`
- Docker Compose updates

**No code written. Just infra.**

**Outcome:**
- ✅ Redis running
- ✅ Celery workers ready
- ✅ Sentry configured
- ✅ Service folder structure exists

---

### Sprint 1: Event Foundation + Product Catalog (Week 2)

**Goal:** Event stream + product model

**Create:**
- behavior_events table
- system_events table
- products table
- product_categories table
- order_items table (link orders to products)

**Update:**
- crm_routes.py: Add POST /api/events endpoint
- Shopify webhook: Emit purchase event to behavior_events

**Test:**
- POST /api/events returns 200
- Events in behavior_events table
- Products can be queried

**Outcome:**
- ✅ Event stream live (behavior + system separated)
- ✅ Product catalog exists
- ✅ Orders linked to products

---

### Sprint 2: Visitor & Session Tracking (Week 3)

**Goal:** Know who's anonymous

**Create:**
- visitors table
- sessions table

**Update:**
- crm-attribution.js: Register visitor + session on page load

**Test:**
- Visitors registered
- Sessions created per browser tab
- Session duration tracked

**Outcome:**
- ✅ Anonymous traffic tracked
- ✅ Sessions tracked
- ✅ Device/IP captured

---

### Sprint 3: Event Emission from Browser (Week 4)

**Goal:** Browser emits page_view, product_view, add_to_cart events

**Update:**
- crm-attribution.js: Track page_view, product_view, add_to_cart

**Test:**
- behavior_events table has 100+ events/day
- Event types correct
- Attribution (UTM) captured

**Outcome:**
- ✅ Browser behavior tracked
- ✅ Complete funnel visible
- ✅ Product views captured

---

### Sprint 4: Identity Resolution (Week 5)

**Goal:** Link visitor → customer when email known

**Create:**
- customer_identities table

**Create:**
- identity_service.py

**Update:**
- crm-attribution.js: Call identify endpoint when email entered
- POST /api/customers/identify endpoint

**Test:**
- Visitor linked to customer
- All previous events get customer_id
- Zero duplicate identities

**Outcome:**
- ✅ Visitors → customers linked
- ✅ All events have customer_id
- ✅ Email resolution working

---

### Sprint 5: Customer Profile Generation (Week 6)

**Goal:** Generate customer_profiles

**Create:**
- customer_profiles table
- profile_service.py
- Celery job (every 5 minutes)

**Test:**
- Profiles generated for all customers
- LTV correct
- Health score 0-100
- Engagement metrics correct

**Outcome:**
- ✅ customer_profiles fully populated
- ✅ Profile service running
- ✅ Metrics accurate

---

### Sprint 6: Segmentation (Week 7)

**Goal:** Classify customers (VIP, at-risk, etc.)

**Update:**
- segmentation_service.py
- Profile generation adds segment

**Test:**
- Segments assigned correctly
- Rules working (VIP > ₹10k, etc.)

**Outcome:**
- ✅ Customers segmented
- ✅ VIP/wholesale/at-risk identified

---

### Sprint 7: Predictions (Week 8)

**Goal:** AI predictions (lead score, churn, reorder)

**Create:**
- customer_predictions table
- prediction_service.py

**Test:**
- Lead scores generated (0-100)
- Churn probability (0-1)
- Reorder prediction (days)

**Outcome:**
- ✅ Predictions available
- ✅ Separate from profiles
- ✅ Can iterate on AI models

---

### Sprint 8: Data Warehouse (Week 9)

**Goal:** Fast dashboards

**Create:**
- daily_metrics table
- daily_customer_metrics table
- daily_product_metrics table

**Create:**
- Nightly aggregation job (Celery)

**Test:**
- Aggregates generated nightly
- Dashboard queries < 100ms

**Outcome:**
- ✅ Dashboards fast
- ✅ No slow event queries
- ✅ Historical trends visible

---

### Sprint 9: Customer 360 UI + APIs (Week 10)

**Goal:** First UI (customer-centric, everything attached)

**Create:**
- Backend APIs:
  - GET /api/customers (search)
  - GET /api/customers/{id} (profile + predictions + segment)
  - GET /api/customers/{id}/timeline (behavior_events)
  - GET /api/customers/{id}/orders
  - GET /api/customers/{id}/products (products purchased)

- Frontend:
  - CustomerListPage (search, cards)
  - CustomerDetailPage (single customer view with all tabs)
  - Tabs: Overview | Timeline | Orders | Products | Insights

**Test:**
- Search works
- Timeline shows events
- Orders visible
- Insights show predictions
- Mobile responsive

**Outcome:**
- ✅ Customer 360 UI live
- ✅ Customer-centric, not scattered screens
- ✅ Timeline is central

---

### Sprint 10: Activity Feed (Week 11)

**Goal:** Timeline becomes the source

**Create:**
- Activity feed UI (already have timeline)
- Add context to events (product names, etc.)

**Test:**
- Timeline human-readable
- Shows: "Viewed Pepper", "Added Pepper to Cart", etc.
- Connected to products table

**Outcome:**
- ✅ Timeline becomes central view
- ✅ All context visible (product names, etc.)
- ✅ Foundation for automation/AI

---

## UI Architecture: Customer-Centric

**NOT:**
```
Customers Screen
Leads Screen
WhatsApp Screen
Tasks Screen
```

**YES:**
```
Customer Screen

├── Overview Tab
│   ├── Profile (email, phone, LTV)
│   ├── Segment (VIP, wholesale, at-risk)
│   ├── Health Score
│   └── Predictions (lead score, churn, reorder)
│
├── Timeline Tab
│   └── Activity Feed (Viewed Pepper, Added to Cart, Purchased, etc.)
│
├── Orders Tab
│   └── Purchase History (all orders, dates, amounts)
│
├── Products Tab
│   └── Products Purchased + Reorder Potential
│
└── Insights Tab
    ├── Lead Score Breakdown
    ├── Churn Risk Factors
    ├── Reorder Prediction
    └── Recommendations
```

**Everything in one place. Customer is the center.**

---

## What NOT to Build

❌ Lead Pipeline (separate screen) — Leads are customers with segment='prospect'  
❌ WhatsApp Inbox (separate screen) — WhatsApp is a communication channel, not a system  
❌ Automation UI (separate screen) — Automation is a system event, visible in timeline  
❌ Reports (separate dashboards) — Use data warehouse tables instead  

---

## Key Differences from Original Plan

| Original | Revised | Why |
|----------|---------|-----|
| tenant_id everywhere | platform_settings table | Avoid premature complexity |
| No product model | products + order_items | Enable product insights |
| Predictions in profiles | Separate customer_predictions | Keep profiles stable |
| All events mixed | Behavior vs system separation | Keep AI models clean |
| Query raw events | daily_metrics aggregates | Dashboards stay fast |
| Database-first | Service-first | Services own logic, tables are outputs |
| Separate Leads/WhatsApp/Automation screens | Everything in customer view | Single source of truth |
| Event schema registry table | Simple list in code | YAGNI for current size |
| 4 sprints | 11 phases (more granular) | Better testing + iteration |

---

## Success Metrics

**Sprint 0:** ✅ Infrastructure ready  
**Sprint 1:** ✅ Events + products flowing  
**Sprint 2:** ✅ Visitors tracked  
**Sprint 3:** ✅ Browser behavior captured  
**Sprint 4:** ✅ Identities linked  
**Sprint 5:** ✅ Profiles generated  
**Sprint 6:** ✅ Customers segmented  
**Sprint 7:** ✅ Predictions working  
**Sprint 8:** ✅ Dashboards fast  
**Sprint 9:** ✅ Customer 360 UI live  
**Sprint 10:** ✅ Activity feed complete  

---

## After Sprint 10: What You Have

✅ **Complete customer intel** — Profile + predictions + segment + timeline  
✅ **Product insights** — Top sellers, frequently bought together  
✅ **Fast dashboards** — Aggregates, not raw events  
✅ **Clean architecture** — Services own logic, tables are outputs  
✅ **Production-ready** — Tested incrementally, no rework  

**Total effort:** 11 weeks, 1 full-time engineer.

**Result:** Production intelligence platform. Not over-engineered. Not scattered. **Customer-centric.**

