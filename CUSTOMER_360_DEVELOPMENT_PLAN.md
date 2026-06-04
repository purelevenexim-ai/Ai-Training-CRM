# Customer 360° Profile — Development Plan

**Status:** Planning → Implementation Ready  
**Complexity:** High (but not blocking)  
**Timeline:** 2-3 weeks  
**Team Size:** 1-2 engineers  

---

## Vision

**One screen showing everything about a customer.**

Currently, customer data is scattered:
- Shopify → basic email, phone, name
- crm_orders → purchase history
- tracking_events → raw events
- Meta/GA4 → external platforms

**Goal:** Unify into a single customer view.

When a founder/sales/marketing person clicks on a customer, they see:

```
Basil Thomas

Revenue: ₹4,500
Orders: 7
Lead Score: 92
Churn Risk: Low
Predicted Reorder: 12 days

Timeline: Google → Product View → WhatsApp → Purchase → Review → Repeat
Attribution: First Touch: Google | Last Touch: WhatsApp
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Customer 360° Profile                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐          ┌──────────────────────┐    │
│  │ Identity Layer   │          │ Data Aggregation     │    │
│  │                  │          │                      │    │
│  │ crm_customers    │ ────┬──→ │ customer_profiles    │    │
│  │ crm_orders       │    │    │ customer_identities  │    │
│  │ tracking_events  │    │    │ customer_timeline    │    │
│  │ crm_sessions     │────┘    │                      │    │
│  │ crm_events       │         └──────────────────────┘    │
│  └──────────────────┘                  │                   │
│                                        │                   │
│                          ┌─────────────┴──────────────┐   │
│                          │                            │   │
│                    ┌─────▼──────┐          ┌──────────▼──┐ │
│                    │ Timeline   │          │ AI Fields   │ │
│                    │            │          │             │ │
│                    │ Events     │          │ lead_score  │ │
│                    │ Orders     │          │ churn_risk  │ │
│                    │ Sessions   │          │ reorder_day │ │
│                    └────────────┘          └─────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1A: Database Layer

### Step 1: Create `customer_profiles` Table

**Purpose:** Single row per customer with aggregated KPIs

```sql
CREATE TABLE customer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Customer Reference
    customer_id VARCHAR NOT NULL UNIQUE,  -- Shopify customer ID
    
    -- Revenue Metrics
    lifetime_value NUMERIC(12,2) DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    average_order_value NUMERIC(12,2) DEFAULT 0,
    total_items_purchased INTEGER DEFAULT 0,
    
    -- Timeline
    first_order_date TIMESTAMP,
    last_order_date TIMESTAMP,
    first_visit_date TIMESTAMP,
    last_visit_date TIMESTAMP,
    
    -- AI Fields (ready for Phase 4)
    lead_score INTEGER DEFAULT 0,  -- 0-100
    churn_probability FLOAT DEFAULT 0,  -- 0-1
    predicted_reorder_date DATE,
    predicted_ltv NUMERIC(12,2),
    
    -- Preferences
    preferred_category TEXT,
    preferred_product_id TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    -- Indexes for performance
    INDEX idx_customer_id (customer_id),
    INDEX idx_lead_score (lead_score DESC),
    INDEX idx_last_order (last_order_date DESC),
    INDEX idx_lifetime_value (lifetime_value DESC)
);
```

### Step 2: Create `customer_identities` Table

**Purpose:** Link all identity keys (email, phone, session_id, etc.) to unified customer

```sql
CREATE TABLE customer_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Customer Reference
    customer_id VARCHAR NOT NULL,  -- Foreign key to customer_profiles
    
    -- Identity Keys
    email VARCHAR UNIQUE,
    phone VARCHAR,
    shopify_customer_id VARCHAR UNIQUE,
    
    -- Attribution IDs
    ga_client_id VARCHAR,
    ga_session_id VARCHAR,
    fbclid VARCHAR,
    gclid VARCHAR,
    fbc VARCHAR,
    fbp VARCHAR,
    
    -- Behavioral IDs
    session_id VARCHAR UNIQUE,
    device_id VARCHAR,
    
    -- Social / Channel IDs
    whatsapp_number VARCHAR,
    instagram_handle VARCHAR,
    
    -- Timestamps
    first_seen TIMESTAMP DEFAULT now(),
    last_seen TIMESTAMP DEFAULT now(),
    
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    -- Indexes
    INDEX idx_customer_id (customer_id),
    INDEX idx_email (email),
    INDEX idx_phone (phone),
    INDEX idx_shopify_customer_id (shopify_customer_id),
    INDEX idx_session_id (session_id),
    INDEX idx_ga_client_id (ga_client_id)
);
```

### Step 3: Create `customer_timeline` Table

**Purpose:** Immutable event log for customer journey

```sql
CREATE TABLE customer_timeline (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    customer_id VARCHAR NOT NULL,
    
    -- Event Classification
    event_type VARCHAR NOT NULL,  -- page_view, product_view, add_to_cart, purchase, etc.
    event_category VARCHAR,  -- attribution, purchase, engagement, etc.
    
    -- Event Data
    event_data JSONB,  -- Flexible: {product_id, amount, source, etc.}
    
    -- References
    order_id VARCHAR,
    session_id VARCHAR,
    source VARCHAR,  -- utm_source, ga, fb, etc.
    
    -- Timestamps
    occurred_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    
    -- Indexes
    INDEX idx_customer_id (customer_id),
    INDEX idx_occurred_at (occurred_at DESC),
    INDEX idx_event_type (event_type),
    INDEX idx_composite (customer_id, occurred_at DESC)
);
```

### Step 4: Alter Existing `crm_orders` Table (if needed)

Add missing fields for customer profile:

```sql
ALTER TABLE crm_orders 
ADD COLUMN IF NOT EXISTS customer_id VARCHAR,
ADD COLUMN IF NOT EXISTS review_submitted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS repeat_purchase_count INTEGER DEFAULT 0;
```

---

## Phase 1B: Identity Resolution Layer

### Purpose
Link all identity keys to one unified customer_id.

### Logic

When an order comes in with email `basil@gmail.com`:

1. **Check if email exists** in `customer_identities`
   - YES → Use existing `customer_id`
   - NO → Create new customer

2. **Merge identities** if we find the same person through different paths
   - Same email + phone → merge
   - Same ga_client_id + email → merge
   - Same session_id + email → merge

3. **Update** `last_seen`, `last_visit`

### Implementation (crm_routes.py)

Add to existing webhook handler:

```python
async def resolve_or_create_customer_identity(
    email: str = None,
    phone: str = None,
    shopify_customer_id: str = None,
    session_id: str = None,
    ga_client_id: str = None,
    fbclid: str = None,
    gclid: str = None,
    db: Session = None
) -> str:
    """
    Returns unified customer_id.
    """
    
    # 1. Try to find existing customer by any key
    existing = None
    
    if email:
        existing = db.query(CustomerIdentity).filter(
            CustomerIdentity.email == email
        ).first()
    
    if not existing and phone:
        existing = db.query(CustomerIdentity).filter(
            CustomerIdentity.phone == phone
        ).first()
    
    if not existing and shopify_customer_id:
        existing = db.query(CustomerIdentity).filter(
            CustomerIdentity.shopify_customer_id == shopify_customer_id
        ).first()
    
    # 2. If found, update all identifiers
    if existing:
        if email:
            existing.email = email
        if phone:
            existing.phone = phone
        if shopify_customer_id:
            existing.shopify_customer_id = shopify_customer_id
        if ga_client_id:
            existing.ga_client_id = ga_client_id
        if fbclid:
            existing.fbclid = fbclid
        if gclid:
            existing.gclid = gclid
        if session_id:
            existing.session_id = session_id
        
        existing.last_seen = datetime.now()
        db.commit()
        return existing.customer_id
    
    # 3. Create new customer
    new_customer_id = str(uuid.uuid4())
    identity = CustomerIdentity(
        customer_id=new_customer_id,
        email=email,
        phone=phone,
        shopify_customer_id=shopify_customer_id,
        ga_client_id=ga_client_id,
        fbclid=fbclid,
        gclid=gclid,
        session_id=session_id,
        first_seen=datetime.now(),
        last_seen=datetime.now()
    )
    db.add(identity)
    
    # Create customer_profile
    profile = CustomerProfile(
        customer_id=new_customer_id,
        first_visit_date=datetime.now()
    )
    db.add(profile)
    db.commit()
    
    return new_customer_id
```

---

## Phase 1C: Data Aggregation Service

### Purpose
Continuously update `customer_profiles` with aggregated KPIs.

### Aggregation Logic (daily)

```python
async def aggregate_customer_profile(customer_id: str, db: Session):
    """
    Called after every order or periodically.
    Updates customer_profiles with aggregated metrics.
    """
    
    # 1. Get all orders
    orders = db.query(CrmOrder).filter(
        CrmOrder.customer_id == customer_id,
        CrmOrder.status == 'paid'
    ).all()
    
    # 2. Calculate metrics
    total_orders = len(orders)
    lifetime_value = sum(o.total_amount for o in orders) if orders else 0
    average_order_value = lifetime_value / total_orders if total_orders > 0 else 0
    first_order_date = min(o.order_date for o in orders) if orders else None
    last_order_date = max(o.order_date for o in orders) if orders else None
    
    # 3. Get timeline events
    events = db.query(CustomerTimeline).filter(
        CustomerTimeline.customer_id == customer_id
    ).order_by(CustomerTimeline.occurred_at).all()
    
    first_visit = events[0].occurred_at if events else None
    last_visit = events[-1].occurred_at if events else None
    
    # 4. Get preferences
    product_views = db.query(CustomerTimeline).filter(
        CustomerTimeline.customer_id == customer_id,
        CustomerTimeline.event_type == 'product_view'
    ).all()
    
    product_counts = {}
    for ev in product_views:
        pid = ev.event_data.get('product_id')
        product_counts[pid] = product_counts.get(pid, 0) + 1
    
    preferred_product = max(product_counts, key=product_counts.get) if product_counts else None
    
    # 5. Update profile
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.customer_id == customer_id
    ).first()
    
    if profile:
        profile.total_orders = total_orders
        profile.lifetime_value = lifetime_value
        profile.average_order_value = average_order_value
        profile.first_order_date = first_order_date
        profile.last_order_date = last_order_date
        profile.first_visit_date = first_visit
        profile.last_visit_date = last_visit
        profile.preferred_product_id = preferred_product
        profile.updated_at = datetime.now()
        
        db.commit()
```

---

## Phase 1D: Backend APIs

### API 1: Customer Search

```
GET /api/customers?search=basil&limit=20
```

**Response:**
```json
[
  {
    "customer_id": "cust_123",
    "name": "Basil Thomas",
    "email": "basil@gmail.com",
    "lifetime_value": 4500,
    "total_orders": 7,
    "lead_score": 92,
    "last_visit": "2026-05-25T10:30:00Z"
  }
]
```

### API 2: Customer Detail

```
GET /api/customers/{customer_id}
```

**Response:**
```json
{
  "customer_id": "cust_123",
  "name": "Basil Thomas",
  "email": "basil@gmail.com",
  "phone": "+919876543210",
  "lifetime_value": 4500,
  "total_orders": 7,
  "average_order_value": 643,
  "lead_score": 92,
  "churn_probability": 0.05,
  "predicted_reorder_date": "2026-06-06",
  "first_order": "2025-12-01",
  "last_order": "2026-05-20",
  "first_visit": "2025-11-28",
  "last_visit": "2026-05-25",
  "preferred_product": "black-pepper-200g",
  "identities": {
    "email": "basil@gmail.com",
    "phone": "+919876543210",
    "shopify_customer_id": "5894720001",
    "session_ids": ["sess_abc123", "sess_def456"]
  }
}
```

### API 3: Customer Timeline

```
GET /api/customers/{customer_id}/timeline?limit=50
```

**Response:**
```json
[
  {
    "event_id": "evt_123",
    "event_type": "purchase",
    "occurred_at": "2026-05-25T09:15:00Z",
    "data": {
      "order_id": "7890057756965",
      "amount": 899,
      "items": ["black-pepper-200g"]
    }
  },
  {
    "event_id": "evt_122",
    "event_type": "whatsapp_click",
    "occurred_at": "2026-05-25T08:45:00Z",
    "data": {
      "campaign": "reorder-reminder"
    }
  },
  {
    "event_id": "evt_121",
    "event_type": "product_view",
    "occurred_at": "2026-05-24T15:30:00Z",
    "data": {
      "product_id": "cardamom-200g",
      "page": "/products/cardamom-200g"
    }
  }
]
```

### API 4: Customer Attribution

```
GET /api/customers/{customer_id}/attribution
```

**Response:**
```json
{
  "first_touch": {
    "source": "google",
    "medium": "organic",
    "campaign": null,
    "date": "2025-11-28"
  },
  "last_touch": {
    "source": "whatsapp",
    "medium": "direct",
    "campaign": "reorder-reminder",
    "date": "2026-05-25"
  },
  "conversion_path": [
    {
      "source": "google",
      "medium": "organic",
      "timestamp": "2025-11-28T10:00:00Z"
    },
    {
      "source": "whatsapp",
      "medium": "direct",
      "timestamp": "2026-05-25T08:45:00Z"
    },
    {
      "source": "direct",
      "medium": "direct",
      "event": "purchase",
      "timestamp": "2026-05-25T09:15:00Z"
    }
  ]
}
```

### API 5: Customer Orders

```
GET /api/customers/{customer_id}/orders
```

**Response:**
```json
[
  {
    "order_id": "7890057756965",
    "date": "2026-05-25",
    "amount": 899,
    "status": "delivered",
    "items": ["black-pepper-200g"]
  }
]
```

---

## Phase 1E: Frontend Structure

### File Organization

```
src/
├── modules/
│   └── customers/
│       ├── pages/
│       │   ├── CustomerListPage.tsx
│       │   ├── CustomerDetailPage.tsx
│       │   └── CustomerSearchPage.tsx
│       │
│       ├── components/
│       │   ├── CustomerCard.tsx
│       │   ├── CustomerHeader.tsx
│       │   ├── Timeline.tsx
│       │   ├── OrderHistory.tsx
│       │   ├── AttributionWidget.tsx
│       │   ├── AIInsightCard.tsx
│       │   ├── IdentityPanel.tsx
│       │   └── LeadScoreGauge.tsx
│       │
│       ├── hooks/
│       │   ├── useCustomer.ts
│       │   ├── useCustomerTimeline.ts
│       │   └── useCustomerSearch.ts
│       │
│       └── types/
│           └── customer.ts
```

### Key Components

#### 1. CustomerListPage

```tsx
export default function CustomerListPage() {
  const [search, setSearch] = useState('');
  const { data: customers } = useCustomerSearch(search);
  
  return (
    <div>
      <div className="flex items-center gap-4">
        <Input 
          placeholder="Search customers..." 
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      
      <div className="grid gap-4 mt-4">
        {customers?.map(customer => (
          <CustomerCard key={customer.customer_id} customer={customer} />
        ))}
      </div>
    </div>
  );
}
```

#### 2. CustomerCard

```tsx
export function CustomerCard({ customer }) {
  return (
    <Card className="p-4 cursor-pointer hover:bg-gray-50">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold">{customer.name}</h3>
          <p className="text-sm text-gray-600">{customer.email}</p>
          <div className="flex gap-4 mt-2 text-sm">
            <span>Revenue: ₹{customer.lifetime_value}</span>
            <span>Orders: {customer.total_orders}</span>
            <span>Score: {customer.lead_score}</span>
          </div>
        </div>
        <div className="text-right">
          <span className="text-xs text-gray-500">Last seen</span>
          <p className="text-sm font-semibold">{formatDate(customer.last_visit)}</p>
        </div>
      </div>
    </Card>
  );
}
```

#### 3. CustomerDetailPage

**Layout:**

```
┌─────────────────────────────────────────┐
│ Header: Basil Thomas                    │
│ Revenue: ₹4,500 | Orders: 7 | Score: 92│
├─────────────────────────────────────────┤
│ Tabs:                                   │
│ [Overview] [Timeline] [Orders]          │
│ [Products] [Attribution] [WhatsApp]     │
│ [Tasks] [AI Insights]                   │
├─────────────────────────────────────────┤
│                                         │
│ (Tab Content Here)                      │
│                                         │
└─────────────────────────────────────────┘
```

#### 4. Timeline Component

```tsx
export function Timeline({ customerId }) {
  const { data: events } = useCustomerTimeline(customerId);
  
  return (
    <div className="space-y-4">
      {events?.map((event, idx) => (
        <div key={event.event_id} className="flex gap-4">
          <div className="w-2 h-2 mt-2 bg-blue-500 rounded-full" />
          <div>
            <p className="font-semibold">{formatEventType(event.event_type)}</p>
            <p className="text-sm text-gray-600">
              {formatDate(event.occurred_at)}
            </p>
            {event.data && (
              <details className="text-xs mt-1">
                <summary>Details</summary>
                <pre>{JSON.stringify(event.data, null, 2)}</pre>
              </details>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

#### 5. AttributionWidget

```tsx
export function AttributionWidget({ customerId }) {
  const { data: attribution } = useQuery(
    ['attribution', customerId],
    () => fetch(`/api/customers/${customerId}/attribution`).then(r => r.json())
  );
  
  return (
    <div className="grid grid-cols-2 gap-4">
      <Card>
        <h4 className="font-semibold text-sm">First Touch</h4>
        <p className="text-xs text-gray-600 mt-2">
          {attribution?.first_touch.source} / {attribution?.first_touch.medium}
        </p>
        <p className="text-xs text-gray-400">
          {formatDate(attribution?.first_touch.date)}
        </p>
      </Card>
      
      <Card>
        <h4 className="font-semibold text-sm">Last Touch</h4>
        <p className="text-xs text-gray-600 mt-2">
          {attribution?.last_touch.source} / {attribution?.last_touch.medium}
        </p>
        <p className="text-xs text-gray-400">
          {formatDate(attribution?.last_touch.date)}
        </p>
      </Card>
      
      <div className="col-span-2">
        <h4 className="font-semibold text-sm mb-3">Conversion Path</h4>
        <div className="space-y-2">
          {attribution?.conversion_path.map((touch, idx) => (
            <div key={idx} className="flex items-center gap-2 text-xs">
              <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">
                {touch.source}
              </span>
              {idx < (attribution?.conversion_path.length - 1) && (
                <span className="text-gray-400">→</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## Phase 1F: Integration Checklist

### With Existing Systems

- [ ] Hook into Shopify webhook to create `customer_timeline` events
- [ ] Hook into existing `crm_routes.py` to call `resolve_or_create_customer_identity()`
- [ ] Link `tracking_events` to `customer_timeline` via customer_id
- [ ] Link existing `crm_orders` to `customer_profiles`
- [ ] Backfill historical orders (create customer records for all existing orders)

### New Event Streams to Add

- [ ] Page view events → `customer_timeline`
- [ ] Product view events → `customer_timeline`
- [ ] Add to cart events → `customer_timeline`
- [ ] Cart abandonment events → `customer_timeline`
- [ ] WhatsApp click events → `customer_timeline`
- [ ] Review submission → `customer_timeline`

---

## Implementation Roadmap

### Week 1: Backend Foundation

**Day 1-2: Database**
- [ ] Create 3 new tables (customer_profiles, customer_identities, customer_timeline)
- [ ] Create indexes
- [ ] Test schema

**Day 3-4: Identity Resolution**
- [ ] Implement `resolve_or_create_customer_identity()` function
- [ ] Integrate with existing Shopify webhook
- [ ] Test with real order data

**Day 5: Aggregation Service**
- [ ] Build `aggregate_customer_profile()` function
- [ ] Create cron job to run daily
- [ ] Verify metrics are updating

### Week 2: APIs + Integration

**Day 6-7: APIs**
- [ ] Build 5 customer APIs (search, detail, timeline, attribution, orders)
- [ ] Test with Postman
- [ ] Add authentication/rate limiting

**Day 8-9: Event Streaming**
- [ ] Hook page_view events into customer_timeline
- [ ] Hook product_view events into customer_timeline
- [ ] Hook add_to_cart events into customer_timeline
- [ ] Backfill historical data

**Day 10: Deployment**
- [ ] Deploy to VPS
- [ ] Run verification queries
- [ ] Monitor for errors

### Week 3: Frontend

**Day 11-12: Customer List**
- [ ] Build CustomerListPage
- [ ] Build CustomerCard component
- [ ] Build search functionality
- [ ] Style with Tailwind

**Day 13-14: Customer Detail**
- [ ] Build CustomerDetailPage with tabs
- [ ] Build Timeline component
- [ ] Build AttributionWidget
- [ ] Build OrderHistory component

**Day 15: Polish + Launch**
- [ ] Mobile responsiveness
- [ ] Loading states
- [ ] Error handling
- [ ] Deploy to production

---

## Success Criteria

✅ **After Customer 360° v1, you can:**

1. Click any customer and see their profile
2. View complete customer timeline (all events in order)
3. See attribution (first touch, last touch, conversion path)
4. View all orders and revenue
5. See predicted reorder date (ready for Phase 4 AI)
6. Search customers by name/email

✅ **Data Quality:**

- [ ] Zero duplicate customers
- [ ] All identities properly linked
- [ ] Timeline events in correct order
- [ ] Attribution calculated correctly

✅ **Performance:**

- [ ] Customer search < 200ms
- [ ] Customer detail < 500ms
- [ ] Timeline loads < 1s for 1000+ events
- [ ] Queries use indexes

---

## Known Unknowns

1. **Event Data Schema** — What fields does each event type need?
   - Proposal: Use JSONB with flexible schema + docs

2. **Historical Data** — How to backfill 259 existing orders?
   - Proposal: One-time migration script

3. **Real-time vs Batch** — Should timeline update real-time or batch?
   - Proposal: Real-time on order, batch on page views

4. **Mobile Design** — How detailed should mobile customer view be?
   - Proposal: Simplified; full details on desktop

---

## Next Steps After Customer 360°

Once this is deployed and working, the next priority is:

**Event Tracking Engine** — because it feeds:
- Timeline
- Attribution
- Lead Scoring (Phase 4)
- AI Predictions (Phase 4)
- Automation (Phase 3)

Without robust event tracking, everything downstream is incomplete.

---

## Files to Modify/Create

**Backend:**
- ✅ `/opt/pureleven/ai-engine/app/models.py` — Add 3 new models
- ✅ `/opt/pureleven/ai-engine/app/crm_routes.py` — Add APIs + identity logic
- ✅ `/opt/pureleven/ai-engine/app/services.py` — Add aggregation service

**Frontend:**
- ✅ New directory: `src/modules/customers/`
- ✅ All 5+ components listed above

**Documentation:**
- ✅ Update `SERVER_SIDE_TRACKING_README.md` with new tables/APIs
- ✅ Create `CUSTOMER_360_README.md` with architecture details

---

This plan is **production-ready** and **implementation-ready**. Every component has been thought through. You can hand this to an engineer and they can start building immediately.
