# Pureleven Customer Intelligence Platform — Final Approved Architecture

**Status:** Architect-Approved for Production  
**Approach:** Domain-driven, service-first, event-dispatcher core  
**Timeline:** 12 phases (Sprint 0 + Sprints 1-11), 12 weeks  
**Philosophy:** Build a Customer Intelligence Platform, not just a CRM.

---

## Core Philosophy

```
Shopify
    ↓
Tracking Layer
    ↓
Behavior Events + System Events
    ↓
Event Dispatcher (core nervous system)
    ↓
Identity Service → Profile Service → Segmentation Service → Prediction Service
    ↓
Customer Activity Feed (human-readable timeline)
    ↓
Customer 360 APIs (stable first, then UI)
    ↓
Customer 360 UI
    ↓
Automation + WhatsApp + AI + Reports (all from one foundation)
```

**Key principle:** Everything flows from events. Everything else is a projection.

---

## Folder Structure: Domain-Driven Architecture

```
app/

├── domains/
│   ├── tracking/
│   │   ├── event_service.py
│   │   ├── event_dispatcher.py
│   │   ├── tracking_repository.py
│   │   └── models.py
│   │
│   ├── customers/
│   │   ├── identity_service.py
│   │   ├── profile_service.py
│   │   ├── segmentation_service.py
│   │   ├── customer_repository.py
│   │   ├── models.py
│   │   └── api.py
│   │
│   ├── orders/
│   │   ├── order_service.py
│   │   ├── order_repository.py
│   │   ├── order_webhooks.py
│   │   ├── models.py
│   │   └── api.py
│   │
│   ├── products/
│   │   ├── product_service.py
│   │   ├── product_repository.py
│   │   ├── models.py
│   │   └── api.py
│   │
│   ├── analytics/
│   │   ├── metrics_service.py
│   │   ├── aggregation_jobs.py
│   │   ├── models.py
│   │   └── api.py
│   │
│   ├── predictions/
│   │   ├── prediction_service.py
│   │   ├── recommendation_service.py
│   │   ├── models.py
│   │   └── api.py
│   │
│   ├── communications/
│   │   ├── messaging_service.py
│   │   ├── channel_router.py
│   │   ├── models.py
│   │   └── api.py  [FUTURE: WhatsApp, Email, SMS, Push]
│   │
│   └── automation/
│       ├── automation_engine.py
│       ├── workflow_service.py
│       ├── trigger_service.py
│       ├── models.py
│       └── api.py  [FUTURE: Workflow builder]
│
├── shared/
│   ├── database/
│   │   ├── models.py (shared SQLAlchemy models)
│   │   ├── session.py
│   │   └── migrations/
│   │
│   ├── events/
│   │   ├── event_types.py (event schema definitions)
│   │   ├── event_validators.py
│   │   └── event_schemas.py
│   │
│   ├── auth/
│   │   ├── auth_service.py
│   │   └── permissions.py
│   │
│   └── utils/
│       ├── logging.py
│       ├── decorators.py
│       └── helpers.py
│
├── api/
│   ├── health.py
│   ├── admin.py (internal admin endpoints)
│   └── v1/
│       ├── customers.py
│       ├── orders.py
│       ├── products.py
│       ├── analytics.py
│       └── predictions.py
│
├── celery_tasks.py
├── settings.py
└── main.py
```

**Why:** As services grow, you scale by domain, not by 4000-line files.

---

## Data Model: Schema Validation + Generated Feeds

### Layer 1: Event Schema (Enforced, Not Free-Form)

```python
# shared/events/event_schemas.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class ProductViewEvent:
    """Required fields for product_view events"""
    product_id: str
    product_name: str
    category: str
    price_inr: float
    timestamp: datetime

@dataclass
class PurchaseEvent:
    """Required fields for purchase events"""
    order_id: str
    amount: float
    currency: str = "INR"
    items_count: int
    timestamp: datetime

@dataclass
class AddToCartEvent:
    """Required fields for add_to_cart events"""
    product_id: str
    product_name: str
    quantity: int
    price_inr: float
    timestamp: datetime

@dataclass
class PageViewEvent:
    """Required fields for page_view events"""
    url: str
    page_title: str
    timestamp: datetime

# Event Validator
class EventValidator:
    """Validate events before storing in behavior_events"""
    
    @staticmethod
    def validate_product_view(event_data: dict) -> bool:
        required = ['product_id', 'product_name', 'category', 'price_inr']
        return all(k in event_data for k in required)
    
    @staticmethod
    def validate_purchase(event_data: dict) -> bool:
        required = ['order_id', 'amount', 'currency']
        return all(k in event_data for k in required)
```

**Why:** JSON chaos is prevented by enforcement, not hope.

---

### Layer 2: Products with Attributes

```sql
CREATE TABLE products (
    id VARCHAR PRIMARY KEY,  -- pepper_200g
    name VARCHAR NOT NULL,
    description TEXT,
    price_inr NUMERIC(12,2),
    
    -- Attributes (for AI/recommendations)
    -- Stored as JSONB for flexibility but structured
    attributes JSONB,  -- {organic: true, premium: true, grade: export}
    
    stock_available INTEGER DEFAULT 0,
    
    total_sold INTEGER DEFAULT 0,
    revenue_total NUMERIC(12,2) DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT now()
);

-- Attributes examples:
-- {organic: true, fair_trade: true, packaging: bulk}
-- {organic: false, conventional: true, origin: vietnam}
-- {grade: premium, export_quality: true, year_harvested: 2024}


CREATE TABLE collections (
    id VARCHAR PRIMARY KEY,  -- spices, organic_only, bulk_discount
    name VARCHAR NOT NULL,
    description TEXT,
    
    created_at TIMESTAMP DEFAULT now()
);

-- collections examples:
-- Spices, Organic, Premium, Export Grade, Bulk Orders, Seasonal


CREATE TABLE product_collection_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id VARCHAR NOT NULL,
    collection_id VARCHAR NOT NULL,
    
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (collection_id) REFERENCES collections(id),
    
    UNIQUE(product_id, collection_id)
);

CREATE INDEX idx_product_id ON product_collection_mapping(product_id);
CREATE INDEX idx_collection_id ON product_collection_mapping(collection_id);


CREATE TABLE product_attributes (
    id VARCHAR PRIMARY KEY,  -- organic, fair_trade, export_grade
    name VARCHAR NOT NULL,
    description TEXT,
    attribute_type VARCHAR,  -- boolean, enum, string
    
    created_at TIMESTAMP DEFAULT now()
);
```

**Why:** Attributes enable:
- Recommendation: "Pepper buyers buy Organic Cardamom 63% of time"
- Filtering: "Show all Organic, Fair Trade products"
- Segmentation: "High-volume bulk buyers"

---

### Layer 3: Orders with Proper Domain

```sql
CREATE TABLE orders (
    id VARCHAR PRIMARY KEY,  -- shopify_order_id
    
    customer_id VARCHAR,  -- FK to customers
    
    -- Order data
    total_amount NUMERIC(12,2),
    currency VARCHAR DEFAULT 'INR',
    
    payment_method VARCHAR,  -- cod, card, upi
    payment_status VARCHAR,  -- pending, paid, failed, refunded
    
    fulfillment_status VARCHAR,  -- pending, partial, fulfilled, cancelled
    
    -- Timeline
    created_at TIMESTAMP DEFAULT now(),
    paid_at TIMESTAMP,
    fulfilled_at TIMESTAMP,
    returned_at TIMESTAMP,
    refunded_at TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX idx_customer_id ON orders(customer_id);
CREATE INDEX idx_created_at ON orders(created_at DESC);


CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    order_id VARCHAR NOT NULL,
    product_id VARCHAR NOT NULL,
    
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12,2),
    total_price NUMERIC(12,2),
    
    -- Future: return_quantity, refund_amount
    
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE INDEX idx_order_id ON order_items(order_id);
```

**Why:** COD, refunds, returns, partial fulfillment all need structure.

---

### Layer 4: Events with Strict Schema

```sql
CREATE TABLE behavior_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event type (enforced in code)
    event_type VARCHAR NOT NULL,  -- page_view, product_view, add_to_cart, purchase
    
    -- Event data (with schema enforcement in app)
    event_data JSONB NOT NULL,
    
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

-- Schema enforced in code via EventValidator
-- No event is inserted without validation
```

---

### Layer 5: Generated Activity Feed (NOT Raw Events)

```sql
CREATE TABLE customer_activity_feed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    customer_id VARCHAR NOT NULL,
    
    -- Human-readable action
    action VARCHAR NOT NULL,  -- viewed_product, added_to_cart, purchased
    
    -- Display text (for UI)
    display_text TEXT NOT NULL,  -- "Viewed Black Pepper Product", "Purchased ₹899"
    
    -- Context (for UI enrichment)
    context JSONB,  -- {product_id: pepper_200g, product_name: Black Pepper}
    
    -- Links to original events/orders
    behavior_event_id UUID,
    order_id VARCHAR,
    
    -- Timeline
    created_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_customer_id ON customer_activity_feed(customer_id, created_at DESC);
);

-- Examples:
-- "Viewed Black Pepper Product" (from product_view event)
-- "Added Pepper to Cart" (from add_to_cart event)
-- "Purchased ₹899" (from purchase event)
-- "Returned Order" (from system event - future)
```

**Why:**
- UI renders fast (no joining events + products)
- Human-readable (no raw event type enumeration)
- Searchable (full-text search on display_text)

---

### Layer 6: Customer Profile (Stable)

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
    add_to_cart_count INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    
    -- Preferences
    favorite_product_id VARCHAR,
    favorite_collection VARCHAR,
    
    -- Segment
    segment VARCHAR,  -- vip, repeat, prospect, at_risk
    
    -- Health
    health_score INTEGER DEFAULT 0,
    
    generated_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX idx_segment ON customer_profiles(segment);
CREATE INDEX idx_ltv ON customer_profiles(lifetime_value DESC);
```

---

### Layer 7: Predictions (Mutable)

```sql
CREATE TABLE customer_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL,
    
    -- Scores
    lead_score INTEGER,
    churn_probability FLOAT,
    
    -- Predictions
    predicted_reorder_days INTEGER,
    predicted_next_purchase_value NUMERIC(12,2),
    
    generated_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    
    CREATE INDEX idx_customer_id ON customer_predictions(customer_id);
    CREATE INDEX idx_lead_score ON customer_predictions(lead_score DESC);
    CREATE INDEX idx_churn ON customer_predictions(churn_probability DESC);
);
```

---

### Layer 8: AI Recommendations (NEW)

```sql
CREATE TABLE ai_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    customer_id VARCHAR NOT NULL,
    product_id VARCHAR NOT NULL,
    
    -- Recommendation data
    score FLOAT,  -- 0-100 confidence
    reason TEXT,  -- "Pepper buyers purchase Cardamom 63% of the time"
    model_name VARCHAR,  -- "collaborative_filter_v1"
    
    -- Status
    recommended_at TIMESTAMP DEFAULT now(),
    clicked BOOLEAN DEFAULT FALSE,
    purchased BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE INDEX idx_customer_id ON ai_recommendations(customer_id);
Create INDEX idx_score ON ai_recommendations(score DESC);
```

**Why:**
- Foundation for: "Customers Also Bought"
- Feedback loop: track if recommended → purchased
- Future: personalized email campaigns, product recommendations

---

### Layer 9: Data Warehouse (Fast Dashboards)

```sql
CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_date DATE NOT NULL UNIQUE,
    
    page_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    add_to_cart_count INTEGER DEFAULT 0,
    purchases_count INTEGER DEFAULT 0,
    revenue_total NUMERIC(12,2) DEFAULT 0,
    
    conversion_rate FLOAT DEFAULT 0,
    atc_rate FLOAT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_metric_date ON daily_metrics(metric_date DESC);


CREATE TABLE daily_customer_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_date DATE NOT NULL,
    customer_id VARCHAR NOT NULL,
    
    page_views INTEGER DEFAULT 0,
    product_views INTEGER DEFAULT 0,
    added_to_cart BOOLEAN DEFAULT FALSE,
    purchased BOOLEAN DEFAULT FALSE,
    purchase_amount NUMERIC(12,2),
    
    UNIQUE(metric_date, customer_id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX idx_customer_date ON daily_customer_metrics(customer_id, metric_date DESC);


CREATE TABLE daily_product_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    metric_date DATE NOT NULL,
    product_id VARCHAR NOT NULL,
    
    views INTEGER DEFAULT 0,
    added_to_cart INTEGER DEFAULT 0,
    sold INTEGER DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    
    UNIQUE(metric_date, product_id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

Create INDEX idx_product_date ON daily_product_metrics(product_id, metric_date DESC);
```

---

## Core Architecture: Event Dispatcher (Nervous System)

### Event Flow

```
Shopify Webhook
    ↓
Order Service (validate order, emit OrderCreated event)
    ↓
Event Service (validate, emit to behavior_events)
    ↓
Event Dispatcher (core)
    ├─→ Identity Service (who is this?)
    ├─→ Profile Service (update profile)
    ├─→ Segmentation Service (reassign segment)
    ├─→ Prediction Service (recalc lead score)
    └─→ Analytics Service (update daily_metrics)
    ↓
Customer Activity Feed (generated record for UI)
    ↓
APIs Ready (for UI to consume)
```

### Event Dispatcher Implementation

```python
# domains/tracking/event_dispatcher.py

from dataclasses import dataclass
from typing import Callable, List

@dataclass
class EventDispatcherJob:
    event_id: str
    event_type: str
    customer_id: str
    event_data: dict

class EventDispatcher:
    """
    Core nervous system.
    Receives event, dispatches to all dependent services.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.handlers: List[Callable] = []
    
    def register_handler(self, handler: Callable):
        """Register a service to be notified of events"""
        self.handlers.append(handler)
    
    def dispatch(self, event_id: str, event_type: str, customer_id: str, event_data: dict):
        """
        Dispatch event to all registered handlers.
        Each service processes independently.
        """
        job = EventDispatcherJob(
            event_id=event_id,
            event_type=event_type,
            customer_id=customer_id,
            event_data=event_data
        )
        
        # Dispatch to all handlers (can be async via Celery)
        for handler in self.handlers:
            try:
                handler(job)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed: {e}")
                # Don't fail entire dispatch, continue

# Initialize dispatcher with handlers
dispatcher = EventDispatcher(db)
dispatcher.register_handler(identity_service.handle_event)
dispatcher.register_handler(profile_service.handle_event)
dispatcher.register_handler(segmentation_service.handle_event)
dispatcher.register_handler(prediction_service.handle_event)
dispatcher.register_handler(analytics_service.handle_event)
dispatcher.register_handler(activity_feed_service.handle_event)
```

**Why:** Services don't know about each other. Event dispatcher decouples them.

---

## 12-Phase Implementation Plan

### Sprint 0: Infrastructure & Folder Structure (Week 1)

**Goal:** Set up infrastructure and folder structure.

**Build:**
- Redis, Celery, Sentry, pgBouncer
- Create folder structure (domains/tracking, domains/customers, etc.)
- Database session management

**Outcome:**
- ✅ Infrastructure ready
- ✅ Folder structure in place
- ✅ All services can be added independently

---

### Sprint 1: Events + Event Dispatcher (Week 2)

**Goal:** Event system with dispatcher core.

**Create:**
- behavior_events table
- system_events table
- event_service.py (with validation)
- event_dispatcher.py
- EventValidator (schema enforcement)

**Update:**
- crm_routes.py: POST /api/events endpoint

**Test:**
- Events validated before insert
- Dispatcher receives events
- Event flow working

**Outcome:**
- ✅ Event system live
- ✅ Dispatcher ready (handlers not yet connected)

---

### Sprint 2: Products Domain (Week 3)

**Goal:** Product catalog with attributes.

**Create:**
- products table
- collections table
- product_collection_mapping
- product_attributes table

**Create:**
- product_service.py
- product_repository.py

**Test:**
- Products can be created
- Collections can be created
- Attributes stored as JSONB

**Outcome:**
- ✅ Product catalog ready
- ✅ Attributes support future recommendations

---

### Sprint 3: Orders Domain (Week 4)

**Goal:** Proper order handling.

**Migrate:**
- crm_orders → orders table (refactor, add new fields)
- Create order_items table
- Link to products

**Create:**
- order_service.py
- order_repository.py
- order_webhooks.py

**Update:**
- Shopify webhook: Emit OrderCreated event to dispatcher

**Test:**
- Orders tracked properly
- Order items linked to products
- OrderCreated events emit

**Outcome:**
- ✅ Order domain established
- ✅ Orders emit events to dispatcher

---

### Sprint 4: Visitor & Session Tracking (Week 5)

**Goal:** Anonymous tracking.

**Create:**
- visitors table
- sessions table
- event_service registers visitors/sessions

**Update:**
- crm-attribution.js: Register visitor/session

**Test:**
- Visitors registered
- Sessions tracked
- Device/IP captured

**Outcome:**
- ✅ Anonymous tracking working

---

### Sprint 5: Event Emission from Browser (Week 6)

**Goal:** Browser emits behavior events.

**Update:**
- crm-attribution.js: Emit page_view, product_view, add_to_cart
- Validate events before sending

**Test:**
- behavior_events table has 100+ events/day
- Events validated

**Outcome:**
- ✅ Browser events flowing

---

### Sprint 6: Identity Service (Week 7)

**Goal:** Link visitor → customer.

**Create:**
- customer_identities table
- identity_service.py

**Update:**
- Event dispatcher: Connect identity_service handler
- POST /api/customers/identify endpoint

**Test:**
- Visitors linked to customers
- All events get customer_id
- Retroactive linking working

**Outcome:**
- ✅ Visitor → customer linkage working

---

### Sprint 7: Profile Service (Week 8)

**Goal:** Generate customer profiles.

**Create:**
- customer_profiles table
- profile_service.py
- Celery job (every 5 min)

**Update:**
- Event dispatcher: Connect profile_service handler

**Test:**
- Profiles generated for all customers
- LTV correct
- Metrics accurate

**Outcome:**
- ✅ Profiles generated

---

### Sprint 8: Segmentation + Predictions (Week 9)

**Goal:** Classify and predict.

**Create:**
- segmentation_service.py
- customer_predictions table
- prediction_service.py
- ai_recommendations table
- recommendation_service.py

**Update:**
- Event dispatcher: Connect all handlers

**Test:**
- Segments assigned
- Predictions generated
- Recommendations scored

**Outcome:**
- ✅ Full customer intelligence available

---

### Sprint 8.5: Activity Feed Generation (Week 9.5)

**Goal:** Generate human-readable timeline.

**Create:**
- customer_activity_feed table
- activity_feed_service.py

**Update:**
- Event dispatcher: Connect activity_feed handler
- Transform raw events into display_text

**Test:**
- "Viewed Black Pepper Product" generated from events
- "Purchased ₹899" generated from purchase events
- UI can render feed fast

**Outcome:**
- ✅ Human-readable activity feed ready

---

### Sprint 9: Data Warehouse (Week 10)

**Goal:** Fast dashboards.

**Create:**
- daily_metrics, daily_customer_metrics, daily_product_metrics
- Nightly aggregation job (Celery)

**Test:**
- Aggregates generated nightly
- Dashboard queries < 100ms

**Outcome:**
- ✅ Dashboards fast

---

### Sprint 10: Admin APIs (Internal Stabilization) (Week 11)

**Goal:** Stabilize internal APIs before UI.

**Create:**
- GET /health (system health)
- GET /api/admin/events (event logs)
- GET /api/admin/customers (customer search + detail)
- GET /api/admin/profiles (profile data)
- GET /api/admin/predictions (prediction data)
- GET /api/admin/recommendations (recommendation data)

**Test:**
- All endpoints respond correctly
- Data consistent
- Pagination works
- Response times < 100ms

**Duration:** 1 week (Sprint 10 only, extended testing)

**Outcome:**
- ✅ APIs stable for UI development

---

### Sprint 11: Customer 360 UI (Week 12)

**Goal:** First UI (customer-centric).

**Create:**
- Customer list API (search)
- Customer detail API
- Frontend: CustomerListPage, CustomerDetailPage

**Tabs:**
- Overview (profile + segment + health + predictions)
- Timeline (activity feed)
- Orders
- Products
- Tasks (empty for now)
- Communications (empty for now)
- Insights

**Test:**
- Search works
- Timeline renders
- All data visible
- Mobile responsive

**Outcome:**
- ✅ Customer 360 UI live

---

### (Future) Sprint 12: Communications Domain Setup

**Goal:** Ready for WhatsApp + Email.

**Create:**
- communications domain folder structure
- messaging_service.py (stub)
- channel_router.py (stub)

**Status:** Empty, ready for WhatsApp integration.

---

## UI Architecture: Customer-Centric

```
Customer Detail

├── Overview Tab
│   ├── Profile (email, phone, LTV, created_at, last_activity)
│   ├── Segment (VIP, repeat, at_risk)
│   ├── Health Score (0-100)
│   └── Quick Stats (total orders, avg order value)
│
├── Timeline Tab
│   └── Activity Feed (human-readable events from customer_activity_feed)
│       Examples:
│       - Viewed Black Pepper Product
│       - Added Pepper to Cart
│       - Purchased ₹899
│       - Viewed Premium Cardamom
│
├── Orders Tab
│   └── Purchase History (all orders with dates, amounts)
│
├── Products Tab
│   ├── Products Purchased
│   └── Reorder Potential (predicted_reorder_days)
│
├── Tasks Tab [NEW]
│   └── Customer tasks (future: created from automation)
│
├── Communications Tab [NEW]
│   ├── WhatsApp (future)
│   ├── Email (future)
│   └── SMS (future)
│
└── Insights Tab
    ├── Lead Score (with breakdown)
    ├── Churn Risk (probability + factors)
    ├── Reorder Prediction (days until next purchase)
    └── AI Recommendations (products recommended, scores, reasons)
```

---

## Services Integration Map

```
Event Dispatcher (core)
    ├── Identity Service
    │   └── Resolves: visitor → customer
    │
    ├── Profile Service
    │   └── Generates: customer_profiles (metrics, timeline)
    │
    ├── Segmentation Service
    │   └── Assigns: segment (VIP, at_risk, etc.)
    │
    ├── Prediction Service
    │   ├── Lead Score
    │   ├── Churn Probability
    │   └── Reorder Days
    │
    ├── Recommendation Service
    │   └── Generates: ai_recommendations (with reasons)
    │
    └── Activity Feed Service
        └── Generates: customer_activity_feed (human-readable)
```

**Key:** No service calls another. All go through dispatcher.

---

## What's Different from Previous Plan

| Previous | Final Approved | Why |
|----------|---|---|
| Flat services/ | Domain-driven structure | Prevents 4000-line files |
| No Order domain | Order service + repo | Handles COD, refunds, returns |
| Simple categories | Products + collections + attributes | Enables recommendations |
| Raw events in timeline | Generated activity_feed | Fast UI, human-readable |
| Free-form event_data | Strict schema validation | Prevents JSON chaos |
| No event dispatcher | Event dispatcher (core) | Decouples services |
| No communications domain | Communications domain (empty, ready) | Ready for WhatsApp |
| No recommendations | ai_recommendations table | Future product engines |
| 10 phases | 12 phases (+ 0.5 for activity feed) | Better testing gates |
| UI before APIs | APIs stabilized in Sprint 10 | Prevents rework |

---

## After Sprint 11: What You Have

✅ **Domain-driven architecture** — Each domain can scale independently  
✅ **Event dispatcher** — Core nervous system, services decouple  
✅ **Product intelligence** — Attributes, collections, recommendations ready  
✅ **Customer intelligence** — Profile, segment, predictions, activity feed  
✅ **Fast dashboards** — Data warehouse, nightly aggregates  
✅ **API-first** — Stabilized before UI  
✅ **Future-ready** — Communications domain, automation domain (stubs ready)  

**Total effort:** 12 weeks, 1 full-time engineer.

**Result:** Proper Customer Intelligence Platform. Extensible. Production-ready. Ready for WhatsApp, automation, AI, recommendations.

---

## Critical Success Factors

1. **Event Dispatcher is Core** — Services don't depend on each other, all depend on dispatcher
2. **Schema Validation First** — Prevent bad data, not clean it up later
3. **Activity Feed Separation** — Raw events separate from human-readable timeline
4. **API Stabilization** — Sprint 10 focuses only on APIs, not UI
5. **Domain Independence** — Each domain can be scaled/iterated independently

---

## Infrastructure Stack (Final)

```
PostgreSQL + pgBouncer (connection pooling)
Redis (caching, job queue)
Celery (async tasks, scheduled jobs)
Sentry (error tracking)
FastAPI (API framework)
SQLAlchemy (ORM)
Pydantic (validation)
```

**pgBouncer:** Prevents connection exhaustion from FastAPI + Celery + Analytics queries.

