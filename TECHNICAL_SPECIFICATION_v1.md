# Pureleven Customer Intelligence Platform — Technical Specification v1

**Status:** Ready for Implementation  
**Date:** May 25, 2026  
**Scope:** Sprint 0-6 (6 weeks)  

---

# Table of Contents

1. Database Migrations
2. Event Schemas & Validation
3. API Contracts
4. UI Wireframes
5. Docker Deployment

---

# 1. Database Migrations

## Master Tables (Keep As-Is)

### crm_orders (Existing, Source of Truth)

```sql
-- NO CHANGES
-- Read-only from perspective of new platform
-- Updated only by crm_routes.py (Shopify webhook)

SELECT * FROM crm_orders LIMIT 1;
-- shopify_order_id | email | total_amount | created_at | 
-- payment_status | meta_status | google_status | ga4_status
```

**Usage:** Customer 360 API reads historical purchases (linked by email/Shopify ID).

### crm_customers (Existing, Dedup Source)

```sql
-- NO CHANGES
-- Contains: id, email, phone, created_at
-- Used: Reference when needed, don't duplicate
```

---

## New Tables (Create)

### 1. behavior_events

```sql
CREATE TABLE behavior_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event metadata
    event_type VARCHAR(50) NOT NULL,  
    -- Values: page_view, product_view, add_to_cart, purchase, whatsapp_click
    event_data JSONB NOT NULL,
    
    -- Identity
    visitor_id UUID,  -- Anonymous session
    customer_id UUID,  -- Linked customer (retroactive)
    
    -- Attribution
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    gclid VARCHAR(100),
    fbclid VARCHAR(100),
    
    -- Context
    session_id UUID,
    ip_address VARCHAR(50),
    user_agent TEXT,
    
    -- Timestamps (BOTH required)
    occurred_at TIMESTAMP NOT NULL,  -- When event actually happened (browser time)
    created_at TIMESTAMP DEFAULT NOW(),  -- When inserted into DB
    
    -- Indexing
    created_index SERIAL,
    
    CONSTRAINT valid_event_type CHECK (event_type IN ('page_view', 'product_view', 'add_to_cart', 'purchase', 'whatsapp_click'))
);

-- Indexes
CREATE INDEX idx_behavior_events_customer_id ON behavior_events(customer_id, occurred_at DESC);
CREATE INDEX idx_behavior_events_visitor_id ON behavior_events(visitor_id, occurred_at DESC);
CREATE INDEX idx_behavior_events_session_id ON behavior_events(session_id);
CREATE INDEX idx_behavior_events_event_type ON behavior_events(event_type);
CREATE INDEX idx_behavior_events_created_at ON behavior_events(created_at DESC);
```

---

### 2. visitors

```sql
CREATE TABLE visitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Browser fingerprint
    browser_id VARCHAR(100) UNIQUE,  -- localStorage key
    ip_address VARCHAR(50),
    user_agent TEXT,
    
    -- Linked customer (retroactive)
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    
    -- Lifecycle
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP,
    
    -- Status
    has_email BOOLEAN DEFAULT FALSE,
    has_phone BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_visitors_customer_id ON visitors(customer_id);
CREATE INDEX idx_visitors_browser_id ON visitors(browser_id);
```

---

### 3. sessions

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Link to visitor
    visitor_id UUID NOT NULL REFERENCES visitors(id),
    customer_id UUID REFERENCES customers(id),
    
    -- Session lifecycle
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,  -- Set when 30 min inactivity detected
    last_activity TIMESTAMP DEFAULT NOW(),
    
    -- Attributes
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    gclid VARCHAR(100),
    fbclid VARCHAR(100),
    
    -- Calculations
    duration_seconds INT,  -- ended_at - started_at
    event_count INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_visitor_id ON sessions(visitor_id);
CREATE INDEX idx_sessions_customer_id ON sessions(customer_id);
CREATE INDEX idx_sessions_started_at ON sessions(started_at DESC);
```

---

### 4. customer_identities

```sql
CREATE TABLE customer_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Link to main customer
    customer_id UUID NOT NULL UNIQUE REFERENCES customers(id),
    
    -- Identity hierarchy (primary → fallback)
    shopify_customer_id VARCHAR(100) UNIQUE,  -- PRIMARY
    email VARCHAR(100) UNIQUE,                 -- SECONDARY
    phone VARCHAR(20) UNIQUE,                  -- TERTIARY
    visitor_id UUID UNIQUE REFERENCES visitors(id),  -- FALLBACK
    
    -- Linking confidence
    primary_key_type VARCHAR(50),  -- shopify_id | email | phone | visitor_id
    confidence FLOAT DEFAULT 1.0,  -- Future: 0.0-1.0
    
    -- Retroactive linking info
    retroactively_linked_event_count INT DEFAULT 0,
    linked_events_at TIMESTAMP,
    
    -- Lifecycle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP
);

CREATE INDEX idx_customer_identities_customer_id ON customer_identities(customer_id);
CREATE INDEX idx_customer_identities_shopify_id ON customer_identities(shopify_customer_id);
CREATE INDEX idx_customer_identities_email ON customer_identities(email);
CREATE INDEX idx_customer_identities_phone ON customer_identities(phone);
```

---

### 5. customer_profiles

```sql
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL UNIQUE REFERENCES customers(id),
    
    -- Identity
    email VARCHAR(100),
    phone VARCHAR(20),
    shopify_customer_id VARCHAR(100),
    
    -- Metrics (stable, stored)
    lifetime_value FLOAT DEFAULT 0,
    total_orders INT DEFAULT 0,
    average_order_value FLOAT DEFAULT 0,
    
    page_views INT DEFAULT 0,
    product_views INT DEFAULT 0,
    total_events INT DEFAULT 0,
    
    -- Dates (STORE THESE, compute days_since at API)
    first_seen TIMESTAMP,
    first_purchase TIMESTAMP,
    last_purchase TIMESTAMP,
    last_activity TIMESTAMP,
    
    -- Computed at API layer (NOT stored)
    -- days_since_last_activity = (NOW() - last_activity)
    
    -- Classification
    segment VARCHAR(50),  -- vip | repeat | first_time | prospect | at_risk
    health_score INT,  -- 0-100
    
    -- Dirty flag for background rebuild
    dirty BOOLEAN DEFAULT FALSE,
    
    -- Rebuild tracking
    generated_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customer_profiles_customer_id ON customer_profiles(customer_id);
CREATE INDEX idx_customer_profiles_segment ON customer_profiles(segment);
CREATE INDEX idx_customer_profiles_dirty ON customer_profiles(dirty) WHERE dirty = TRUE;
```

---

### 6. customer_activity_feed

```sql
CREATE TABLE customer_activity_feed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Link to customer
    customer_id UUID NOT NULL REFERENCES customers(id),
    
    -- Link to raw event (for debugging)
    event_id UUID REFERENCES behavior_events(id),
    event_type VARCHAR(50),
    
    -- Human-readable timeline
    action VARCHAR(50),  -- viewed_page, viewed_product, purchased, etc.
    display_text VARCHAR(500) NOT NULL,  -- "Viewed Black Pepper", "Purchased ₹899"
    context JSONB,  -- Raw event data
    
    -- Timestamp (use behavior_event occurred_at if linked)
    occurred_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_action CHECK (action IN ('viewed_page', 'viewed_product', 'added_to_cart', 'purchased', 'whatsapp_click', 'aggregated'))
);

CREATE INDEX idx_customer_activity_feed_customer_id ON customer_activity_feed(customer_id, occurred_at DESC);
CREATE INDEX idx_customer_activity_feed_event_type ON customer_activity_feed(event_type);
```

---

### 7. event_errors (NEW: Error Tracking)

```sql
CREATE TABLE event_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What failed
    event_type VARCHAR(50),
    raw_event_data JSONB,
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Debugging
    validation_failed_field VARCHAR(100),  -- Which field failed validation
    stack_trace TEXT,
    
    -- Context
    visitor_id UUID,
    ip_address VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_event_errors_created_at ON event_errors(created_at DESC);
```

---

### 8. processed_webhooks (NEW: Idempotency)

```sql
CREATE TABLE processed_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Shopify webhook identification
    webhook_id VARCHAR(100) UNIQUE NOT NULL,
    webhook_type VARCHAR(50),  -- orders/paid, orders/create, etc.
    
    -- Idempotency
    processed BOOLEAN DEFAULT TRUE,
    result_status VARCHAR(50),  -- success | failed | retry
    error_message TEXT,
    
    -- Tracking
    processed_at TIMESTAMP DEFAULT NOW(),
    shopify_order_id VARCHAR(100)
);

CREATE INDEX idx_processed_webhooks_webhook_id ON processed_webhooks(webhook_id);
CREATE INDEX idx_processed_webhooks_processed_at ON processed_webhooks(processed_at DESC);
```

---

### 9. event_processing_log (NEW: Audit Trail)

```sql
CREATE TABLE event_processing_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Event being processed
    event_id UUID REFERENCES behavior_events(id),
    event_type VARCHAR(50),
    
    -- Processing status
    status VARCHAR(50),  -- pending | processing | processed | failed | retried
    
    -- Details
    processor_name VARCHAR(100),  -- "identity_service", "profile_service", etc.
    attempted_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_ms INT,
    
    -- Error tracking
    error_message TEXT,
    retry_count INT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_event_processing_log_event_id ON event_processing_log(event_id);
CREATE INDEX idx_event_processing_log_status ON event_processing_log(status);
CREATE INDEX idx_event_processing_log_created_at ON event_processing_log(created_at DESC);
```

---

### Master Customer Table

```sql
-- NEW: Master customer table (not from crm_customers)

CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Primary identity
    shopify_customer_id VARCHAR(100) UNIQUE,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    
    -- Registration
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Status
    status VARCHAR(50) DEFAULT 'active'  -- active | inactive | merged
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_shopify_id ON customers(shopify_customer_id);
```

---

## Migration Order (Sequential)

```
1. customers (master table)
2. visitors
3. sessions
4. behavior_events
5. customer_identities
6. customer_profiles
7. customer_activity_feed
8. event_errors
9. processed_webhooks
10. event_processing_log
```

---

# 2. Event Schemas & Validation

## Event Types & Structure

### page_view

```json
{
  "event_type": "page_view",
  "event_data": {
    "page_url": "https://pureleven.com/collections/spices",
    "page_title": "Spices Collection",
    "referrer": "google.com"
  }
}
```

**Required:** page_url, page_title  
**Optional:** referrer  
**Validate:** URL format, title non-empty

---

### product_view

```json
{
  "event_type": "product_view",
  "event_data": {
    "product_id": "pepper_200g",
    "product_name": "Black Pepper 200g",
    "price": 299,
    "currency": "INR",
    "category": "Spices",
    "url": "https://pureleven.com/products/pepper_200g"
  }
}
```

**Required:** product_id, product_name, price, category  
**Optional:** url, variant_id, collection  
**Validate:** product_id non-empty, price > 0, currency in [INR, USD]

---

### add_to_cart

```json
{
  "event_type": "add_to_cart",
  "event_data": {
    "product_id": "pepper_200g",
    "product_name": "Black Pepper 200g",
    "price": 299,
    "quantity": 1,
    "currency": "INR"
  }
}
```

**Required:** product_id, product_name, price, quantity  
**Validate:** quantity > 0, price > 0

---

### purchase

```json
{
  "event_type": "purchase",
  "event_data": {
    "order_id": "shopify_123456",
    "amount": 899,
    "currency": "INR",
    "item_count": 2,
    "items": [
      {
        "product_id": "pepper_200g",
        "product_name": "Black Pepper 200g",
        "price": 299,
        "quantity": 1
      }
    ]
  }
}
```

**Required:** order_id, amount, currency, item_count  
**Optional:** items array  
**Validate:** amount > 0, item_count > 0, items valid

---

### whatsapp_click (Future)

```json
{
  "event_type": "whatsapp_click",
  "event_data": {
    "campaign_id": "campaign_123",
    "message_id": "msg_456",
    "phone": "+919876543210"
  }
}
```

---

## Validation Rules

```python
# shared/events/event_validator.py

class EventValidator:
    
    REQUIRED_FIELDS = {
        "page_view": ["page_url", "page_title"],
        "product_view": ["product_id", "product_name", "price", "category"],
        "add_to_cart": ["product_id", "product_name", "price", "quantity"],
        "purchase": ["order_id", "amount", "currency", "item_count"],
        "whatsapp_click": ["campaign_id", "message_id"]
    }
    
    @staticmethod
    def validate(event_type: str, event_data: dict) -> bool:
        """Validate event against schema."""
        
        if event_type not in EventValidator.REQUIRED_FIELDS:
            raise ValueError(f"Unknown event_type: {event_type}")
        
        required = EventValidator.REQUIRED_FIELDS[event_type]
        for field in required:
            if field not in event_data or event_data[field] is None:
                raise ValueError(f"Missing required field: {field}")
        
        # Type-specific validation
        if event_type == "product_view":
            if event_data["price"] <= 0:
                raise ValueError("price must be > 0")
        
        if event_type == "purchase":
            if event_data["amount"] <= 0:
                raise ValueError("amount must be > 0")
        
        return True
```

---

# 3. API Contracts

## Authentication

**Header:** `Authorization: Bearer <JWT_TOKEN>`

**JWT Payload:**

```json
{
  "sub": "user_id",
  "role": "founder|admin|sales|support",
  "email": "user@pureleven.com",
  "exp": 1719331200
}
```

**Roles:**
- `founder` → Full access
- `admin` → Full access
- `sales` → Read-only Customer 360
- `support` → Read-only, limited customer data

---

## Event Ingestion

### POST /api/v1/events

**Request:**

```http
POST /api/v1/events
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "event_type": "product_view",
  "event_data": {
    "product_id": "pepper_200g",
    "product_name": "Black Pepper 200g",
    "price": 299,
    "category": "Spices"
  },
  "visitor_id": "v_abc123",
  "customer_id": "c_xyz789",  // optional
  "session_id": "s_123456",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "spices_summer",
  "occurred_at": "2026-05-25T10:30:00Z"
}
```

**Response (Success):**

```json
{
  "status": "ok",
  "event_id": "e_abc123xyz",
  "created_at": "2026-05-25T10:30:00Z"
}
```

**Response (Validation Error):**

```json
{
  "status": "error",
  "error": "VALIDATION_FAILED",
  "message": "Missing required field: product_name",
  "field": "product_name",
  "code": 400
}
```

**Error Handling:**
- Invalid event → Store in `event_errors` table, return 400
- Missing auth → Return 401
- Invalid JWT → Return 403

---

## Customer Identity

### POST /api/v1/customers/identify

**Request:**

```http
POST /api/v1/customers/identify
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "visitor_id": "v_abc123",
  "email": "customer@example.com",
  "phone": "+919876543210",
  "shopify_customer_id": "gid://shopify/Customer/123456"
}
```

**Response:**

```json
{
  "status": "ok",
  "customer_id": "c_xyz789",
  "retroactively_linked_events": 45
}
```

---

## Customer 360 API

### GET /api/v1/customers (Search)

**Request:**

```http
GET /api/v1/customers?q=basil@example.com&limit=20
Authorization: Bearer <JWT>
```

**Response:**

```json
{
  "results": [
    {
      "customer_id": "c_xyz789",
      "email": "basil@example.com",
      "phone": "+919876543210",
      "segment": "vip",
      "lifetime_value": 5000,
      "total_orders": 3,
      "health_score": 85,
      "last_activity": "2026-05-25T10:30:00Z"
    }
  ],
  "total": 1
}
```

---

### GET /api/v1/customers/{customer_id}

**Request:**

```http
GET /api/v1/customers/c_xyz789?timeline_limit=50&page=1
Authorization: Bearer <JWT>
```

**Response:**

```json
{
  "profile": {
    "customer_id": "c_xyz789",
    "email": "basil@example.com",
    "phone": "+919876543210",
    "shopify_customer_id": "gid://shopify/Customer/123456",
    
    "lifetime_value": 5000,
    "total_orders": 3,
    "average_order_value": 1666.67,
    "segment": "vip",
    "health_score": 85,
    
    "page_views": 42,
    "product_views": 18,
    "total_events": 127,
    
    "first_seen": "2025-01-15T08:00:00Z",
    "first_purchase": "2025-02-01T12:30:00Z",
    "last_purchase": "2026-05-20T15:45:00Z",
    "last_activity": "2026-05-25T10:30:00Z",
    "days_since_last_activity": 5
  },
  
  "timeline": [
    {
      "event_id": "e_abc123",
      "event_type": "product_view",
      "action": "viewed_product",
      "display_text": "Viewed Black Pepper Product",
      "context": {...},
      "occurred_at": "2026-05-25T10:30:00Z"
    },
    {
      "event_id": "e_def456",
      "event_type": "purchase",
      "action": "purchased",
      "display_text": "Purchased ₹899",
      "context": {...},
      "occurred_at": "2026-05-20T15:45:00Z"
    }
  ],
  "timeline_pagination": {
    "page": 1,
    "page_size": 50,
    "total": 147,
    "has_next": true
  },
  
  "orders": [
    {
      "order_id": "shopify_123456",
      "amount": 899,
      "status": "paid",
      "created_at": "2026-05-20T15:45:00Z"
    }
  ],
  
  "predictions": null  // Added in Sprint 5
}
```

---

## Webhook Endpoint (Existing, Modified)

### POST /api/crm/webhooks/shopify

**Idempotency Check:**

```python
# Before processing, check processed_webhooks table
webhook_id = request.headers.get("X-Shopify-Webhook-Id")

existing = db.query(ProcessedWebhook).filter(
    ProcessedWebhook.webhook_id == webhook_id
).first()

if existing:
    return {"status": "ok", "duplicate": True}  # Ignore retry

# Process webhook
# ...

# Mark as processed
ProcessedWebhook(webhook_id=webhook_id, processed=True, result_status="success")
```

---

# 4. UI Wireframes

## Customer 360 Admin Dashboard

### Page 1: Customer Search

```
┌─────────────────────────────────────┐
│ Pureleven Customer 360              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ [Search by email/phone...      ]    │
│ [Filter: Segment ▼]  [Role ▼]       │
└─────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ Customer Name        | Orders | LTV    | Status  │
├──────────────────────────────────────────────────┤
│ Basil Kumar          │  3     | ₹5000  │ VIP     │
│ Priya Shah           │  1     | ₹899   │ First   │
│ Rajesh Patel         │  15    | ₹45000 │ VIP     │
└──────────────────────────────────────────────────┘

[Next] [< Prev]
```

---

### Page 2: Customer Detail

```
┌──────────────────────────────────────────────────┐
│ Basil Kumar (basil@example.com)                  │
│ Phone: +919876543210                             │
└──────────────────────────────────────────────────┘

TABS:
┌─────────────┬──────────┬────────┬────────┐
│ Overview    │ Timeline │ Orders │ Events │
└─────────────┴──────────┴────────┴────────┘

=== OVERVIEW TAB ===

Profile Summary
┌──────────────────────────────────┐
│ Lifetime Value: ₹5000            │
│ Total Orders: 3                  │
│ Avg Order Value: ₹1666.67        │
│ Segment: VIP                     │
│ Health Score: 85/100             │
│ Last Activity: 5 days ago        │
└──────────────────────────────────┘

Events
┌──────────────────────────────────┐
│ Page Views: 42                   │
│ Product Views: 18                │
│ Add to Cart: 12                  │
│ Purchases: 3                     │
└──────────────────────────────────┘

---

=== TIMELINE TAB ===

[Viewed Black Pepper Product] May 25, 10:30 AM
[Added Pepper to Cart] May 25, 10:32 AM
[Purchased ₹899] May 20, 3:45 PM
[Viewed Turmeric Product] May 19, 8:15 AM
[Added Turmeric to Cart] May 19, 8:17 AM
[Purchased ₹699] May 15, 2:20 PM
[Viewed Homepage] May 15, 2:00 PM
[Viewed Spices Collection] May 15, 2:05 PM

[Load More...]

---

=== ORDERS TAB ===

Order ID        | Amount | Status | Date
─────────────────────────────────────────
shopify_123456  | ₹899   | Paid   | May 20
shopify_123455  | ₹699   | Paid   | May 15
shopify_123454  | ₹3402  | Paid   | Apr 2

---

=== EVENTS TAB ===

Event Type      | Date       | Time
─────────────────────────────────────
product_view    | May 25     | 10:30
add_to_cart     | May 25     | 10:32
purchase        | May 20     | 3:45 PM
```

---

## Mobile Responsive

- Search: Full width input, stacked filters
- Customer detail: Stack tabs vertically on mobile
- Timeline: Horizontal scroll-friendly cards
- Orders: Swipeable table rows

**Stack:** Next.js + Tailwind + ShadCN UI

---

# 5. Docker Deployment

## Docker Compose Structure

```yaml
version: "3.9"

services:
  
  # Existing services (keep as-is)
  pureleven-postgres:
    image: postgres:15
    container_name: pureleven-postgres
    environment:
      POSTGRES_DB: pureleven
      POSTGRES_USER: pureleven
      POSTGRES_PASSWORD: (from .env)
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - pureleven-network
  
  # New service: Redis (for Celery)
  pureleven-redis:
    image: redis:7-alpine
    container_name: pureleven-redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - pureleven-network
  
  # New service: pgBouncer (connection pooling)
  pureleven-pgbouncer:
    image: pgbouncer:latest
    container_name: pureleven-pgbouncer
    environment:
      PGHOST: pureleven-postgres
      PGPORT: 5432
      PGUSER: pureleven
      PGPASSWORD: (from .env)
      PGDATABASE: pureleven
    ports:
      - "6432:6432"
    volumes:
      - ./pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini
    networks:
      - pureleven-network
    depends_on:
      - pureleven-postgres
  
  # Existing AI engine (keep as-is, or update port)
  pureleven-ai-engine:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pureleven-ai-engine
    environment:
      DATABASE_URL: postgresql://pureleven:${DB_PASSWORD}@pureleven-pgbouncer:6432/pureleven
      REDIS_URL: redis://pureleven-redis:6379/0
      CELERY_BROKER_URL: redis://pureleven-redis:6379/0
      CELERY_RESULT_BACKEND: redis://pureleven-redis:6379/1
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app
    networks:
      - pureleven-network
    depends_on:
      - pureleven-postgres
      - pureleven-redis
      - pureleven-pgbouncer
  
  # New service: Celery worker
  pureleven-celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pureleven-celery-worker
    command: celery -A app.celery_tasks worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql://pureleven:${DB_PASSWORD}@pureleven-pgbouncer:6432/pureleven
      REDIS_URL: redis://pureleven-redis:6379/0
      CELERY_BROKER_URL: redis://pureleven-redis:6379/0
      CELERY_RESULT_BACKEND: redis://pureleven-redis:6379/1
    networks:
      - pureleven-network
    depends_on:
      - pureleven-postgres
      - pureleven-redis
  
  # New service: Celery beat (scheduler)
  pureleven-celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: pureleven-celery-beat
    command: celery -A app.celery_tasks beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://pureleven:${DB_PASSWORD}@pureleven-pgbouncer:6432/pureleven
      REDIS_URL: redis://pureleven-redis:6379/0
      CELERY_BROKER_URL: redis://pureleven-redis:6379/0
      CELERY_RESULT_BACKEND: redis://pureleven-redis:6379/1
    networks:
      - pureleven-network
    depends_on:
      - pureleven-postgres
      - pureleven-redis

volumes:
  postgres_data:
  redis_data:

networks:
  pureleven-network:
    driver: bridge
```

---

## Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://pureleven:password@pureleven-pgbouncer:6432/pureleven
DB_PASSWORD=your_postgres_password

# Redis
REDIS_URL=redis://pureleven-redis:6379/0

# Celery
CELERY_BROKER_URL=redis://pureleven-redis:6379/0
CELERY_RESULT_BACKEND=redis://pureleven-redis:6379/1

# API
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET=your_jwt_secret_key

# Deployment
ENV=production
LOG_LEVEL=info
```

---

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ .

# Run API server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Deployment Checklist

- [ ] Redis running
- [ ] pgBouncer configured and running
- [ ] Celery worker running
- [ ] Celery beat running
- [ ] Database migrations applied
- [ ] Event endpoint responding
- [ ] Customer 360 API responding
- [ ] JWT auth working
- [ ] Event validation rejecting bad data
- [ ] Webhook idempotency working

---

# Next Steps

## Sprint 0 Deliverables

1. ✅ Database migrations (all 10 tables)
2. ✅ Docker Compose with Redis + pgBouncer + Celery
3. ✅ Event validation module
4. ✅ JWT auth setup
5. ✅ Event ingestion endpoint
6. ✅ Error tracking (event_errors table)

## Sprint 1 Deliverables

1. Behavior events table populated from browser
2. Event stream flowing end-to-end
3. Visitors table populated

---

**Status:** Ready to build  
**Owner:** (Your name)  
**Last Updated:** May 25, 2026
