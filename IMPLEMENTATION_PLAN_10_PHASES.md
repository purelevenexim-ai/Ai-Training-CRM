# Pureleven Intelligence Platform — 10-Phase Implementation Plan

**Approach:** Parallel architecture — Keep production untouched, build new system alongside  
**Timeline:** 10 phases, 1 week per phase = 10 weeks  
**Team:** 1 full-time engineer (you)  
**Principle:** Test each phase before moving to next  

---

## Architecture: Production + Intelligence Platform

```
PRODUCTION SYSTEM (UNTOUCHED)          INTELLIGENCE PLATFORM (NEW)
┌────────────────────────┐             ┌─────────────────────────┐
│                        │             │                         │
│  Shopify Store         │             │  crm_events             │
│  crm_routes.py        │─────────────→│  identity_service       │
│  crm_orders           │             │  profile_service        │
│  crm_customers        │             │  timeline_service       │
│  tracking_events      │             │  crm_visitors           │
│  GA4 / Meta fanout    │             │  crm_profiles           │
│                        │             │                         │
└────────────────────────┘             │  Customer 360 UI        │
                                       │  Leads (Phase 5+)       │
                                       │  Automation (Phase 6+)  │
                                       │                         │
                                       └─────────────────────────┘
```

**Key:** Production system unchanged. New system grows beside it.

---

## Phase 1: Event Foundation (Week 1)

**Goal:** Single crm_events table, nothing else. Validate it works.

### What to Build

**1. Database Migration:**

```sql
CREATE TABLE crm_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What happened
    event_name VARCHAR NOT NULL,  -- page_view, product_view, add_to_cart, purchase, etc.
    event_data JSONB,             -- Flexible: {product_id, price, order_id, amount, ...}
    
    -- Who did it (may be null initially)
    visitor_id UUID,
    customer_id VARCHAR,          -- Will be linked later
    session_id UUID,
    
    -- Attribution
    utm_source VARCHAR,
    utm_medium VARCHAR,
    utm_campaign VARCHAR,
    utm_content VARCHAR,
    gclid VARCHAR,
    fbclid VARCHAR,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    referrer VARCHAR,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_event_name ON crm_events(event_name);
CREATE INDEX idx_customer_id ON crm_events(customer_id) WHERE customer_id IS NOT NULL;
CREATE INDEX idx_created_at ON crm_events(created_at DESC);
CREATE INDEX idx_visitor_id ON crm_events(visitor_id) WHERE visitor_id IS NOT NULL;
```

**2. Event Service (new file: `app/services/event_service.py`):**

```python
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import insert
from datetime import datetime
from uuid import uuid4

def create_event(
    db: Session,
    event_name: str,
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
    user_agent: str = None,
    referrer: str = None,
) -> dict:
    """
    Create an event in crm_events table.
    Single source of truth for all event creation.
    """
    
    event = {
        "id": str(uuid4()),
        "event_name": event_name,
        "event_data": event_data or {},
        "visitor_id": visitor_id,
        "customer_id": customer_id,
        "session_id": session_id,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "gclid": gclid,
        "fbclid": fbclid,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "referrer": referrer,
        "created_at": datetime.now()
    }
    
    # Insert into crm_events
    stmt = insert(CrmEvent).values(**event)
    db.execute(stmt)
    db.commit()
    
    return {
        "id": event["id"],
        "event_name": event_name,
        "created_at": event["created_at"]
    }

def get_events(db: Session, limit: int = 100) -> list:
    """Query recent events (for testing)"""
    events = db.query(CrmEvent).order_by(CrmEvent.created_at.desc()).limit(limit).all()
    return events
```

**3. Add API Endpoint (in `crm_routes.py`):**

```python
@app.post("/api/events")
async def track_event(
    event_name: str,
    event_data: dict = None,
    visitor_id: str = None,
    session_id: str = None,
    utm_source: str = None,
    utm_medium: str = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Create an event.
    Example:
    POST /api/events?event_name=page_view&visitor_id=V123
    {
      "event_data": {"page": "/products/pepper"}
    }
    """
    
    from app.services.event_service import create_event
    
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None
    
    result = create_event(
        db=db,
        event_name=event_name,
        event_data=event_data,
        visitor_id=visitor_id,
        session_id=session_id,
        utm_source=utm_source,
        utm_medium=utm_medium,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    return result


@app.get("/api/events?limit=100")
async def get_recent_events(limit: int = 100, db: Session = Depends(get_db)):
    """Get recent events (for testing)"""
    from app.services.event_service import get_events
    events = get_events(db, limit)
    return [
        {
            "id": e.id,
            "event_name": e.event_name,
            "event_data": e.event_data,
            "created_at": e.created_at
        }
        for e in events
    ]
```

**4. Add Model (in `models.py`):**

```python
from sqlalchemy import Column, String, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import UUID, INET
import uuid

class CrmEvent(Base):
    __tablename__ = "crm_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_name = Column(String, nullable=False, index=True)
    event_data = Column(JSON, nullable=True)
    
    visitor_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    customer_id = Column(String, nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    
    utm_source = Column(String, nullable=True)
    utm_medium = Column(String, nullable=True)
    utm_campaign = Column(String, nullable=True)
    utm_content = Column(String, nullable=True)
    gclid = Column(String, nullable=True)
    fbclid = Column(String, nullable=True)
    
    ip_address = Column(INET, nullable=True)
    user_agent = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
```

### Testing Phase 1

**1. Create table:**
```bash
ssh root@192.46.213.140
docker exec pureleven-postgres psql -U pureleven -d pureleven -f migrations/create_crm_events.sql
```

**2. Verify table exists:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c "\dt crm_events"
```

**3. Test API endpoint:**
```bash
curl -X POST "https://track.pureleven.com/api/events?event_name=test_event&visitor_id=V123" \
  -H "Content-Type: application/json" \
  -d '{"event_data": {"test": "data"}}'
```

**4. Verify data inserted:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT COUNT(*) as event_count FROM crm_events;"
```

**Success Criteria:**
- ✅ Table created with all columns
- ✅ Indexes created
- ✅ API endpoint responds 200
- ✅ Event inserted into table
- ✅ Can query recent events

---

## Phase 2: Browser Event Tracking (Week 2)

**Goal:** Browser emits page_view and product_view events.

### What to Build

**1. Update `crm-attribution.js`:**

Add event emission (alongside existing code):

```javascript
// NEW: Emit page_view event
window.trackPageView = async function(pageUrl) {
    const payload = {
        event_name: "page_view",
        event_data: {
            page_url: pageUrl,
            page_title: document.title
        },
        visitor_id: getVisitorId(),
        session_id: getSessionId(),
        utm_source: getUTMParam('utm_source'),
        utm_medium: getUTMParam('utm_medium'),
        utm_campaign: getUTMParam('utm_campaign')
    };
    
    try {
        await fetch("/api/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to track page_view:", e);
    }
};

// Call on every page load
document.addEventListener("DOMContentLoaded", () => {
    window.trackPageView(window.location.pathname);
});

// NEW: Emit product_view event
window.trackProductView = async function(productId, productName, price) {
    const payload = {
        event_name: "product_view",
        event_data: {
            product_id: productId,
            product_name: productName,
            price: price
        },
        visitor_id: getVisitorId(),
        session_id: getSessionId(),
        utm_source: getUTMParam('utm_source'),
        utm_medium: getUTMParam('utm_medium')
    };
    
    try {
        await fetch("/api/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to track product_view:", e);
    }
};

// Call when product page loads (Shopify-specific)
// Find product ID from page meta tag or window variable
if (window.Shopify && window.Shopify.product) {
    window.trackProductView(
        window.Shopify.product.id,
        window.Shopify.product.title,
        window.Shopify.product.price
    );
}
```

**2. Event types to enable (create as reference doc for now):**

```
page_view — User visits a page
product_view — User views a product (with product_id, price)
add_to_cart — User adds to cart
begin_checkout — User starts checkout
purchase — Order placed
home_page — User visits home
pepper_page — User visits Pepper pillar page (future)
cardamom_page — User visits Cardamom pillar page (future)
```

### Testing Phase 2

**1. Deploy updated `crm-attribution.js`:**
```bash
# Update the file locally, then deploy to Shopify or CDN
```

**2. Visit store and check events:**
```bash
# Open browser dev console on https://pureleven.com/
# Should see fetch POST to /api/events
```

**3. Query created events:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT event_name, COUNT(*) FROM crm_events GROUP BY 1 ORDER BY COUNT(*) DESC;"
```

**Success Criteria:**
- ✅ page_view events appearing in crm_events
- ✅ product_view events appearing
- ✅ Visitor ID consistent across events
- ✅ UTM params captured
- ✅ No errors in browser console

---

## Phase 3: Visitor Tracking (Week 3)

**Goal:** Know who the anonymous visitor is.

### What to Build

**1. Create visitors table:**

```sql
CREATE TABLE crm_visitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL UNIQUE,
    
    customer_id VARCHAR,  -- Linked later
    
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    device_id VARCHAR,
    ip_address INET,
    
    FOREIGN KEY (customer_id) REFERENCES crm_customers(id)
);

CREATE INDEX idx_session_id ON crm_visitors(session_id);
CREATE INDEX idx_customer_id ON crm_visitors(customer_id) WHERE customer_id IS NOT NULL;
```

**2. Update crm-attribution.js to send visitor info:**

```javascript
// Generate or retrieve visitor ID
window.getVisitorId = function() {
    let visitorId = localStorage.getItem('pureleven_visitor_id');
    if (!visitorId) {
        visitorId = 'V' + Date.now() + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('pureleven_visitor_id', visitorId);
    }
    return visitorId;
};

// Generate session ID (per browser tab)
window.getSessionId = function() {
    if (!window.pureleven_session_id) {
        window.pureleven_session_id = 'S' + Date.now() + Math.random().toString(36).substr(2, 9);
    }
    return window.pureleven_session_id;
};

// Send visitor info to backend
window.registerVisitor = async function() {
    const payload = {
        visitor_id: getVisitorId(),
        session_id: getSessionId(),
        device_id: getDeviceId()
    };
    
    try {
        await fetch("/api/visitors/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to register visitor:", e);
    }
};

// Register visitor on page load
document.addEventListener("DOMContentLoaded", () => {
    window.registerVisitor();
});
```

**3. Add API endpoint (in `crm_routes.py`):**

```python
@app.post("/api/visitors/register")
async def register_visitor(
    visitor_id: str,
    session_id: str,
    device_id: str = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Register a visitor"""
    
    # Check if visitor already exists
    existing = db.query(CrmVisitor).filter(
        CrmVisitor.session_id == session_id
    ).first()
    
    if not existing:
        visitor = CrmVisitor(
            id=uuid.uuid4(),
            session_id=session_id,
            device_id=device_id,
            ip_address=request.client.host if request else None
        )
        db.add(visitor)
    else:
        existing.last_seen = datetime.now()
    
    db.commit()
    
    return {"visitor_id": visitor_id, "session_id": session_id}
```

### Testing Phase 3

**1. Create table:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "CREATE TABLE crm_visitors (...);"
```

**2. Visit store, check browser console:**
```
Should see fetch POST to /api/visitors/register
```

**3. Verify visitor registered:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT COUNT(*) FROM crm_visitors;"
```

**Success Criteria:**
- ✅ crm_visitors table has rows
- ✅ Visitor ID consistent across page reloads (localStorage)
- ✅ Session ID per browser tab
- ✅ IP address captured

---

## Phase 4: Shopify Order Event (Week 4)

**Goal:** Orders emit events (alongside existing crm_orders).

### What to Build

**1. Update Shopify webhook in `crm_routes.py`:**

After existing order processing, add:

```python
@app.post("/api/crm/webhooks/shopify")
async def shopify_webhook(request: Request, db: Session = Depends(get_db)):
    # ... existing code ...
    
    # EXISTING: Store in crm_orders, send to Meta/GA4
    # This all stays the same
    
    # NEW: Emit purchase event
    from app.services.event_service import create_event
    
    create_event(
        db=db,
        event_name="purchase",
        event_data={
            "order_id": order_id,
            "email": email,
            "amount": total_price,
            "currency": currency,
            "items": items,
            "payment_method": payment_method,
            "cart_token": cart_token
        },
        customer_id=customer_id,  # If known
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
        gclid=gclid,
        fbclid=fbclid
    )
    
    # ... rest of webhook handling continues ...
```

**2. No schema changes needed.** Just calling create_event service.

### Testing Phase 4

**1. Place a test order on store:**
```
https://pureleven.com → Add to cart → Checkout → Place order
```

**2. Verify purchase event created:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT * FROM crm_events WHERE event_name='purchase' ORDER BY created_at DESC LIMIT 1;"
```

**3. Verify production tracking still works:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT * FROM crm_orders ORDER BY order_date DESC LIMIT 1;"
```

**Success Criteria:**
- ✅ crm_events has purchase event
- ✅ crm_orders still has order (unchanged)
- ✅ Meta still receives purchase event
- ✅ GA4 still receives purchase event
- ✅ Zero impact on production tracking

---

## Phase 5: Identity Resolution Service (Week 5)

**Goal:** Link visitor → customer when email enters.

### What to Build

**1. Create identities table:**

```sql
CREATE TABLE customer_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL,
    
    email VARCHAR UNIQUE,
    phone VARCHAR UNIQUE,
    shopify_customer_id VARCHAR UNIQUE,
    
    visitor_id UUID,
    session_id UUID,
    
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX idx_customer_id ON customer_identities(customer_id);
CREATE INDEX idx_email ON customer_identities(email);
```

**2. Create identity service (new file: `app/services/identity_service.py`):**

```python
def resolve_identity(
    db: Session,
    email: str = None,
    phone: str = None,
    shopify_customer_id: str = None,
    visitor_id: str = None,
    session_id: str = None,
) -> str:
    """
    Link visitor to customer.
    Returns customer_id.
    """
    
    customer_id = None
    
    # Check if email exists in identities
    if email:
        identity = db.query(CustomerIdentity).filter(
            CustomerIdentity.email == email
        ).first()
        if identity:
            customer_id = identity.customer_id
    
    # Check if phone exists
    if not customer_id and phone:
        identity = db.query(CustomerIdentity).filter(
            CustomerIdentity.phone == phone
        ).first()
        if identity:
            customer_id = identity.customer_id
    
    # Check if shopify customer ID exists
    if not customer_id and shopify_customer_id:
        identity = db.query(CustomerIdentity).filter(
            CustomerIdentity.shopify_customer_id == shopify_customer_id
        ).first()
        if identity:
            customer_id = identity.customer_id
    
    # If found, update existing
    if customer_id and identity:
        identity.visitor_id = visitor_id or identity.visitor_id
        identity.session_id = session_id or identity.session_id
        identity.last_seen = datetime.now()
    else:
        # Create new customer identity
        # First check if customer exists in crm_customers
        customer = None
        if email:
            customer = db.query(Customer).filter(
                Customer.email == email
            ).first()
        
        if not customer:
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
            id=uuid.uuid4(),
            customer_id=customer_id,
            email=email,
            phone=phone,
            shopify_customer_id=shopify_customer_id,
            visitor_id=visitor_id,
            session_id=session_id
        )
        db.add(identity)
    
    db.commit()
    
    # Update all events from this visitor to have customer_id
    if visitor_id and customer_id:
        db.query(CrmEvent).filter(
            CrmEvent.visitor_id == visitor_id,
            CrmEvent.customer_id.is_(None)
        ).update({CrmEvent.customer_id: customer_id})
        db.commit()
    
    return customer_id


@app.post("/api/customers/identify")
async def identify(
    email: str = None,
    phone: str = None,
    visitor_id: str = None,
    session_id: str = None,
    db: Session = Depends(get_db)
):
    """Identify a customer"""
    from app.services.identity_service import resolve_identity
    
    customer_id = resolve_identity(
        db=db,
        email=email,
        phone=phone,
        visitor_id=visitor_id,
        session_id=session_id
    )
    
    return {"customer_id": customer_id}
```

**3. Update crm-attribution.js to call identify:**

```javascript
window.identifyCustomer = async function(email) {
    const payload = {
        email: email,
        visitor_id: getVisitorId(),
        session_id: getSessionId()
    };
    
    try {
        const response = await fetch("/api/customers/identify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        localStorage.setItem('pureleven_customer_id', result.customer_id);
        return result.customer_id;
    } catch (e) {
        console.error("Failed to identify customer:", e);
    }
};

// Call when email is entered (Shopify checkout page)
// Hook into email input change event
document.addEventListener("DOMContentLoaded", () => {
    const emailInput = document.querySelector('input[type="email"]');
    if (emailInput) {
        emailInput.addEventListener("change", (e) => {
            if (e.target.value) {
                window.identifyCustomer(e.target.value);
            }
        });
    }
});
```

### Testing Phase 5

**1. Create table:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "CREATE TABLE customer_identities (...);"
```

**2. Test identify endpoint:**
```bash
curl -X POST "https://track.pureleven.com/api/customers/identify" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "visitor_id": "V123"}'
```

**3. Verify identity created:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT * FROM customer_identities LIMIT 5;"
```

**Success Criteria:**
- ✅ Visitor linked to customer
- ✅ All previous events updated with customer_id
- ✅ New events have customer_id from start
- ✅ No duplicates in customer_identities

---

## Phase 6: Customer Sessions (Week 6)

**Goal:** Track complete user sessions.

### What to Build

**1. Create sessions table:**

```sql
CREATE TABLE crm_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_id UUID NOT NULL,
    customer_id VARCHAR,
    
    started_at TIMESTAMP DEFAULT now(),
    ended_at TIMESTAMP,
    
    page_views_count INTEGER DEFAULT 0,
    product_views_count INTEGER DEFAULT 0,
    events_count INTEGER DEFAULT 0,
    
    landing_page VARCHAR,
    exit_page VARCHAR,
    referrer VARCHAR,
    
    FOREIGN KEY (visitor_id) REFERENCES crm_visitors(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE INDEX idx_visitor_id ON crm_sessions(visitor_id);
CREATE INDEX idx_customer_id ON crm_sessions(customer_id);
CREATE INDEX idx_started_at ON crm_sessions(started_at DESC);
```

**2. Session service:**

```python
def create_session(
    db: Session,
    visitor_id: str,
    session_id: str,
    referrer: str = None,
    landing_page: str = None
) -> str:
    """Create session record"""
    
    session = CrmSession(
        id=uuid.uuid4(),
        visitor_id=visitor_id,
        referrer=referrer,
        landing_page=landing_page
    )
    db.add(session)
    db.commit()
    return str(session.id)
```

**3. Update crm-attribution.js to call create_session:**

```javascript
window.initializeSession = async function() {
    const referrer = document.referrer;
    const landing_page = window.location.pathname;
    
    const payload = {
        visitor_id: getVisitorId(),
        session_id: getSessionId(),
        referrer: referrer,
        landing_page: landing_page
    };
    
    try {
        await fetch("/api/sessions/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to create session:", e);
    }
};

// Call on page load
document.addEventListener("DOMContentLoaded", () => {
    window.initializeSession();
});
```

### Testing Phase 6

**1. Create table:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "CREATE TABLE crm_sessions (...);"
```

**2. Visit store, check sessions created:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT * FROM crm_sessions ORDER BY started_at DESC LIMIT 5;"
```

**Success Criteria:**
- ✅ Session created on first page load
- ✅ Referrer captured
- ✅ Landing page captured
- ✅ Multiple pages in same session tracked

---

## Phase 7: Customer Profiles Projection (Week 7)

**Goal:** Generate customer_profiles table from events.

### What to Build

**1. Create profiles table:**

```sql
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR NOT NULL UNIQUE,
    
    email VARCHAR,
    phone VARCHAR,
    name VARCHAR,
    
    -- Metrics
    lifetime_value NUMERIC DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    average_order_value NUMERIC,
    
    -- Timeline
    first_seen TIMESTAMP,
    first_purchase TIMESTAMP,
    last_purchase TIMESTAMP,
    last_activity TIMESTAMP,
    days_since_last_activity INTEGER,
    
    -- Engagement
    page_views_count INTEGER DEFAULT 0,
    product_views_count INTEGER DEFAULT 0,
    total_events_count INTEGER DEFAULT 0,
    
    -- AI Fields (placeholder)
    health_score INTEGER DEFAULT 0,
    lead_score INTEGER DEFAULT 0,
    churn_probability FLOAT DEFAULT 0,
    
    -- Generated
    generated_at TIMESTAMP DEFAULT now(),
    
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    UNIQUE(customer_id)
);

CREATE INDEX idx_customer_id ON customer_profiles(customer_id);
CREATE INDEX idx_lifetime_value ON customer_profiles(lifetime_value DESC);
CREATE INDEX idx_health_score ON customer_profiles(health_score DESC);
```

**2. Profile generation service (new file: `app/services/profile_service.py`):**

```python
def generate_customer_profile(db: Session, customer_id: str) -> dict:
    """
    Generate complete customer profile from events + orders.
    Called periodically (every 5 minutes).
    Replaces entire row.
    """
    
    from app.services.event_service import create_event
    
    # Get customer identity
    identity = db.query(CustomerIdentity).filter(
        CustomerIdentity.customer_id == customer_id
    ).first()
    
    if not identity:
        return None
    
    # Get all events for this customer
    events = db.query(CrmEvent).filter(
        CrmEvent.customer_id == customer_id
    ).all()
    
    # Get all orders for this customer
    orders = db.query(CrmOrder).filter(
        CrmOrder.email == identity.email
    ).all()
    
    # Calculate metrics
    lifetime_value = sum(o.total_amount for o in orders) if orders else 0
    total_orders = len(orders)
    average_order_value = lifetime_value / total_orders if total_orders > 0 else 0
    
    # Timeline
    first_seen = min(e.created_at for e in events) if events else None
    last_activity = max(e.created_at for e in events) if events else None
    first_purchase = min(o.order_date for o in orders) if orders else None
    last_purchase = max(o.order_date for o in orders) if orders else None
    
    days_since_activity = (datetime.now() - last_activity).days if last_activity else None
    
    # Engagement
    page_views = len([e for e in events if e.event_name == "page_view"])
    product_views = len([e for e in events if e.event_name == "product_view"])
    total_events = len(events)
    
    # Health score (0-100)
    health_score = 0
    if total_orders > 0:
        health_score += 25  # Made purchase
    if total_events > 5:
        health_score += 25  # High engagement
    if average_order_value > 500:
        health_score += 25  # High AOV
    if not days_since_activity or days_since_activity < 30:
        health_score += 25  # Recent activity
    
    # Update or create profile
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        profile = CustomerProfile(customer_id=customer_id)
        db.add(profile)
    
    profile.email = identity.email
    profile.phone = identity.phone
    profile.lifetime_value = lifetime_value
    profile.total_orders = total_orders
    profile.average_order_value = average_order_value
    profile.first_seen = first_seen
    profile.first_purchase = first_purchase
    profile.last_purchase = last_purchase
    profile.last_activity = last_activity
    profile.days_since_last_activity = days_since_activity
    profile.page_views_count = page_views
    profile.product_views_count = product_views
    profile.total_events_count = total_events
    profile.health_score = health_score
    profile.generated_at = datetime.now()
    
    db.commit()
    
    return {
        "customer_id": customer_id,
        "lifetime_value": lifetime_value,
        "health_score": health_score,
        "generated_at": profile.generated_at
    }


def generate_all_profiles(db: Session):
    """Generate profiles for all customers"""
    customers = db.query(distinct(CrmEvent.customer_id)).filter(
        CrmEvent.customer_id.isnot(None)
    ).all()
    
    for (customer_id,) in customers:
        generate_customer_profile(db, customer_id)
    
    return {"profiles_generated": len(customers)}
```

**3. Setup Celery job (new file: `app/celery_tasks.py`):**

```python
from celery import Celery
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.services.profile_service import generate_all_profiles

celery_app = Celery(
    'pureleven',
    broker='redis://localhost:6379',
    backend='redis://localhost:6379'
)

@celery_app.task
def refresh_all_profiles():
    """Regenerate all customer profiles"""
    db = SessionLocal()
    try:
        result = generate_all_profiles(db)
        print(f"Profiles refreshed: {result}")
        return result
    finally:
        db.close()

# Schedule every 5 minutes
celery_app.conf.beat_schedule = {
    'refresh-profiles': {
        'task': 'app.celery_tasks.refresh_all_profiles',
        'schedule': 300.0,  # Every 5 minutes
    },
}
```

**4. Add API endpoint:**

```python
@app.get("/api/customers/{customer_id}/profile")
async def get_customer_profile(customer_id: str, db: Session = Depends(get_db)):
    """Get customer profile"""
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        from app.services.profile_service import generate_customer_profile
        generate_customer_profile(db, customer_id)
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer_id
        ).first()
    
    return {
        "customer_id": profile.customer_id,
        "email": profile.email,
        "lifetime_value": profile.lifetime_value,
        "total_orders": profile.total_orders,
        "health_score": profile.health_score,
        "last_activity": profile.last_activity
    }
```

### Testing Phase 7

**1. Create table:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "CREATE TABLE customer_profiles (...);"
```

**2. Setup Redis & Celery:**
```bash
# Update docker-compose.yml with redis
# Deploy Celery worker
```

**3. Manually trigger profile generation:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT * FROM customer_profiles LIMIT 5;"
```

**4. Test API endpoint:**
```bash
curl https://track.pureleven.com/api/customers/cust_123/profile
```

**Success Criteria:**
- ✅ customer_profiles table has rows
- ✅ LTV calculations correct (matches crm_orders)
- ✅ Health score 0-100
- ✅ API returns profile instantly

---

## Phase 8: Customer 360 UI (Week 8)

**Goal:** First UI reading from customer_profiles and crm_events.

### What to Build

**1. Backend APIs (4 endpoints):**

```python
@app.get("/api/customers")
async def search_customers(q: str, db: Session = Depends(get_db)):
    """Search customers by email/phone"""
    results = db.query(CustomerProfile).filter(
        or_(
            CustomerProfile.email.ilike(f"%{q}%"),
            CustomerProfile.phone.like(f"%{q}%")
        )
    ).limit(20).all()
    
    return [
        {
            "customer_id": r.customer_id,
            "email": r.email,
            "lifetime_value": r.lifetime_value,
            "total_orders": r.total_orders,
            "health_score": r.health_score,
            "last_activity": r.last_activity
        }
        for r in results
    ]

@app.get("/api/customers/{customer_id}")
async def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Get full customer profile"""
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if not profile:
        return {"error": "Customer not found"}
    
    return {
        "customer_id": profile.customer_id,
        "email": profile.email,
        "phone": profile.phone,
        "lifetime_value": profile.lifetime_value,
        "total_orders": profile.total_orders,
        "average_order_value": profile.average_order_value,
        "first_purchase": profile.first_purchase,
        "last_purchase": profile.last_purchase,
        "health_score": profile.health_score,
        "page_views": profile.page_views_count,
        "product_views": profile.product_views_count
    }

@app.get("/api/customers/{customer_id}/timeline")
async def get_timeline(customer_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get customer event timeline"""
    events = db.query(CrmEvent).filter(
        CrmEvent.customer_id == customer_id
    ).order_by(CrmEvent.created_at.desc()).limit(limit).all()
    
    return [
        {
            "event_name": e.event_name,
            "event_data": e.event_data,
            "created_at": e.created_at
        }
        for e in events
    ]

@app.get("/api/customers/{customer_id}/orders")
async def get_orders(customer_id: str, db: Session = Depends(get_db)):
    """Get customer orders"""
    # Get customer email from customer_id
    identity = db.query(CustomerIdentity).filter(
        CustomerIdentity.customer_id == customer_id
    ).first()
    
    if not identity:
        return []
    
    orders = db.query(CrmOrder).filter(
        CrmOrder.email == identity.email
    ).order_by(CrmOrder.order_date.desc()).all()
    
    return [
        {
            "order_id": o.shopify_order_id,
            "date": o.order_date,
            "amount": o.total_amount,
            "status": o.status,
            "items": o.items
        }
        for o in orders
    ]
```

**2. Frontend (React/Next.js, new directory `src/modules/customers/`):**

```
src/
  modules/
    customers/
      pages/
        CustomerListPage.tsx
        CustomerDetailPage.tsx
      components/
        CustomerCard.tsx
        Timeline.tsx
        OrderHistory.tsx
        ProfileHeader.tsx
      hooks/
        useCustomer.ts
        useCustomerSearch.ts
```

Basic structure (CustomerListPage):

```typescript
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

export default function CustomerListPage() {
  const [search, setSearch] = useState('');
  
  const { data: customers } = useQuery({
    queryKey: ['customers', search],
    queryFn: async () => {
      const res = await fetch(`/api/customers?q=${search}`);
      return res.json();
    },
    enabled: search.length > 2
  });
  
  return (
    <div className="p-6">
      <input
        placeholder="Search customers..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full p-2 border rounded"
      />
      
      <div className="mt-6 space-y-4">
        {customers?.map(c => (
          <div key={c.customer_id} className="p-4 border rounded cursor-pointer hover:bg-gray-50">
            <p className="font-semibold">{c.email}</p>
            <p>Revenue: ₹{c.lifetime_value} | Orders: {c.total_orders}</p>
            <p>Health Score: {c.health_score}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Testing Phase 8

**1. Hit search API:**
```bash
curl "https://track.pureleven.com/api/customers?q=test"
```

**2. Deploy React frontend:**
```bash
npm run build
rsync -avz dist/ root@192.46.213.140:/var/www/crm-dashboard/
```

**3. Open in browser:**
```
https://ai.pureleven.com/customers
```

**Success Criteria:**
- ✅ Search returns customers instantly
- ✅ Click customer → see profile
- ✅ Timeline shows events
- ✅ Orders match crm_orders

---

## Phase 9: Add to Cart & Checkout Events (Week 9)

**Goal:** Full funnel tracking.

### What to Build

**1. Update crm-attribution.js:**

```javascript
// Track add to cart
window.trackAddToCart = async function(productId, productName, quantity, price) {
    const payload = {
        event_name: "add_to_cart",
        event_data: {
            product_id: productId,
            product_name: productName,
            quantity: quantity,
            price: price
        },
        visitor_id: getVisitorId(),
        session_id: getSessionId()
    };
    
    try {
        await fetch("/api/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to track add_to_cart:", e);
    }
};

// Track begin checkout
window.trackCheckout = async function() {
    const payload = {
        event_name: "begin_checkout",
        event_data: {
            cart_value: getCartValue()
        },
        visitor_id: getVisitorId(),
        session_id: getSessionId()
    };
    
    try {
        await fetch("/api/events", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
    } catch (e) {
        console.error("Failed to track begin_checkout:", e);
    }
};

// Hook into Shopify cart events
if (window.Shopify && window.Shopify.cart) {
    document.addEventListener("click", (e) => {
        if (e.target.closest("[data-button-name='Add to cart']") || 
            e.target.closest(".add-to-cart")) {
            // Capture product from page
            window.trackAddToCart(
                window.Shopify.product.id,
                window.Shopify.product.title,
                1,
                window.Shopify.product.price
            );
        }
    });
}
```

**2. Query funnel:**

```sql
SELECT 
  event_name,
  COUNT(*) as count
FROM crm_events
WHERE event_name IN ('page_view', 'product_view', 'add_to_cart', 'begin_checkout', 'purchase')
GROUP BY event_name
ORDER BY 
  CASE event_name
    WHEN 'page_view' THEN 1
    WHEN 'product_view' THEN 2
    WHEN 'add_to_cart' THEN 3
    WHEN 'begin_checkout' THEN 4
    WHEN 'purchase' THEN 5
  END;
```

### Testing Phase 9

**1. Place test order (track funnel):**
```
Home Page → Product Page → Add to Cart → Checkout → Purchase
```

**2. Query funnel:**
```bash
docker exec pureleven-postgres psql -U pureleven -d pureleven -c \
  "SELECT event_name, COUNT(*) FROM crm_events WHERE event_name IN ('page_view', 'product_view', 'add_to_cart', 'begin_checkout', 'purchase') GROUP BY event_name;"
```

**Success Criteria:**
- ✅ Complete funnel captured
- ✅ Conversion rates calculable
- ✅ Drop-off points visible

---

## Phase 10: Segments & Reporting (Week 10)

**Goal:** Classify customers, create basic reports.

### What to Build

**1. Add segments to customer_profiles:**

```sql
ALTER TABLE customer_profiles ADD COLUMN segments JSONB DEFAULT '{}';
ALTER TABLE customer_profiles ADD COLUMN tags JSONB DEFAULT '{}';
```

**2. Update profile generation to add segments:**

```python
def generate_customer_profile(db: Session, customer_id: str):
    # ... existing code ...
    
    # Calculate segments
    segments = {}
    
    if lifetime_value > 10000:
        segments['vip'] = True
    
    if total_orders > 20:
        segments['wholesale'] = True
    
    if total_orders > 1:
        segments['repeat_customer'] = True
    
    if days_since_activity and days_since_activity > 60:
        segments['at_risk'] = True
    
    profile.segments = segments
    db.commit()
```

**3. Basic reporting API:**

```python
@app.get("/api/reports/segments")
async def segments_report(db: Session = Depends(get_db)):
    """Segment breakdown"""
    profiles = db.query(CustomerProfile).all()
    
    segments = {}
    for p in profiles:
        if p.segments:
            for seg, val in p.segments.items():
                if val:
                    segments[seg] = segments.get(seg, 0) + 1
    
    return {"segments": segments, "total_customers": len(profiles)}


@app.get("/api/reports/funnel")
async def funnel_report(db: Session = Depends(get_db)):
    """Conversion funnel"""
    events = db.query(CrmEvent).all()
    
    event_counts = {}
    for e in events:
        event_counts[e.event_name] = event_counts.get(e.event_name, 0) + 1
    
    # Calculate conversion
    page_views = event_counts.get('page_view', 1)
    purchases = event_counts.get('purchase', 0)
    
    conversion_rate = (purchases / page_views * 100) if page_views > 0 else 0
    
    return {
        "funnel": event_counts,
        "conversion_rate": round(conversion_rate, 2)
    }


@app.get("/api/reports/lifetime-value")
async def ltv_report(db: Session = Depends(get_db)):
    """LTV distribution"""
    profiles = db.query(CustomerProfile).all()
    
    ltv_buckets = {
        '0-1000': 0,
        '1000-5000': 0,
        '5000-10000': 0,
        '10000+': 0
    }
    
    for p in profiles:
        ltv = p.lifetime_value or 0
        if ltv < 1000:
            ltv_buckets['0-1000'] += 1
        elif ltv < 5000:
            ltv_buckets['1000-5000'] += 1
        elif ltv < 10000:
            ltv_buckets['5000-10000'] += 1
        else:
            ltv_buckets['10000+'] += 1
    
    return {"ltv_distribution": ltv_buckets}
```

### Testing Phase 10

**1. Test segments report:**
```bash
curl https://track.pureleven.com/api/reports/segments
```

**2. Test funnel report:**
```bash
curl https://track.pureleven.com/api/reports/funnel
```

**3. Test LTV report:**
```bash
curl https://track.pureleven.com/api/reports/lifetime-value
```

**Success Criteria:**
- ✅ Segments calculated correctly
- ✅ Funnel conversion visible
- ✅ LTV distribution accurate

---

## Post-Phase 10: What You Have

✅ **crm_events** — Central event stream (immutable)  
✅ **crm_visitors** — Who visited  
✅ **crm_sessions** — Visitor sessions  
✅ **customer_identities** — Visitor → customer linking  
✅ **customer_profiles** — Generated customer view  
✅ **Customer 360 UI** — See any customer, complete profile + timeline + orders  
✅ **Reporting APIs** — Segments, funnel, LTV  

**Production system unchanged** — No risk to tracking  
**Completely parallel** — New system grows beside old one  

---

## Phase Dependencies

```
Phase 1: crm_events (foundation)
    ↓
Phase 2: Browser events (emit page_view, product_view)
    ↓
Phase 3: crm_visitors (track who)
    ↓
Phase 4: Order events (emit from webhook)
    ↓
Phase 5: Identity service (visitor → customer linking)
    ↓
Phase 6: Sessions (complete session tracking)
    ↓
Phase 7: Profiles (generate from events + orders)
    ↓
Phase 8: Customer 360 UI (first UI)
    ↓
Phase 9: Funnel (add_to_cart, checkout)
    ↓
Phase 10: Reporting (segments, reports)
```

Each phase **must** complete before next (sequential, not parallel).

---

## Testing Strategy for Each Phase

For each phase:

1. **Database** — Verify table created, indexes exist
2. **API** — Test endpoint responds, inserts data
3. **Data** — Query database, verify correct data
4. **Production** — Ensure existing tracking unaffected
5. **UI** (Phase 8+) — Visual test in browser

Never move to next phase without passing all tests.

---

## Files to Modify/Create

**Modify:**
- `crm_routes.py` (add event endpoints, call identity service, emit purchase events)
- `crm-attribution.js` (emit events instead of just localStorage)

**Create:**
- `app/services/event_service.py`
- `app/services/identity_service.py`
- `app/services/profile_service.py`
- `app/celery_tasks.py`
- `src/modules/customers/` (UI)

**Database:**
- 6 new tables (crm_events, crm_visitors, crm_sessions, customer_identities, customer_profiles, no schema changes to existing)

---

## Success Metrics

**Week 1:** ✅ crm_events table live, API responds  
**Week 2:** ✅ 100+ events/day flowing in  
**Week 3:** ✅ Visitors tracked  
**Week 4:** ✅ Orders emitting events (Meta/GA4 still working)  
**Week 5:** ✅ Identity service linking visitors → customers  
**Week 6:** ✅ Sessions tracked  
**Week 7:** ✅ customer_profiles generated  
**Week 8:** ✅ Customer 360 UI working  
**Week 9:** ✅ Full funnel tracked  
**Week 10:** ✅ Reports/segments available  

---

## After Phase 10: Future Phases

Once foundation solid:

**Phase 11:** Lead Management (leads table, assignment rules)  
**Phase 12:** Automation Engine (workflows, triggers on events)  
**Phase 13:** WhatsApp Hub (conversations, bulk messaging)  
**Phase 14:** AI Layer (scoring, churn prediction)  
**Phase 15:** Advanced Analytics (cohort analysis, retention curves)

Each builds on crm_events + customer_profiles.

